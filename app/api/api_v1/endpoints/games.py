from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/{game_id}", response_model=schemas.Game)
def read_game(game_id: int, db: Session = Depends(deps.get_db)):
    db_game = crud.get_game(db, game_id=game_id)
    if db_game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return db_game