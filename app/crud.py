from typing import Union
from sqlalchemy.orm import Session

from app import models
from app.schemas import Player, Game, Competition, Club


# needs refactoring, lot of duplication


def get_club_by_id(db: Session, club_id: int):
    return db.query(models.Club).filter(models.Club.club_id == club_id).first()


def get_multi_club(db: Session, skip: int = 0, limit: Union[int, None] = None) -> list[Club]:
    return (
        db.query(models.Club)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_competition_by_id(db: Session, competition_id: str):
    return db.query(models.Competition).filter(models.Competition.competition_id == competition_id.upper()).first()


def get_multi_competition(db: Session, skip: int = 0, limit: Union[int, None] = None) -> list[Competition]:
    return (
        db.query(models.Competition)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_game_by_id(db: Session, game_id: int):
    return db.query(models.Game).filter(models.Game.game_id == game_id).first()


def get_multi_game(db: Session, skip: int = 0, limit: Union[int, None] = None) -> list[Game]:
    return (
        db.query(models.Game)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_player_by_id(db: Session, player_id: int):
    return db.query(models.Player).filter(models.Player.player_id == player_id).first()


def get_multi_player(db: Session, skip: int = 0, limit: Union[int, None] = None) -> list[Player]:
    return (
        db.query(models.Player)
        .offset(skip)
        .limit(limit)
        .all()
    )