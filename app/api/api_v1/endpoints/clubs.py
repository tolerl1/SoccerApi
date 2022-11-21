from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/", response_model=list[schemas.Club])
def read_clubs(db: Session = Depends(deps.get_db), skip: int = 0, limit: Union[int, None] = None):
    """Retrieve list of clubs."""
    db_club = crud.get_multi_club(db, skip=skip, limit=limit)
    if db_club is None:
        raise HTTPException(status_code=404, detail="some error")
    return db_club


@router.get("/{club_id}", response_model=schemas.Club)
def read_club_by_id(club_id: int, db: Session = Depends(deps.get_db)):
    db_club = crud.get_club_by_id(db, club_id=club_id)
    if db_club is None:
        raise HTTPException(status_code=404, detail="Club not found")
    return db_club