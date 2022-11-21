from typing import Optional, Union
from sqlalchemy.orm import Session

from app import models
from app.schemas import Player


def get_club(db: Session, club_id: int):
    return db.query(models.Club).filter(models.Club.club_id == club_id).first()


def get_competition(db: Session, competition_id: str):
    return db.query(models.Competition).filter(models.Competition.competition_id == competition_id.upper()).first()


def get_game(db: Session, game_id: int):
    return db.query(models.Game).filter(models.Game.game_id == game_id).first()


def get_player_by_id(db: Session, player_id: int):
    return db.query(models.Player).filter(models.Player.player_id == player_id).first()


def get_multi_player(db: Session, skip: int = 0, limit: Union[int, None] = None) -> list[Player]:
    return (
        db.query(models.Player)
        .offset(skip)
        .limit(limit)
        .all()
    )