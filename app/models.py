from sqlalchemy import Column, ForeignKey, Integer, String, Date, Boolean, Float
from sqlalchemy.orm import relationship

from app.database import Base

# class Appearance:
#     __tablename__ = 'appearances'

#     appearance_id = Column(String)
#     game_id = Column(Integer, ForeignKey("games.game_id"))
#     player_id = Column(Integer, ForeignKey("players.player_id"))
#     player_club_id = Column(Integer)
#     date = Column(Date)
#     player_pretty_name = Column(String)
#     competition_id = Column(String)
#     yellow_cards = Column(Integer)
#     red_cards = Column(Integer)
#     goals = Column(Integer)
#     assists = Column(Integer)
#     minutes_played = Column(Integer)


# class ClubGame:
#     __tablename__ = 'club_games'

#     club_id = Column(Integer, ForeignKey("clubs.club_id"))
#     game_id = Column(String)
#     own_goals = Column(Integer)
#     own_position = Column(Integer)
#     own_manager_name = Column(String)
#     opponent_id = Column(String)
#     opponent_goals = Column(Integer)
#     opponent_position = Column(Integer)
#     opponent_manager_name = Column(String)
#     hosting = Column(String)
#     is_win = Column(Boolean)


class Club(Base):
    __tablename__ = 'clubs'

    club_id = Column(Integer, primary_key=True)
    name = Column(String)
    pretty_name = Column(String)
    domestic_competition_id = Column(String)
    total_market_value = Column(Float)
    squad_size = Column(Integer)
    average_age = Column(Float)
    foreigners_number = Column(Integer)
    foreigners_percentage = Column(Float)
    national_team_players = Column(Integer)
    stadium_name = Column(String)
    stadium_seats = Column(Integer)
    net_transfer_record = Column(String)
    coach_name = Column(String)
    url = Column(String)


class Competition(Base):
    __tablename__ = 'competitions'

    competition_id = Column(String, primary_key=True)
    pretty_name = Column(String)
    type = Column(String)
    sub_type = Column(String)
    country_id = Column(Integer)
    country_name = Column(String)
    country_latitude = Column(Float)
    country_longitude = Column(Float)
    domestic_league_code = Column(String)
    name = Column(String)
    confederation = Column(String)
    url = Column(String)


class Game(Base):
    __tablename__ = 'games'

    game_id = Column(Integer, primary_key=True)
    competition_id = Column(String)
    competition_type = Column(String)
    season = Column(String)
    round = Column(String)
    date = Column(Date)
    home_club_id = Column(Integer)
    away_club_id = Column(Integer)
    home_club_goals = Column(Integer)
    away_club_goals = Column(Integer)
    aggregate = Column(String)
    home_club_position = Column(Integer)
    away_club_position = Column(Integer)
    club_home_pretty_name = Column(String)
    club_away_pretty_name = Column(String)
    home_club_manager_name = Column(String)
    away_club_manager_name = Column(String)
    stadium = Column(String)
    attendance = Column(Integer)
    referee = Column(String)
    url = Column(String)


# class PlayerValuation:
#     __tablename__ = 'player_valuations'

#     date = Column(Date)
#     datetime = Column(Date)
#     dateweek = Column(Date)
#     player_id = Column(Integer, ForeignKey("players.player_id"))
#     current_club_id = Column(Integer)
#     market_value = Column(Integer)
#     player_club_domestic_competition_id = Column(String)


class Player(Base):
    __tablename__ = 'players'

    player_id = Column(Integer, primary_key=True)
    pretty_name = Column(String)
    club_id = Column(Integer)
    club_pretty_name = Column(String)
    current_club_id = Column(Integer)
    country_of_citizenship = Column(String)
    country_of_birth = Column(String)
    date_of_birth = Column(Date)
    position = Column(String)
    sub_position = Column(String)
    name = Column(String)
    foot = Column(String)
    height_in_cm = Column(Integer)
    market_value_in_gbp = Column(Float)
    highest_market_value_in_gbp = Column(Float)
    agent_name = Column(String)
    contract_expiration_date = Column(Date)
    domestic_competition_id = Column(String)
    club_name = Column(String)
    image_url = Column(String)
    last_season = Column(String)
    url = Column(String)
