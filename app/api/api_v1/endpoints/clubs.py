from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/{club_id}", response_model=schemas.Club)
def read_club(club_id: int, db: Session = Depends(deps.get_db)):
    db_club = crud.get_club(db, club_id=club_id)
    if db_club is None:
        raise HTTPException(status_code=404, detail="Club not found")
    return db_club