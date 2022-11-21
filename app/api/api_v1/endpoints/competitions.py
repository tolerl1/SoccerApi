from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import crud, models, schemas
from app.api import deps


router = APIRouter()


@router.get("/{competition_id}", response_model=schemas.Competition)
def read_competition(competition_id: str, db: Session = Depends(deps.get_db)):
    db_competition = crud.get_competition(db, competition_id=competition_id)
    if db_competition is None:
        raise HTTPException(status_code=404, detail="Competition not found")
    return db_competition