"""
soccerdata integration — pulls match results and player stats into the DB.

Install: pip install soccerdata

Key scrapers used here:
  FBref         – comprehensive stats for Big 5 leagues + UCL (free)
  ClubElo       – Elo ratings updated daily (free, no scraping)
  Understat     – xG data for Big 5 leagues back to 2014 (free)
  football_data – Match results CSV from football-data.co.uk (free)

Each scraper has its own league codes; the mapping below translates
from our DB competition_id (Transfermarkt codes) to scraper-specific ones.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app import models

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# League code mappings  (DB competition_id → scraper league string)
# ---------------------------------------------------------------------------

FBREF_LEAGUE_MAP: dict[str, str] = {
    "GB1": "ENG-Premier League",
    "ES1": "ESP-La Liga",
    "DE1": "GER-Bundesliga",
    "IT1": "ITA-Serie A",
    "FR1": "FRA-Ligue 1",
    "PT1": "POR-Primeira Liga",
    "NL1": "NED-Eredivisie",
    "CL":  "UEFA-Champions League",
}

UNDERSTAT_LEAGUE_MAP: dict[str, str] = {
    "GB1": "EPL",
    "ES1": "La_liga",
    "DE1": "Bundesliga",
    "IT1": "Serie_A",
    "FR1": "Ligue_1",
}

CLUBELO_LEAGUE_MAP: dict[str, str] = {
    "GB1": "ENG",
    "ES1": "ESP",
    "DE1": "GER",
    "IT1": "ITA",
    "FR1": "FRA",
}

FOOTBALL_DATA_LEAGUE_MAP: dict[str, str] = {
    "GB1": "E0",     # English Premier League
    "ES1": "SP1",    # Spanish La Liga
    "DE1": "D1",     # German Bundesliga
    "IT1": "I1",     # Italian Serie A
    "FR1": "F1",     # French Ligue 1
}


# ---------------------------------------------------------------------------
# FBref scraper
# ---------------------------------------------------------------------------

def fetch_fbref_schedule(
    competition_id: str, season: str, db: Session
) -> dict:
    """
    Pull match schedule + results from FBref for a given league/season.
    Requires: pip install soccerdata
    """
    try:
        import soccerdata as sd
    except ImportError:
        raise ImportError("Run: pip install soccerdata")

    league = FBREF_LEAGUE_MAP.get(competition_id)
    if not league:
        raise ValueError(f"No FBref mapping for competition_id '{competition_id}'")

    scraper = sd.FBref(leagues=[league], seasons=[season])
    schedule = scraper.read_schedule()

    inserted = 0
    for _, row in schedule.iterrows():
        home_id = _get_or_create_club(db, row.get("home_team"), competition_id)
        away_id = _get_or_create_club(db, row.get("away_team"), competition_id)

        existing = (
            db.query(models.Game)
            .filter(
                models.Game.competition_id == competition_id,
                models.Game.season == season,
                models.Game.home_club_id == home_id,
                models.Game.away_club_id == away_id,
            )
            .first()
        )
        if existing:
            # Update result if now available
            home_g = row.get("home_goals")
            away_g = row.get("away_goals")
            if home_g is not None and existing.home_club_goals is None:
                existing.home_club_goals = int(home_g)
                existing.away_club_goals = int(away_g)
            continue

        game = models.Game(
            competition_id=competition_id,
            season=season,
            date=_parse_date(row.get("date")),
            home_club_id=home_id,
            away_club_id=away_id,
            club_home_pretty_name=str(row.get("home_team", "")),
            club_away_pretty_name=str(row.get("away_team", "")),
            home_club_goals=_safe_int(row.get("home_goals")),
            away_club_goals=_safe_int(row.get("away_goals")),
        )
        db.add(game)
        inserted += 1

    db.commit()
    return {"competition_id": competition_id, "season": season, "games_inserted": inserted}


def fetch_fbref_player_stats(
    competition_id: str, season: str, db: Session, stat_type: str = "standard"
) -> dict:
    """
    Pull player season stats from FBref.
    stat_type: 'standard' | 'shooting' | 'passing' | 'defense' | 'misc'
    Updates market_value_in_gbp placeholder with a rating proxy if available.
    """
    try:
        import soccerdata as sd
    except ImportError:
        raise ImportError("Run: pip install soccerdata")

    league = FBREF_LEAGUE_MAP.get(competition_id)
    if not league:
        raise ValueError(f"No FBref mapping for competition_id '{competition_id}'")

    scraper = sd.FBref(leagues=[league], seasons=[season])
    stats = scraper.read_player_season_stats(stat_type=stat_type)

    updated = 0
    for _, row in stats.iterrows():
        player_name = str(row.get("player", ""))
        if not player_name:
            continue
        player = (
            db.query(models.Player)
            .filter(models.Player.pretty_name.ilike(f"%{player_name}%"))
            .first()
        )
        if player:
            # Update last_season if this data is newer
            player.last_season = season
            updated += 1

    db.commit()
    return {"competition_id": competition_id, "season": season, "players_updated": updated}


# ---------------------------------------------------------------------------
# Understat scraper (xG per match)
# ---------------------------------------------------------------------------

def fetch_understat_results(
    competition_id: str, season: str, db: Session
) -> dict:
    """
    Pull match results with xG from Understat. Updates existing Game rows.
    Understat seasons are stored as the starting year (2023 for 2023/24).
    """
    try:
        import soccerdata as sd
    except ImportError:
        raise ImportError("Run: pip install soccerdata")

    league = UNDERSTAT_LEAGUE_MAP.get(competition_id)
    if not league:
        raise ValueError(f"No Understat mapping for competition_id '{competition_id}'")

    # Understat uses 4-digit year for the start of the season
    year = int(season.split("/")[0]) if "/" in season else int(season)
    scraper = sd.Understat(leagues=[league], seasons=[year])
    schedule = scraper.read_schedule()

    updated = 0
    for _, row in schedule.iterrows():
        home_team = str(row.get("home_team", ""))
        away_team = str(row.get("away_team", ""))
        game = (
            db.query(models.Game)
            .filter(
                models.Game.competition_id == competition_id,
                models.Game.season == season,
                models.Game.club_home_pretty_name.ilike(f"%{home_team}%"),
                models.Game.club_away_pretty_name.ilike(f"%{away_team}%"),
            )
            .first()
        )
        if game and row.get("home_goals") is not None and game.home_club_goals is None:
            game.home_club_goals = _safe_int(row.get("home_goals"))
            game.away_club_goals = _safe_int(row.get("away_goals"))
            updated += 1

    db.commit()
    return {"competition_id": competition_id, "season": season, "games_updated": updated}


# ---------------------------------------------------------------------------
# Club Elo
# ---------------------------------------------------------------------------

def fetch_club_elo_ratings(db: Session) -> list[dict]:
    """
    Pull current Club Elo ratings (updated daily).
    Returns a list of {team, elo, country, level} dicts — does not write to DB
    directly since Elo is a derived quantity; use the simulator's ratings.py instead.
    """
    try:
        import soccerdata as sd
    except ImportError:
        raise ImportError("Run: pip install soccerdata")

    scraper = sd.ClubElo()
    df = scraper.read_by_date()
    return [
        {
            "team": row.get("team"),
            "elo": row.get("elo"),
            "country": row.get("country"),
            "level": row.get("level"),
        }
        for _, row in df.iterrows()
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_club(db: Session, name: Any, competition_id: str) -> int | None:
    if not name:
        return None
    name_str = str(name)
    club = db.query(models.Club).filter(models.Club.pretty_name == name_str).first()
    if club:
        return club.club_id
    # Create a minimal club record
    new_club = models.Club(
        name=name_str,
        pretty_name=name_str,
        domestic_competition_id=competition_id,
    )
    db.add(new_club)
    db.flush()
    return new_club.club_id


def _parse_date(val: Any) -> date | None:
    if val is None:
        return None
    try:
        from datetime import datetime
        return datetime.strptime(str(val)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def _safe_int(val: Any) -> int | None:
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None
