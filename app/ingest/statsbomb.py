"""
StatsBomb open-data ingestion.

Two modes:
  1. Local clone  – point STATSBOMB_DATA_DIR at a local clone of
                    github.com/statsbomb/open-data  (fastest, no rate limits)
  2. HTTP raw     – fetches JSON files directly from the GitHub raw URL

Data is parsed and stored in the `statsbomb_matches` and `events` tables.

Available competitions (as of mid-2026):
  La Liga 2004/05–2020/21  (competition_id=11, the deepest historical dataset)
  Champions League 2003/04–2018/19  (id=16)
  Premier League 2003/04, 2015/16   (id=2)
  Bundesliga 2015/16, 2023/24       (id=9)
  Ligue 1 2015/16, 2021/22, 2022/23 (id=7)
  FIFA World Cup 1958–2022           (id=43)
  UEFA Euro 2020, 2024               (id=55)
  Copa América 2024                  (id=223)
  FA WSL 2018/19–2023/24             (id=37)
  + women's leagues, MLS, AFCON, etc.
"""

import json
import os
import urllib.request
from pathlib import Path
from typing import Iterator

from sqlalchemy.orm import Session

from app import models

# Base URL for raw GitHub files (public, no auth needed)
_GH_RAW = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
_LOCAL_DIR = os.environ.get("STATSBOMB_DATA_DIR", "")


# ---------------------------------------------------------------------------
# Low-level JSON fetchers
# ---------------------------------------------------------------------------

def _read_json(relative_path: str) -> list | dict:
    """Read a JSON file from local clone or GitHub raw URL."""
    if _LOCAL_DIR:
        full = Path(_LOCAL_DIR) / "data" / relative_path
        with open(full) as f:
            return json.load(f)

    url = f"{_GH_RAW}/{relative_path}"
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read())


def list_competitions() -> list[dict]:
    """Return the StatsBomb competitions index."""
    return _read_json("competitions.json")


def list_matches(competition_id: int, season_id: int) -> list[dict]:
    """Return match list for a competition/season."""
    return _read_json(f"matches/{competition_id}/{season_id}.json")


def iter_events(match_id: int) -> Iterator[dict]:
    """Yield all events for a single match."""
    events = _read_json(f"events/{match_id}.json")
    yield from events


def load_lineups(match_id: int) -> list[dict]:
    return _read_json(f"lineups/{match_id}.json")


# ---------------------------------------------------------------------------
# DB writers
# ---------------------------------------------------------------------------

def upsert_match(db: Session, match: dict, competition_id: int, season_id: int) -> models.StatsBombMatch:
    """Insert or update a StatsBomb match record."""
    mid = match["match_id"]
    existing = db.query(models.StatsBombMatch).filter_by(match_id=mid).first()

    obj = existing or models.StatsBombMatch()
    obj.match_id = mid
    obj.competition_id = competition_id
    obj.season_id = season_id
    obj.competition_name = match.get("competition", {}).get("competition_name", "")
    obj.season_name = match.get("season", {}).get("season_name", "")
    obj.match_date = match.get("match_date")
    obj.home_team_id = match.get("home_team", {}).get("home_team_id")
    obj.home_team_name = match.get("home_team", {}).get("home_team_name", "")
    obj.away_team_id = match.get("away_team", {}).get("away_team_id")
    obj.away_team_name = match.get("away_team", {}).get("away_team_name", "")
    obj.home_score = match.get("home_score")
    obj.away_score = match.get("away_score")
    obj.stadium = match.get("stadium", {}).get("name")
    obj.referee = match.get("referee", {}).get("name")

    if not existing:
        db.add(obj)
    return obj


def upsert_events_for_match(db: Session, match_id: int) -> int:
    """
    Fetch and store all events for `match_id`.
    Returns number of events written.
    Only stores event types useful for xGC: Pass, Carry, Shot, Pressure,
    Ball Receipt, Interception, Clearance, Dribble.
    """
    RELEVANT_TYPES = {
        "Pass", "Carry", "Shot", "Pressure",
        "Ball Receipt*", "Interception", "Clearance", "Dribble",
    }

    count = 0
    for ev in iter_events(match_id):
        etype = ev.get("type", {}).get("name", "")
        if etype not in RELEVANT_TYPES:
            continue

        eid = ev["id"]
        existing = db.query(models.StatsBombEvent).filter_by(event_id=eid).first()
        if existing:
            continue  # idempotent

        loc = ev.get("location") or [None, None]
        end_loc = (
            ev.get("pass", {}).get("end_location")
            or ev.get("carry", {}).get("end_location")
            or ev.get("shot", {}).get("end_location")
            or [None, None]
        )

        obj = models.StatsBombEvent(
            event_id=eid,
            match_id=match_id,
            index=ev.get("index"),
            period=ev.get("period"),
            minute=ev.get("minute"),
            second=ev.get("second"),
            event_type=etype,
            possession=ev.get("possession"),
            possession_team_id=ev.get("possession_team", {}).get("id"),
            team_id=ev.get("team", {}).get("id"),
            team_name=ev.get("team", {}).get("name", ""),
            player_id=ev.get("player", {}).get("id"),
            player_name=ev.get("player", {}).get("name", ""),
            position=ev.get("position", {}).get("name"),
            location_x=loc[0],
            location_y=loc[1],
            end_location_x=end_loc[0] if len(end_loc) > 0 else None,
            end_location_y=end_loc[1] if len(end_loc) > 1 else None,
            under_pressure=ev.get("under_pressure", False),
            outcome=_outcome(ev, etype),
            statsbomb_xg=ev.get("shot", {}).get("statsbomb_xg"),
        )
        db.add(obj)
        count += 1

    db.flush()
    return count


def ingest_competition_season(
    db: Session,
    competition_id: int,
    season_id: int,
    events: bool = True,
    max_matches: int | None = None,
) -> dict:
    """
    Full ingestion pipeline for one StatsBomb competition/season.

    Returns a summary dict with match and event counts.
    """
    matches = list_matches(competition_id, season_id)
    if max_matches:
        matches = matches[:max_matches]

    match_count = 0
    event_count = 0

    for m in matches:
        upsert_match(db, m, competition_id, season_id)
        match_count += 1
        if events:
            event_count += upsert_events_for_match(db, m["match_id"])

    db.commit()
    return {
        "competition_id": competition_id,
        "season_id": season_id,
        "matches_ingested": match_count,
        "events_ingested": event_count,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _outcome(ev: dict, etype: str) -> str | None:
    key = etype.lower().replace(" ", "_").replace("*", "").strip()
    sub = ev.get(key, {})
    if isinstance(sub, dict):
        return sub.get("outcome", {}).get("name") if isinstance(sub.get("outcome"), dict) else sub.get("outcome")
    return None
