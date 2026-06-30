"""
Aggregate event-level GC attributions into per-player and per-team xGC ratings.

Two entry points:

  compute_player_xgc_from_events(db, match_ids) → list[PlayerXGCResult]
    Runs the full pipeline: loads events from DB → attributes each event →
    aggregates by player_id → returns sorted results.

  compute_team_ratings_from_events(db, competition_id, season_id) → dict
    Wraps the above and groups by team_id, returning xGF/xGA/net_GD suitable
    for feeding into the Poisson match simulator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from sqlalchemy.orm import Session

from .attribution import attribute_events, PlayerContribution
from .goal_probability import compute_gp


@dataclass
class PlayerXGCResult:
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    offensive_gc: float
    defensive_gc: float
    event_count: int

    @property
    def net_gc(self) -> float:
        return self.offensive_gc + self.defensive_gc


@dataclass
class TeamXGCRating:
    team_id: int
    team_name: str
    xgf: float   # average offensive GC per 90 min (proxy for xGF)
    xga: float   # average defensive GC conceded per 90 min (proxy for xGA)
    minutes_played: int = 0

    @property
    def net_gd(self) -> float:
        return self.xgf - self.xga


# ---------------------------------------------------------------------------
# Player aggregation
# ---------------------------------------------------------------------------

def compute_player_xgc_from_events(
    db: Session,
    match_ids: list[int],
    gp_fn: Callable = compute_gp,
) -> list[PlayerXGCResult]:
    """
    Load StatsBomb events for the given match IDs, run attribution, and
    return aggregated per-player GC results sorted by net_gc descending.
    """
    from app import models as m

    if not match_ids:
        return []

    events = (
        db.query(m.StatsBombEvent)
        .filter(m.StatsBombEvent.match_id.in_(match_ids))
        .order_by(m.StatsBombEvent.match_id, m.StatsBombEvent.index)
        .all()
    )

    attributions = attribute_events(events, gp_fn=gp_fn)

    # Accumulate per player
    accum: dict[int, dict] = {}
    for attr in attributions:
        for c in attr.contributions:
            if c.player_id <= 0:
                continue  # skip placeholder receiver entries
            if c.player_id not in accum:
                accum[c.player_id] = {
                    "player_name": c.player_name,
                    "team_id": c.team_id,
                    "team_name": "",
                    "offensive_gc": 0.0,
                    "defensive_gc": 0.0,
                    "event_count": 0,
                }
            accum[c.player_id]["offensive_gc"] += c.offensive_gc
            accum[c.player_id]["defensive_gc"] += c.defensive_gc
            accum[c.player_id]["event_count"] += 1

    # Resolve team names from DB
    team_ids = {v["team_id"] for v in accum.values() if v["team_id"]}
    team_names: dict[int, str] = {}
    if team_ids:
        matches_q = (
            db.query(m.StatsBombMatch)
            .filter(m.StatsBombMatch.match_id.in_(match_ids))
            .all()
        )
        for match in matches_q:
            if match.home_team_id:
                team_names[match.home_team_id] = match.home_team_name or ""
            if match.away_team_id:
                team_names[match.away_team_id] = match.away_team_name or ""

    results = []
    for pid, data in accum.items():
        tid = data["team_id"]
        results.append(
            PlayerXGCResult(
                player_id=pid,
                player_name=data["player_name"],
                team_id=tid,
                team_name=team_names.get(tid, ""),
                offensive_gc=round(data["offensive_gc"], 4),
                defensive_gc=round(data["defensive_gc"], 4),
                event_count=data["event_count"],
            )
        )

    results.sort(key=lambda r: r.net_gc, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Team aggregation → simulator-ready ratings
# ---------------------------------------------------------------------------

def compute_team_ratings_from_events(
    db: Session,
    competition_id: int,
    season_id: int,
    gp_fn: Callable = compute_gp,
    per_90: bool = True,
) -> dict[int, TeamXGCRating]:
    """
    Return a dict of {team_id: TeamXGCRating} for all teams in a StatsBomb
    competition/season.  Rates are scaled per 90 minutes if `per_90=True`.
    """
    from app import models as m

    matches = (
        db.query(m.StatsBombMatch)
        .filter(
            m.StatsBombMatch.competition_id == competition_id,
            m.StatsBombMatch.season_id == season_id,
        )
        .all()
    )
    if not matches:
        return {}

    match_ids = [match.match_id for match in matches]
    player_results = compute_player_xgc_from_events(db, match_ids, gp_fn=gp_fn)

    # Group by team
    team_off: dict[int, float] = {}
    team_def: dict[int, float] = {}
    team_names: dict[int, str] = {}

    for r in player_results:
        team_off[r.team_id] = team_off.get(r.team_id, 0.0) + r.offensive_gc
        team_def[r.team_id] = team_def.get(r.team_id, 0.0) + r.defensive_gc
        if r.team_name:
            team_names[r.team_id] = r.team_name

    # Estimate minutes: each match contributes 90 min per team
    match_count: dict[int, int] = {}
    for match in matches:
        for tid in (match.home_team_id, match.away_team_id):
            if tid:
                match_count[tid] = match_count.get(tid, 0) + 1

    results: dict[int, TeamXGCRating] = {}
    for tid in set(team_off) | set(team_def):
        n_matches = match_count.get(tid, 1)
        minutes = n_matches * 90
        scale = (90 / minutes) if per_90 and minutes > 0 else 1.0

        xgf = max(team_off.get(tid, 0.0) * scale, 0.50)
        xga_raw = team_def.get(tid, 0.0) * scale
        # Defensive GC is how much the team defended; xGA is threat conceded =
        # average league offense minus what this team defended.
        # Simple proxy: use 1.55 (league average) minus defensive contribution.
        avg_league_xgf = 1.55
        xga = max(avg_league_xgf - xga_raw, 0.50)

        results[tid] = TeamXGCRating(
            team_id=tid,
            team_name=team_names.get(tid, str(tid)),
            xgf=round(xgf, 3),
            xga=round(xga, 3),
            minutes_played=minutes,
        )

    return results
