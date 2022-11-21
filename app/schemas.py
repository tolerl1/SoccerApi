from datetime import date as date_type
from typing import Optional, Union

from pydantic import BaseModel


# class AppearanceBase(BaseModel):
#     appearance_id: str
#     game_id: int
#     player_id: int
#     player_club_id: int
#     date: date_type
#     player_pretty_name: str
#     competition_id: str
#     yellow_cards: int
#     red_cards: int
#     goals: int
#     assists: int
#     minutes_played: int


# class Appearance():
#     pass


# class ClubGameBase(BaseModel):
#     club_id: int
#     game_id: str
#     own_goals: int
#     own_position: int
#     own_manager_name: str
#     opponent_id: str
#     opponent_goals: int
#     opponent_position: int
#     opponent_manager_name: str
#     hosting: str
#     is_win: bool


# class ClubGame():
#     pass


class ClubBase(BaseModel):
    club_id: int
    name: Optional[str] = None
    pretty_name: Optional[str] = None
    domestic_competition_id: Optional[str] = None
    total_market_value: Optional[float] = None
    squad_size: Optional[int] = None
    average_age: Optional[float] = None
    foreigners_number: Optional[int] = None
    foreigners_percentage: Optional[float] = None
    national_team_players: Optional[int] = None
    stadium_name: Optional[str] = None
    stadium_seats: Optional[int] = None
    net_transfer_record: Optional[str] = None
    coach_name: Optional[str] = None
    url: Optional[str] = None


class ClubCreate(ClubBase):
    pass


class Club(ClubBase):
    class Config:
        orm_mode = True


class CompetitionBase(BaseModel):
    competition_id: str
    pretty_name: str
    type: str
    sub_type: str
    country_id: int
    country_name: Optional[str] = None
    country_latitude: float
    country_longitude: float
    domestic_league_code: Optional[str] = None
    name: str
    confederation: str
    url: Optional[str] = None


class CompetitionCreate(CompetitionBase):
    pass


class Competition(CompetitionBase):
    class Config:
        orm_mode = True


class GameBase(BaseModel):
    game_id: int
    competition_id: Optional[str] = None
    competition_type: Optional[str] = None
    season: Optional[str] = None
    round: Optional[str] = None
    date: Optional[date_type] = None
    home_club_id: Optional[int] = None
    away_club_id: Optional[int] = None
    home_club_goals: Optional[int] = None
    away_club_goals: Optional[int] = None
    aggregate: Optional[str] = None
    home_club_position: Optional[int] = None
    away_club_position: Optional[int] = None
    club_home_pretty_name: Optional[str] = None
    club_away_pretty_name: Optional[str] = None
    home_club_manager_name: Optional[str] = None
    away_club_manager_name: Optional[str] = None
    stadium: Optional[str] = None
    attendance: Optional[int] = None
    referee: Optional[str] = None
    url: Optional[str] = None


class GameCreate(GameBase):
    pass


class Game(GameBase):
    class Config:
        orm_mode = True


# class PlayerValuationBase(BaseModel):
#     date: date_type
#     datetime: date_type
#     dateweek: date_type
#     player_id: int
#     current_club_id: int
#     market_value: int
#     player_club_domestic_competition_id: str


# class PlayerValuation():
#     pass


class PlayerBase(BaseModel):
    player_id: int
    pretty_name: Optional[str] = None
    club_id: Optional[int] = None
    club_pretty_name: Optional[str] = None
    current_club_id: Optional[int] = None
    country_of_citizenship: Optional[str] = None
    country_of_birth: Optional[str] = None
    date_of_birth: Optional[date_type] = None
    position: Optional[str] = None
    sub_position: Optional[str] = None
    name: Optional[str] = None
    foot: Optional[str] = None
    height_in_cm: Optional[int] = None
    market_value_in_gbp: Optional[float] = None
    highest_market_value_in_gbp: Optional[float] = None
    agent_name: Optional[str] = None
    contract_expiration_date: Optional[date_type] = None
    domestic_competition_id: Optional[str] = None
    club_name: Optional[str] = None
    image_url: Optional[str] = None
    last_season: Optional[str] = None
    url: Optional[str] = None


class PlayerCreate(PlayerBase):
    pass


class Player(PlayerBase):
    class Config:
        orm_mode = True
