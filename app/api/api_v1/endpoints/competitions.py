from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/", response_model=list[schemas.Competition])
def read_competitions(db: Session = Depends(deps.get_db), skip: int = 0, limit: Union[int, None] = None):
    """Retrieve list of competitions."""
    db_competition = crud.get_multi_competition(db, skip=skip, limit=limit)
    if db_competition is None:
        raise HTTPException(status_code=404, detail="some error")
    return db_competition


@router.get("/{competition_id}", response_model=schemas.Competition)
def read_competition_by_id(competition_id: str, db: Session = Depends(deps.get_db)):
    db_competition = crud.get_competition_by_id(db, competition_id=competition_id)
    if db_competition is None:
        raise HTTPException(status_code=404, detail="Competition not found")
    return db_competition