"""
Data ingestion endpoints — trigger pulls from external sources.

POST /ingest/statsbomb        — ingest StatsBomb open-data competition/season
GET  /ingest/statsbomb/competitions  — list available StatsBomb competitions
POST /ingest/fbref/schedule   — pull match results from FBref via soccerdata
POST /ingest/fbref/players    — pull player season stats from FBref
POST /ingest/understat        — pull xG results from Understat
GET  /ingest/club-elo         — fetch current Club Elo ratings (no DB write)
GET  /ingest/xgc/{competition_id}/{season_id}  — compute event-level xGC from ingested data
"""

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app import models
from app.api.deps import DbSession
from app.database import SessionLocal
from app.schemas import (
    FBrefIngestRequest,
    FBrefIngestResponse,
    PlayerXGCEventResult,
    StatsBombCompetition,
    StatsBombIngestRequest,
    StatsBombIngestResponse,
)

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _sync_call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Run a blocking soccerdata function with a dedicated sync DB session."""
    db = SessionLocal()
    try:
        return fn(*args, db=db, **kwargs)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# StatsBomb
# ---------------------------------------------------------------------------

@router.get("/statsbomb/competitions")
async def list_statsbomb_competitions() -> list[StatsBombCompetition]:
    """
    Return all competitions available in the StatsBomb open-data repository.
    Fetches live from GitHub (or local clone if STATSBOMB_DATA_DIR is set).
    """
    try:
        from app.ingest.statsbomb import list_competitions
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        comps = await list_competitions()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch StatsBomb data: {exc}")

    return [
        StatsBombCompetition(
            competition_id=c["competition_id"],
            season_id=c["season_id"],
            competition_name=c.get("competition_name", ""),
            season_name=c.get("season_name", ""),
        )
        for c in comps
    ]


@router.post("/statsbomb")
async def ingest_statsbomb(req: StatsBombIngestRequest, db: DbSession) -> StatsBombIngestResponse:
    """
    Ingest a StatsBomb competition/season into the DB.

    Set events=false to import only match metadata (faster).
    Use max_matches to limit ingest during testing.
    """
    try:
        from app.ingest.statsbomb import ingest_competition_season
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        result = await ingest_competition_season(
            db=db,
            competition_id=req.competition_id,
            season_id=req.season_id,
            events=req.events,
            max_matches=req.max_matches,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Ingestion error: {exc}")

    return StatsBombIngestResponse(**result)


# ---------------------------------------------------------------------------
# FBref via soccerdata (blocking library — runs in thread pool)
# ---------------------------------------------------------------------------

@router.post("/fbref/schedule")
async def ingest_fbref_schedule(req: FBrefIngestRequest) -> FBrefIngestResponse:
    """
    Pull match schedule and results from FBref for a competition/season.
    Requires: pip install soccerdata
    """
    try:
        from app.ingest.soccerdata_client import fetch_fbref_schedule
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        result = await asyncio.to_thread(_sync_call, fetch_fbref_schedule, req.competition_id, req.season)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"FBref error: {exc}")

    return FBrefIngestResponse(**result)


@router.post("/fbref/players")
async def ingest_fbref_players(req: FBrefIngestRequest) -> FBrefIngestResponse:
    """
    Pull player season stats from FBref.
    stat_type: standard | shooting | passing | defense | misc
    """
    try:
        from app.ingest.soccerdata_client import fetch_fbref_player_stats
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        result = await asyncio.to_thread(
            _sync_call, fetch_fbref_player_stats, req.competition_id, req.season,
            stat_type=req.stat_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"FBref error: {exc}")

    return FBrefIngestResponse(**result)


# ---------------------------------------------------------------------------
# Understat
# ---------------------------------------------------------------------------

@router.post("/understat")
async def ingest_understat(req: FBrefIngestRequest) -> FBrefIngestResponse:
    """
    Pull match results with xG from Understat (Big 5 leagues only).
    Requires: pip install soccerdata
    """
    try:
        from app.ingest.soccerdata_client import fetch_understat_results
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        result = await asyncio.to_thread(_sync_call, fetch_understat_results, req.competition_id, req.season)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Understat error: {exc}")

    return FBrefIngestResponse(**result)


# ---------------------------------------------------------------------------
# Club Elo
# ---------------------------------------------------------------------------

@router.get("/club-elo")
async def get_club_elo() -> list[dict[str, Any]]:
    """
    Fetch current Club Elo ratings. Returns list of {team, elo, country, level}.
    Does not write to DB. Requires: pip install soccerdata
    """
    try:
        from app.ingest.soccerdata_client import fetch_club_elo_ratings
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    try:
        return await asyncio.to_thread(fetch_club_elo_ratings)  # type: ignore[return-value]
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Club Elo error: {exc}")


# ---------------------------------------------------------------------------
# Event-level xGC
# ---------------------------------------------------------------------------

@router.get("/xgc/{competition_id}/{season_id}")
async def compute_event_xgc(
    competition_id: int,
    season_id: int,
    db: DbSession,
) -> list[PlayerXGCEventResult]:
    """
    Compute event-level xGC ratings for all players in a StatsBomb
    competition/season (data must have been ingested first via POST /ingest/statsbomb).

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
                f"season_id={season_id}. Ingest it first via POST /ingest/statsbomb."
            ),
        )

    match_ids = [m.match_id for m in matches]

    try:
        results = await compute_player_xgc_from_events(db, match_ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"xGC computation error: {exc}")

    return [
        PlayerXGCEventResult(
            player_id=r.player_id,
            player_name=r.player_name,
            team_id=r.team_id,
            team_name=r.team_name,
            offensive_gc=r.offensive_gc,
            defensive_gc=r.defensive_gc,
            net_gc=r.net_gc,
            event_count=r.event_count,
        )
        for r in results
    ]
