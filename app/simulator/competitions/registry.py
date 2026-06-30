"""
Known competition configurations.

competition_id values match what the existing soccerdata / Transfermarkt-sourced
DB uses (Transfermarkt codes).  StatsBomb uses numeric IDs — those are noted too.

Adding a new competition is as simple as adding an entry here and wiring it
into `build_simulator`.
"""

from sqlalchemy.orm import Session

# competition_id (DB/Transfermarkt) → config dict
COMPETITION_CONFIGS: dict[str, dict] = {
    # -----------------------------------------------------------------------
    # Domestic leagues — format: "league"
    # -----------------------------------------------------------------------
    "GB1": {
        "name": "Premier League",
        "country": "England",
        "format": "league",
        "n_teams": 20,
        "top_n_ucl": 4,
        "top_n_uel": 1,
        "top_n_uecl": 1,
        "relegation_spots": 3,
        "home_advantage": 0.08,
        "statsbomb_id": 2,           # StatsBomb numeric competition_id
    },
    "ES1": {
        "name": "La Liga",
        "country": "Spain",
        "format": "league",
        "n_teams": 20,
        "top_n_ucl": 4,
        "top_n_uel": 1,
        "top_n_uecl": 1,
        "relegation_spots": 3,
        "home_advantage": 0.07,
        "statsbomb_id": 11,
    },
    "DE1": {
        "name": "Bundesliga",
        "country": "Germany",
        "format": "league",
        "n_teams": 18,
        "top_n_ucl": 4,
        "top_n_uel": 1,
        "top_n_uecl": 1,
        "relegation_spots": 2,
        "home_advantage": 0.08,
        "statsbomb_id": 9,
    },
    "IT1": {
        "name": "Serie A",
        "country": "Italy",
        "format": "league",
        "n_teams": 20,
        "top_n_ucl": 4,
        "top_n_uel": 1,
        "top_n_uecl": 1,
        "relegation_spots": 3,
        "home_advantage": 0.07,
        "statsbomb_id": 12,
    },
    "FR1": {
        "name": "Ligue 1",
        "country": "France",
        "format": "league",
        "n_teams": 18,
        "top_n_ucl": 2,
        "top_n_uel": 2,
        "top_n_uecl": 1,
        "relegation_spots": 3,
        "home_advantage": 0.07,
        "statsbomb_id": 7,
    },
    "PT1": {
        "name": "Primeira Liga",
        "country": "Portugal",
        "format": "league",
        "n_teams": 18,
        "top_n_ucl": 3,
        "top_n_uel": 2,
        "top_n_uecl": 1,
        "relegation_spots": 2,
        "home_advantage": 0.08,
        "statsbomb_id": None,
    },
    "NL1": {
        "name": "Eredivisie",
        "country": "Netherlands",
        "format": "league",
        "n_teams": 18,
        "top_n_ucl": 2,
        "top_n_uel": 2,
        "top_n_uecl": 1,
        "relegation_spots": 2,
        "home_advantage": 0.08,
        "statsbomb_id": None,
    },
    # -----------------------------------------------------------------------
    # Group-stage + knockout — format: "group_knockout"
    # -----------------------------------------------------------------------
    "CL": {
        "name": "UEFA Champions League (classic format)",
        "country": "Europe",
        "format": "group_knockout",
        "n_groups": 8,
        "teams_per_group": 4,
        "advance_per_group": 2,
        "best_third_count": 0,
        "home_advantage": 0.05,
        "statsbomb_id": 16,
    },
    "EL": {
        "name": "UEFA Europa League",
        "country": "Europe",
        "format": "group_knockout",
        "n_groups": 8,
        "teams_per_group": 4,
        "advance_per_group": 2,
        "best_third_count": 8,   # 8 third-place CL teams drop in at R32
        "home_advantage": 0.05,
        "statsbomb_id": 35,
    },
    "UEFA_EURO": {
        "name": "UEFA European Championship",
        "country": "Europe",
        "format": "group_knockout",
        "n_groups": 6,
        "teams_per_group": 4,
        "advance_per_group": 2,
        "best_third_count": 4,
        "home_advantage": 0.03,
        "statsbomb_id": 55,
    },
    "COPA_AMERICA": {
        "name": "Copa América",
        "country": "South America",
        "format": "group_knockout",
        "n_groups": 4,
        "teams_per_group": 4,
        "advance_per_group": 2,
        "best_third_count": 2,
        "home_advantage": 0.03,
        "statsbomb_id": 223,
    },
    "WC": {
        "name": "FIFA World Cup (32-team classic)",
        "country": "World",
        "format": "group_knockout",
        "n_groups": 8,
        "teams_per_group": 4,
        "advance_per_group": 2,
        "best_third_count": 0,
        "home_advantage": 0.0,
        "statsbomb_id": 43,
    },
}

# Reverse map: StatsBomb numeric ID → DB competition_id
STATSBOMB_TO_DB: dict[int, str] = {
    cfg["statsbomb_id"]: db_id
    for db_id, cfg in COMPETITION_CONFIGS.items()
    if cfg.get("statsbomb_id")
}


def build_simulator(competition_id: str, season: str | None, db: Session):
    """
    Factory that returns the correct simulator subclass for a competition.

    Raises ValueError if the competition_id is unknown.
    """
    from .league import LeagueSimulator
    from .group_knockout import GroupKnockoutSimulator

    cfg = COMPETITION_CONFIGS.get(competition_id)
    if cfg is None:
        raise ValueError(
            f"Unknown competition '{competition_id}'. "
            f"Known IDs: {sorted(COMPETITION_CONFIGS.keys())}"
        )

    fmt = cfg["format"]

    if fmt == "league":
        return LeagueSimulator(
            competition_id=competition_id,
            season=season,
            db=db,
            top_n_ucl=cfg.get("top_n_ucl", 4),
            top_n_uel=cfg.get("top_n_uel", 1),
            top_n_uecl=cfg.get("top_n_uecl", 1),
            relegation_spots=cfg.get("relegation_spots", 3),
            home_advantage=cfg.get("home_advantage", 0.08),
        )

    if fmt == "group_knockout":
        return GroupKnockoutSimulator(
            competition_id=competition_id,
            season=season,
            db=db,
            advance_per_group=cfg.get("advance_per_group", 2),
            best_third_count=cfg.get("best_third_count", 0),
        )

    raise ValueError(f"Unknown format '{fmt}' for competition '{competition_id}'.")
