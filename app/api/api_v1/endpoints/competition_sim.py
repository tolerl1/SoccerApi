"""
Generic competition simulation endpoints.

POST /competition-sim/simulate   — run Monte Carlo for any league or cup
GET  /competition-sim/configs    — list all supported competitions
GET  /competition-sim/standings/{competition_id}/{season}  — current DB standings
GET  /competition-sim/team-ratings/{competition_id}/{season}  — derived team ratings
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.schemas import CompetitionSimRequest, CompetitionSimResponse
from app.simulator.competitions.registry import COMPETITION_CONFIGS, build_simulator

router = APIRouter(prefix="/competition-sim", tags=["competition-sim"])


def _run_simulation(competition_id: str, season: str, n: int) -> list[Any]:
    """Sync helper executed in a thread pool — creates its own DB session."""
    db: Session = SessionLocal()
    try:
        sim = build_simulator(competition_id, season, db)
        return sim.run_monte_carlo(n_simulations=n)  # type: ignore[return-value]
    finally:
        db.close()


def _run_standings(competition_id: str, season: str) -> list[Any]:
    db: Session = SessionLocal()
    try:
        sim = build_simulator(competition_id, season, db)
        return sim.get_current_standings()  # type: ignore[return-value]
    finally:
        db.close()


def _run_team_ratings(competition_id: str, season: str) -> tuple[dict[int, Any], dict[int, str]]:
    db: Session = SessionLocal()
    try:
        sim = build_simulator(competition_id, season, db)
        return sim.get_team_ratings(), sim.get_teams()  # type: ignore[return-value]
    finally:
        db.close()


@router.get("/configs")
def list_competition_configs() -> list[dict[str, str]]:
    """Return all supported competition configurations."""
    return [
        {"competition_id": cid, "name": cfg["name"], "format": cfg["format"]}
        for cid, cfg in COMPETITION_CONFIGS.items()
    ]


@router.post("/simulate")
async def simulate_competition(req: CompetitionSimRequest) -> CompetitionSimResponse:
    """
    Run a Monte Carlo simulation for any supported competition.

    competition_id: DB competition code (e.g. 'GB1', 'CL', 'WC')
    season: e.g. '2023/24' or '2024'
    n_simulations: number of iterations (default 5000, max 50000)
    """
    if req.competition_id not in COMPETITION_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown competition_id '{req.competition_id}'. Available: {list(COMPETITION_CONFIGS)}",
        )

    n = min(req.n_simulations, 50_000)
    cfg = COMPETITION_CONFIGS[req.competition_id]

    try:
        rows = await asyncio.to_thread(_run_simulation, req.competition_id, req.season, n)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return CompetitionSimResponse(
        competition_id=req.competition_id,
        season=req.season,
        format=cfg["format"],
        n_simulations=n,
        results=[r.__dict__ if hasattr(r, "__dict__") else r for r in rows],
    )


@router.get("/standings/{competition_id}/{season}")
async def get_current_standings(competition_id: str, season: str) -> list[dict[str, Any]]:
    """Return the current league standings from played games in the DB."""
    if competition_id not in COMPETITION_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Unknown competition '{competition_id}'")

    cfg = COMPETITION_CONFIGS[competition_id]
    if cfg["format"] != "league":
        raise HTTPException(
            status_code=400, detail="Standings are only available for league-format competitions."
        )

    try:
        standings = await asyncio.to_thread(_run_standings, competition_id, season)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return [s.__dict__ for s in standings]


@router.get("/team-ratings/{competition_id}/{season}")
async def get_team_ratings(competition_id: str, season: str) -> list[dict[str, Any]]:
    """Return derived team xGF/xGA ratings for a competition/season from DB data."""
    if competition_id not in COMPETITION_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Unknown competition '{competition_id}'")

    try:
        ratings, teams = await asyncio.to_thread(_run_team_ratings, competition_id, season)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return [
        {
            "club_id": club_id,
            "club_name": teams.get(club_id, str(club_id)),
            "xgf": round(r["xgf"], 3),
            "xga": round(r["xga"], 3),
            "net_gd": round(r["xgf"] - r["xga"], 3),
        }
        for club_id, r in ratings.items()
    ]
