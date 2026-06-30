from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api.deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.Club])
async def read_clubs(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int | None = None):
    """Retrieve list of clubs."""
    clubs = await crud.get_multi_club(db, skip=skip, limit=limit)
    if clubs is None:
        raise HTTPException(status_code=404, detail="some error")
    return clubs


@router.get("/{club_id}", response_model=schemas.Club)
async def read_club_by_id(club_id: int, db: AsyncSession = Depends(get_db)):
    club = await crud.get_club_by_id(db, club_id=club_id)
    if club is None:
        raise HTTPException(status_code=404, detail="Club not found")
    return club
