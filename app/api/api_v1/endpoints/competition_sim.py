"""
Generic competition simulation endpoints.

POST /competition-sim/simulate   — run Monte Carlo for any league or cup
GET  /competition-sim/configs    — list all supported competitions
GET  /competition-sim/standings/{competition_id}/{season}  — current DB standings
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas import CompetitionSimRequest, CompetitionSimResponse
from app.simulator.competitions.registry import COMPETITION_CONFIGS, build_simulator
from app.simulator.competitions.league import LeagueSimulator
from app.simulator.competitions.group_knockout import GroupKnockoutSimulator

router = APIRouter()


@router.get("/configs")
def list_competition_configs():
    """Return all supported competition configurations."""
    return [
        {
            "competition_id": cid,
            "name": cfg["name"],
            "format": cfg["format"],
        }
        for cid, cfg in COMPETITION_CONFIGS.items()
    ]


@router.post("/simulate", response_model=CompetitionSimResponse)
def simulate_competition(req: CompetitionSimRequest, db: Session = Depends(get_db)):
    """
    Run a Monte Carlo simulation for any supported competition.

    competition_id: DB competition code (e.g. 'GB1', 'CL', 'WC')
    season: e.g. '2023/24' or '2024'
    n_simulations: number of iterations (default 5000)
    """
    if req.competition_id not in COMPETITION_CONFIGS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown competition_id '{req.competition_id}'. "
                   f"Available: {list(COMPETITION_CONFIGS)}",
        )

    try:
        sim = build_simulator(req.competition_id, req.season, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    cfg = COMPETITION_CONFIGS[req.competition_id]
    fmt = cfg["format"]

    try:
        n = min(req.n_simulations, 50_000)
        rows = sim.run_monte_carlo(n_simulations=n)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation error: {exc}")

    return CompetitionSimResponse(
        competition_id=req.competition_id,
        season=req.season,
        format=fmt,
        n_simulations=n,
        results=[r.__dict__ if hasattr(r, "__dict__") else r for r in rows],
    )


@router.get("/standings/{competition_id}/{season}")
def get_current_standings(
    competition_id: str,
    season: str,
    db: Session = Depends(get_db),
):
    """Return the current league standings from played games in the DB."""
    if competition_id not in COMPETITION_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Unknown competition '{competition_id}'")

    cfg = COMPETITION_CONFIGS[competition_id]
    if cfg["format"] != "league":
        raise HTTPException(
            status_code=400, detail="Standings are only available for league-format competitions."
        )

    try:
        sim = build_simulator(competition_id, season, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    standings = sim.get_current_standings()
    return [s.__dict__ for s in standings]


@router.get("/team-ratings/{competition_id}/{season}")
def get_team_ratings(
    competition_id: str,
    season: str,
    db: Session = Depends(get_db),
):
    """Return derived team xGF/xGA ratings for a competition/season from DB data."""
    if competition_id not in COMPETITION_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Unknown competition '{competition_id}'")

    try:
        sim = build_simulator(competition_id, season, db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    ratings = sim.get_team_ratings()
    teams = sim.get_teams()

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
