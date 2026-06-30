"""
Analytics endpoints — computed metrics and external data lookups.

GET /analytics/statsbomb/competitions          – competitions available in StatsBomb open-data
GET /analytics/club-elo                        – live Club Elo ratings from clubelo.com
GET /analytics/xgc/{competition_id}/{season_id} – event-level xGC per player (StatsBomb data)
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app import models
from app.api.deps import DbSession

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/statsbomb/competitions")
async def list_statsbomb_competitions() -> list[dict[str, Any]]:
    """
    Return all competitions available in the StatsBomb open-data repository.
    Fetches live from GitHub (or local clone if STATSBOMB_DATA_DIR is set).
    """
    try:
        from app.ingest.statsbomb import list_competitions
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        return await list_competitions()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch StatsBomb data: {exc}")


@router.get("/club-elo")
async def get_club_elo() -> list[dict[str, Any]]:
    """
    Fetch current Club Elo ratings from clubelo.com.
    Returns a list of {team, elo, country, level} dicts. Does not write to DB.
    Requires: pip install soccerdata
    """
    try:
        from app.ingest.soccerdata_client import fetch_club_elo_ratings
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        return await asyncio.to_thread(fetch_club_elo_ratings)  # type: ignore[return-value]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Club Elo error: {exc}")


@router.get("/xgc/{competition_id}/{season_id}")
async def compute_event_xgc(
    competition_id: int,
    season_id: int,
    db: DbSession,
) -> list[dict[str, Any]]:
    """
    Compute event-level xGC (Expected Goal Contribution) per player for a
    StatsBomb competition/season. Data must be ingested first via the worker:

        python -m app.ingest.worker statsbomb <competition_id> <season_id>

    Returns players sorted by net_gc descending.
    """
    try:
        from app.xgc_event.player_xgc import compute_player_xgc_from_events
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    result = await db.execute(
        select(models.StatsBombMatch)
        .where(models.StatsBombMatch.competition_id == competition_id)
        .where(models.StatsBombMatch.season_id == season_id)
    )
    matches = list(result.scalars().all())

    if not matches:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No StatsBomb data found for competition_id={competition_id}, "
                f"season_id={season_id}. "
                "Ingest it first: python -m app.ingest.worker statsbomb "
                f"{competition_id} {season_id}"
            ),
        )

    match_ids = [m.match_id for m in matches]

    try:
        rows = await compute_player_xgc_from_events(db, match_ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"xGC computation error: {exc}")

    return [
        {
            "player_id": r.player_id,
            "player_name": r.player_name,
            "team_id": r.team_id,
            "team_name": r.team_name,
            "offensive_gc": r.offensive_gc,
            "defensive_gc": r.defensive_gc,
            "net_gc": r.net_gc,
            "event_count": r.event_count,
        }
        for r in sorted(rows, key=lambda r: r.net_gc, reverse=True)
    ]
