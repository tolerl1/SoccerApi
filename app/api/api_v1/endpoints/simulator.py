"""
xGC World Cup Simulator API endpoints.

Routes:
  GET  /simulator/team-ratings              – xGF/xGA/Net GD for all 48 WC 2026 teams
  GET  /simulator/team-ratings/{team}       – Single team rating
  GET  /simulator/player-ratings            – Player xGC ratings computed from DB
  GET  /simulator/groups                    – WC 2026 group assignments
  POST /simulator/simulate-match            – One-off Poisson match simulation
  POST /simulator/simulate-tournament       – Single full WC 2026 simulation
  POST /simulator/monte-carlo               – N-trial Monte Carlo probability table
  GET  /simulator/probabilities/{team}      – Stage probabilities for one team (10k sims)
  GET  /simulator/club-ratings              – Elo + attack/defense from match history
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import crud, schemas
from app.api.deps import DbSession
from app.simulator import world_cup_2026 as wc
from app.simulator.match_simulator import simulate_match
from app.simulator.monte_carlo import run_monte_carlo
from app.simulator.tournament import simulate_full_tournament
from app.simulator.ratings import compute_elo_ratings, compute_attack_defense_strengths
from app.simulator.xgc import compute_player_xgc

router = APIRouter(prefix="/simulator", tags=["simulator"])


# ---------------------------------------------------------------------------
# Team ratings (hardcoded xGC from The Athletic's WC 2026 model)
# ---------------------------------------------------------------------------

@router.get("/team-ratings")
def get_all_team_ratings() -> list[schemas.TeamRating]:
    """Return xGF / xGA / Net GD for all 48 WC 2026 teams, sorted by Net GD."""
    teams = [
        schemas.TeamRating(team=name, **ratings)
        for name, ratings in wc.TEAM_RATINGS.items()
    ]
    return sorted(teams, key=lambda t: t.net_gd, reverse=True)


@router.get("/team-ratings/{team_name}")
def get_team_rating(team_name: str) -> schemas.TeamRating:
    """Return the xGC rating for a single WC 2026 team."""
    rating = wc.TEAM_RATINGS.get(team_name)
    if rating is None:
        for name, r in wc.TEAM_RATINGS.items():
            if name.lower() == team_name.lower():
                return schemas.TeamRating(team=name, **r)
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found.")
    return schemas.TeamRating(team=team_name, **rating)


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

@router.get("/groups")
def get_groups() -> dict[str, list[str]]:
    """Return the WC 2026 group assignments."""
    return wc.GROUPS


# ---------------------------------------------------------------------------
# Player xGC ratings (derived from DB market values)
# ---------------------------------------------------------------------------

@router.get("/player-ratings")
async def get_player_ratings(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    position_group: Annotated[str | None, Query()] = None,
) -> list[schemas.PlayerXGC]:
    """
    Return player xGC ratings computed from market values in the DB.
    Optionally filter by position_group: forward | midfielder | defender | goalkeeper.
    """
    players = await crud.get_multi_player(db)
    if not players:
        raise HTTPException(status_code=404, detail="No players found in DB.")

    ratings = compute_player_xgc(players)

    if position_group:
        ratings = [r for r in ratings if r["position_group"] == position_group.lower()]

    return [schemas.PlayerXGC(**r) for r in ratings[skip: skip + limit]]


# ---------------------------------------------------------------------------
# Match simulation
# ---------------------------------------------------------------------------

@router.post("/simulate-match")
async def simulate_one_match(payload: schemas.MatchSimRequest) -> schemas.MatchSimResult:
    """
    Simulate a single match between two teams using Poisson goal-scoring.

    Provide either:
      - `home_team` / `away_team` (names looked up in WC 2026 ratings), or
      - Explicit `home_xgf`, `home_xga`, `away_xgf`, `away_xga` overrides.
    """
    home_r = _resolve_team_rating(payload.home_team, payload.home_xgf, payload.home_xga)
    away_r = _resolve_team_rating(payload.away_team, payload.away_xgf, payload.away_xga)

    result = await asyncio.to_thread(
        simulate_match,
        payload.home_team or "Home", home_r["xgf"], home_r["xga"],
        payload.away_team or "Away", away_r["xgf"], away_r["xga"],
        payload.knockout, payload.neutral_venue,
    )

    return schemas.MatchSimResult(
        home_team=result.home_team,
        away_team=result.away_team,
        home_goals=result.home_goals,
        away_goals=result.away_goals,
        home_xg=result.home_xg,
        away_xg=result.away_xg,
        went_to_extra_time=result.went_to_extra_time,
        went_to_penalties=result.went_to_penalties,
        penalty_winner=result.penalty_winner,
        winner=result.winner,
    )


# ---------------------------------------------------------------------------
# Tournament simulation
# ---------------------------------------------------------------------------

@router.post("/simulate-tournament")
async def simulate_tournament_once() -> schemas.TournamentSimResult:
    """Run one complete WC 2026 simulation and return the full bracket outcome."""
    result = await asyncio.to_thread(simulate_full_tournament, wc.TEAM_RATINGS)
    return schemas.TournamentSimResult(
        champion=result.champion,
        finalist=result.finalist,
        semifinalists=result.semifinalists,
        quarterfinalists=result.quarterfinalists,
        round_of_16=result.round_of_16,
        round_of_32=result.round_of_32,
        group_stage_exit=result.group_stage_exit,
    )


# ---------------------------------------------------------------------------
# Monte Carlo probability table
# ---------------------------------------------------------------------------

@router.post("/monte-carlo")
async def run_monte_carlo_simulation(
    n_simulations: Annotated[int, Query(ge=100, le=50_000)] = 1000,
) -> list[schemas.TeamProbabilityRow]:
    """
    Run N Monte Carlo WC 2026 simulations and return per-team stage probabilities.
    """
    probs = await asyncio.to_thread(run_monte_carlo, n_simulations)
    rows = [
        schemas.TeamProbabilityRow(
            team=p.team,
            make_round_of_32=p.make_round_of_32,
            make_round_of_16=p.make_round_of_16,
            make_quarterfinals=p.make_quarterfinals,
            make_semifinals=p.make_semifinals,
            make_final=p.make_final,
            win_world_cup=p.win_world_cup,
            simulations=p.simulations,
        )
        for p in probs.values()
    ]
    return sorted(rows, key=lambda r: r.win_world_cup, reverse=True)


@router.get("/probabilities/{team_name}")
async def get_team_probabilities(
    team_name: str,
    n_simulations: Annotated[int, Query(ge=100, le=50_000)] = 5000,
) -> schemas.TeamProbabilityRow:
    """Return stage-progression probabilities for a single team via Monte Carlo."""
    matched = _fuzzy_team_name(team_name)
    if matched is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_name}' not found.")

    probs = await asyncio.to_thread(run_monte_carlo, n_simulations)
    p = probs.get(matched)
    if p is None:
        raise HTTPException(status_code=404, detail=f"No simulation data for '{matched}'.")

    return schemas.TeamProbabilityRow(
        team=p.team,
        make_round_of_32=p.make_round_of_32,
        make_round_of_16=p.make_round_of_16,
        make_quarterfinals=p.make_quarterfinals,
        make_semifinals=p.make_semifinals,
        make_final=p.make_final,
        win_world_cup=p.win_world_cup,
        simulations=p.simulations,
    )


# ---------------------------------------------------------------------------
# Club ratings from DB
# ---------------------------------------------------------------------------

@router.get("/club-ratings")
async def get_club_ratings(
    db: DbSession,
    method: Annotated[str, Query(pattern="^(elo|strength)$")] = "elo",
) -> list[schemas.ClubRating]:
    """
    Compute club ratings from historical match results in the DB.

    method=elo      → Elo points (higher = better)
    method=strength → Attack / defense strength multipliers + derived xGF/xGA
    """
    games = await crud.get_multi_game(db)
    if not games:
        raise HTTPException(status_code=404, detail="No games found in DB.")

    if method == "elo":
        elo = await asyncio.to_thread(compute_elo_ratings, games)
        clubs = {g.home_club_id: g.club_home_pretty_name for g in games}
        clubs.update({g.away_club_id: g.club_away_pretty_name for g in games})
        return sorted(
            [
                schemas.ClubRating(
                    club_id=cid,
                    club_name=clubs.get(cid, f"Club {cid}"),
                    elo=round(rating, 1),
                )
                for cid, rating in elo.items()
            ],
            key=lambda r: r.elo or 0,
            reverse=True,
        )

    strengths = await asyncio.to_thread(compute_attack_defense_strengths, games)
    clubs = {g.home_club_id: g.club_home_pretty_name for g in games}
    clubs.update({g.away_club_id: g.club_away_pretty_name for g in games})
    return sorted(
        [
            schemas.ClubRating(
                club_id=cid,
                club_name=clubs.get(cid, f"Club {cid}"),
                attack=s["attack"],
                defense=s["defense"],
                xgf=s["xgf"],
                xga=s["xga"],
            )
            for cid, s in strengths.items()
        ],
        key=lambda r: (r.xgf or 0) - (r.xga or 0),
        reverse=True,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_team_rating(
    team_name: str | None,
    xgf_override: float | None,
    xga_override: float | None,
) -> dict[str, float]:
    if xgf_override is not None and xga_override is not None:
        return {"xgf": xgf_override, "xga": xga_override}
    if team_name:
        matched = _fuzzy_team_name(team_name)
        if matched:
            return wc.TEAM_RATINGS[matched]
    raise HTTPException(
        status_code=422,
        detail=(
            f"Could not resolve team '{team_name}'. "
            "Provide a valid WC 2026 team name or explicit xgf/xga values."
        ),
    )


def _fuzzy_team_name(name: str) -> str | None:
    if name in wc.TEAM_RATINGS:
        return name
    lower = name.lower()
    for k in wc.TEAM_RATINGS:
        if k.lower() == lower:
            return k
    return None
