from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import crud, schemas
from app.api.deps import DbSession

router = APIRouter(prefix="/clubs", tags=["clubs"])


@router.get("/")
async def read_clubs(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> list[schemas.Club]:
    """Retrieve list of clubs."""
    return await crud.get_multi_club(db, skip=skip, limit=limit)


@router.get("/{club_id}")
async def read_club_by_id(club_id: int, db: DbSession) -> schemas.Club:
    club = await crud.get_club_by_id(db, club_id=club_id)
    if club is None:
        raise HTTPException(status_code=404, detail="Club not found")
    return club
