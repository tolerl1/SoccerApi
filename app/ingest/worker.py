"""
Ingestion worker — pull external datasets into the DB.

Run manually or schedule via cron:

    python -m app.ingest.worker statsbomb <competition_id> <season_id>
    python -m app.ingest.worker fbref-schedule GB1 2023/24
    python -m app.ingest.worker fbref-players GB1 2023/24
    python -m app.ingest.worker understat GB1 2023/24
    python -m app.ingest.worker club-elo
    python -m app.ingest.worker xgc <competition_id> <season_id>
"""

import argparse
import asyncio
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Async tasks (StatsBomb, xGC)
# ---------------------------------------------------------------------------

async def _ingest_statsbomb(
    competition_id: int,
    season_id: int,
    *,
    events: bool = True,
    max_matches: int | None = None,
) -> None:
    from app.database import AsyncSessionLocal
    from app.ingest.statsbomb import ingest_competition_season

    async with AsyncSessionLocal() as db:
        result = await ingest_competition_season(
            db, competition_id, season_id, events=events, max_matches=max_matches
        )
    log.info("StatsBomb ingestion complete: %s", result)


async def _compute_xgc(competition_id: int, season_id: int) -> None:
    from sqlalchemy import select

    from app.database import AsyncSessionLocal
    from app import models
    from app.xgc_event.player_xgc import compute_player_xgc_from_events

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.StatsBombMatch)
            .where(models.StatsBombMatch.competition_id == competition_id)
            .where(models.StatsBombMatch.season_id == season_id)
        )
        matches = list(result.scalars().all())

    if not matches:
        log.error(
            "No StatsBomb data for competition_id=%d season_id=%d — run `statsbomb` first.",
            competition_id,
            season_id,
        )
        return

    match_ids = [m.match_id for m in matches]
    async with AsyncSessionLocal() as db:
        rows = await compute_player_xgc_from_events(db, match_ids)

    for r in sorted(rows, key=lambda x: x.net_gc, reverse=True):
        print(f"{r.player_name:30s}  {r.team_name:25s}  net={r.net_gc:+.3f}")
    log.info("xGC computed for %d players across %d matches.", len(rows), len(match_ids))


# ---------------------------------------------------------------------------
# Sync tasks (soccerdata — blocking library)
# ---------------------------------------------------------------------------

def _ingest_fbref_schedule(competition_id: str, season: str) -> None:
    from app.database import SessionLocal
    from app.ingest.soccerdata_client import fetch_fbref_schedule

    db = SessionLocal()
    try:
        result = fetch_fbref_schedule(competition_id, season, db)
    finally:
        db.close()
    log.info("FBref schedule ingestion complete: %s", result)


def _ingest_fbref_players(competition_id: str, season: str, stat_type: str) -> None:
    from app.database import SessionLocal
    from app.ingest.soccerdata_client import fetch_fbref_player_stats

    db = SessionLocal()
    try:
        result = fetch_fbref_player_stats(competition_id, season, db, stat_type=stat_type)
    finally:
        db.close()
    log.info("FBref player stats ingestion complete: %s", result)


def _ingest_understat(competition_id: str, season: str) -> None:
    from app.database import SessionLocal
    from app.ingest.soccerdata_client import fetch_understat_results

    db = SessionLocal()
    try:
        result = fetch_understat_results(competition_id, season, db)
    finally:
        db.close()
    log.info("Understat ingestion complete: %s", result)


def _fetch_club_elo() -> None:
    from app.ingest.soccerdata_client import fetch_club_elo_ratings

    ratings = fetch_club_elo_ratings()
    for r in ratings:
        print(r)
    log.info("Club Elo fetched: %d teams.", len(ratings))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m app.ingest.worker",
        description="Pull external soccer datasets into the SoccerApi database.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sb = sub.add_parser("statsbomb", help="Ingest StatsBomb open-data matches and events")
    sb.add_argument("competition_id", type=int, help="StatsBomb competition ID")
    sb.add_argument("season_id", type=int, help="StatsBomb season ID")
    sb.add_argument("--no-events", dest="events", action="store_false", default=True,
                    help="Skip event ingestion (import match metadata only)")
    sb.add_argument("--max-matches", type=int, default=None,
                    help="Limit ingestion to first N matches (useful for testing)")

    fs = sub.add_parser("fbref-schedule", help="Pull match schedule and results from FBref")
    fs.add_argument("competition_id", help="DB competition code, e.g. GB1, ES1, CL")
    fs.add_argument("season", help="Season string, e.g. 2023/24")

    fp = sub.add_parser("fbref-players", help="Pull player season stats from FBref")
    fp.add_argument("competition_id", help="DB competition code")
    fp.add_argument("season", help="Season string")
    fp.add_argument("--stat-type", default="standard",
                    choices=["standard", "shooting", "passing", "defense", "misc"],
                    help="FBref stat category (default: standard)")

    us = sub.add_parser("understat", help="Pull match xG results from Understat")
    us.add_argument("competition_id", help="DB competition code, e.g. GB1, ES1")
    us.add_argument("season", help="Season string, e.g. 2023/24")

    sub.add_parser("club-elo", help="Fetch current Club Elo ratings (prints to stdout, no DB write)")

    xgc = sub.add_parser("xgc", help="Compute event-level xGC from ingested StatsBomb data")
    xgc.add_argument("competition_id", type=int, help="StatsBomb competition ID")
    xgc.add_argument("season_id", type=int, help="StatsBomb season ID")

    return p


def main() -> None:
    args = _build_parser().parse_args()

    if args.cmd == "statsbomb":
        asyncio.run(_ingest_statsbomb(
            args.competition_id, args.season_id,
            events=args.events, max_matches=args.max_matches,
        ))
    elif args.cmd == "fbref-schedule":
        _ingest_fbref_schedule(args.competition_id, args.season)
    elif args.cmd == "fbref-players":
        _ingest_fbref_players(args.competition_id, args.season, stat_type=args.stat_type)
    elif args.cmd == "understat":
        _ingest_understat(args.competition_id, args.season)
    elif args.cmd == "club-elo":
        _fetch_club_elo()
    elif args.cmd == "xgc":
        asyncio.run(_compute_xgc(args.competition_id, args.season_id))


if __name__ == "__main__":
    main()
