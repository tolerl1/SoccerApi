from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import crud, schemas
from app.api.deps import DbSession

router = APIRouter(prefix="/competitions", tags=["competitions"])


@router.get("/")
async def read_competitions(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> list[schemas.Competition]:
    """Retrieve list of competitions."""
    return await crud.get_multi_competition(db, skip=skip, limit=limit)


@router.get("/{competition_id}")
async def read_competition_by_id(competition_id: str, db: DbSession) -> schemas.Competition:
    competition = await crud.get_competition_by_id(db, competition_id=competition_id)
    if competition is None:
        raise HTTPException(status_code=404, detail="Competition not found")
    return competition
