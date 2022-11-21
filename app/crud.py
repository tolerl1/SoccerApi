from sqlalchemy.orm import Session

from . import models, schemas


def get_club(db: Session, club_id: int):
    return db.query(models.Club).filter(models.Club.club_id == club_id).first()


def get_competition(db: Session, competition_id: str):
    return db.query(models.Competition).filter(models.Competition.competition_id == competition_id.upper()).first()


def get_game(db: Session, game_id: int):
    return db.query(models.Game).filter(models.Game.game_id == game_id).first()


def get_player(db: Session, player_id: int):
    return db.query(models.Player).filter(models.Player.player_id == player_id).first()