from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/", response_model=list[schemas.Game])
def read_games(db: Session = Depends(deps.get_db), skip: int = 0, limit: Union[int, None] = None):
    """Retrieve list of games."""
    db_game = crud.get_multi_game(db, skip=skip, limit=limit)
    if db_game is None:
        raise HTTPException(status_code=404, detail="some error")
    return db_game


@router.get("/{game_id}", response_model=schemas.Game)
def read_game_by_id(game_id: int, db: Session = Depends(deps.get_db)):
    db_game = crud.get_game_by_id(db, game_id=game_id)
    if db_game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return db_game