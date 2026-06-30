from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api.deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.Competition])
async def read_competitions(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int | None = None):
    """Retrieve list of competitions."""
    competitions = await crud.get_multi_competition(db, skip=skip, limit=limit)
    if competitions is None:
        raise HTTPException(status_code=404, detail="some error")
    return competitions


@router.get("/{competition_id}", response_model=schemas.Competition)
async def read_competition_by_id(competition_id: str, db: AsyncSession = Depends(get_db)):
    competition = await crud.get_competition_by_id(db, competition_id=competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition
