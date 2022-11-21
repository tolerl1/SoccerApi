from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/", response_model=list[schemas.Player])
def read_players(db: Session = Depends(deps.get_db), skip: int = 0, limit: Union[int, None] = None):
    """Retrieve list of players."""
    db_player = crud.get_multi_player(db, skip=skip, limit=limit)
    if db_player is None:
        raise HTTPException(status_code=404, detail="some error")
    return db_player


@router.get("/{player_id}", response_model=schemas.Player)
def read_player_by_id(player_id: int, db: Session = Depends(deps.get_db)):
    """Retrieve a player by id."""
    db_player = crud.get_player_by_id(db, player_id=player_id)
    if db_player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return db_player
