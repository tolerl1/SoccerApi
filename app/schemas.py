from datetime import date as date_type

from pydantic import BaseModel, ConfigDict


class ClubBase(BaseModel):
    club_id: int
    name: str | None = None
    pretty_name: str | None = None
    domestic_competition_id: str | None = None
    total_market_value: float | None = None
    squad_size: int | None = None
    average_age: float | None = None
    foreigners_number: int | None = None
    foreigners_percentage: float | None = None
    national_team_players: int | None = None
    stadium_name: str | None = None
    stadium_seats: int | None = None
    net_transfer_record: str | None = None
    coach_name: str | None = None
    url: str | None = None


class ClubCreate(ClubBase):
    pass


class Club(ClubBase):
    model_config = ConfigDict(from_attributes=True)


class CompetitionBase(BaseModel):
    competition_id: str
    pretty_name: str
    type: str
    sub_type: str
    country_id: int
    country_name: str | None = None
    country_latitude: float
    country_longitude: float
    domestic_league_code: str | None = None
    name: str
    confederation: str
    url: str | None = None


class CompetitionCreate(CompetitionBase):
    pass


class Competition(CompetitionBase):
    model_config = ConfigDict(from_attributes=True)


class GameBase(BaseModel):
    game_id: int
    competition_id: str | None = None
    competition_type: str | None = None
    season: str | None = None
    round: str | None = None
    date: date_type | None = None
    home_club_id: int | None = None
    away_club_id: int | None = None
    home_club_goals: int | None = None
    away_club_goals: int | None = None
    aggregate: str | None = None
    home_club_position: int | None = None
    away_club_position: int | None = None
    club_home_pretty_name: str | None = None
    club_away_pretty_name: str | None = None
    home_club_manager_name: str | None = None
    away_club_manager_name: str | None = None
    stadium: str | None = None
    attendance: int | None = None
    referee: str | None = None
    url: str | None = None


class GameCreate(GameBase):
    pass


class Game(GameBase):
    model_config = ConfigDict(from_attributes=True)


class PlayerBase(BaseModel):
    player_id: int
    pretty_name: str | None = None
    club_id: int | None = None
    club_pretty_name: str | None = None
    current_club_id: int | None = None
    country_of_citizenship: str | None = None
    country_of_birth: str | None = None
    date_of_birth: date_type | None = None
    position: str | None = None
    sub_position: str | None = None
    name: str | None = None
    foot: str | None = None
    height_in_cm: int | None = None
    market_value_in_gbp: float | None = None
    highest_market_value_in_gbp: float | None = None
    agent_name: str | None = None
    contract_expiration_date: date_type | None = None
    domestic_competition_id: str | None = None
    club_name: str | None = None
    image_url: str | None = None
    last_season: str | None = None
    url: str | None = None


class PlayerCreate(PlayerBase):
    pass


class Player(PlayerBase):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Simulator schemas
# ---------------------------------------------------------------------------

class TeamRating(BaseModel):
    team: str
    xgf: float
    xga: float
    net_gd: float


class PlayerXGC(BaseModel):
    player_id: int
    name: str | None = None
    team: str | None = None
    position_group: str
    net_xgc: float
    offensive_xgc: float
    defensive_xgc: float
    market_value_gbp: float | None = None


class MatchSimRequest(BaseModel):
    home_team: str | None = None
    away_team: str | None = None
    home_xgf: float | None = None
    home_xga: float | None = None
    away_xgf: float | None = None
    away_xga: float | None = None
    knockout: bool = False
    neutral_venue: bool = True


class MatchSimResult(BaseModel):
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    home_xg: float
    away_xg: float
    went_to_extra_time: bool
    went_to_penalties: bool
    penalty_winner: str | None = None
    winner: str | None = None


class TournamentSimResult(BaseModel):
    champion: str
    finalist: str
    semifinalists: list[str]
    quarterfinalists: list[str]
    round_of_16: list[str]
    round_of_32: list[str]
    group_stage_exit: list[str]


class TeamProbabilityRow(BaseModel):
    team: str
    make_round_of_32: float
    make_round_of_16: float
    make_quarterfinals: float
    make_semifinals: float
    make_final: float
    win_world_cup: float
    simulations: int


class ClubRating(BaseModel):
    club_id: int | None = None
    club_name: str | None = None
    elo: float | None = None
    attack: float | None = None
    defense: float | None = None
    xgf: float | None = None
    xga: float | None = None


# ---------------------------------------------------------------------------
# Competition simulation schemas
# ---------------------------------------------------------------------------

class LeagueProbRow(BaseModel):
    club_id: int | None = None
    club_name: str
    avg_final_position: float
    win_title: float
    qualify_ucl: float
    qualify_uel: float
    qualify_uecl: float
    relegated: float
    simulations: int


class KnockoutProbRow(BaseModel):
    team_id: int | None = None
    team_name: str
    win_tournament: float
    reach_final: float
    reach_semifinal: float
    reach_quarterfinal: float
    reach_round_of_16: float
    reach_group_stage: float
    simulations: int


class CompetitionSimRequest(BaseModel):
    competition_id: str
    season: str
    n_simulations: int = 5000


class CompetitionSimResponse(BaseModel):
    competition_id: str
    season: str
    format: str
    n_simulations: int
    results: list


# ---------------------------------------------------------------------------
# Ingestion schemas
# ---------------------------------------------------------------------------

class StatsBombIngestRequest(BaseModel):
    competition_id: int
    season_id: int
    events: bool = True
    max_matches: int | None = None


class StatsBombIngestResponse(BaseModel):
    competition_id: int
    season_id: int
    matches_ingested: int
    events_ingested: int


class FBrefIngestRequest(BaseModel):
    competition_id: str
    season: str
    stat_type: str = "standard"


class FBrefIngestResponse(BaseModel):
    competition_id: str
    season: str
    games_inserted: int | None = None
    players_updated: int | None = None


class PlayerXGCEventResult(BaseModel):
    player_id: int
    player_name: str
    team_id: int
    team_name: str
    offensive_gc: float
    defensive_gc: float
    net_gc: float
    event_count: int


class StatsBombCompetition(BaseModel):
    competition_id: int
    season_id: int
    competition_name: str
    season_name: str
