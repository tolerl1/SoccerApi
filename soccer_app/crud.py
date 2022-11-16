from sqlalchemy.orm import Session

from . import models, schemas


def get_player(db: Session, player_id: int):
    return db.query(models.Player).filter(models.Player.player_id == player_id).first()

