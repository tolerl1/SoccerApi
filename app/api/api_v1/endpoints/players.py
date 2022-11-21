from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/{player_id}", response_model=schemas.Player)
def read_player(player_id: int, db: Session = Depends(deps.get_db)):
    """Retrieve a player."""
    db_player = crud.get_player(db, player_id=player_id)
    if db_player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return db_player