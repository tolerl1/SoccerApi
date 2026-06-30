from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import crud, schemas
from app.api.deps import DbSession

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/")
async def read_games(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> list[schemas.Game]:
    """Retrieve list of games."""
    return await crud.get_multi_game(db, skip=skip, limit=limit)


@router.get("/{game_id}")
async def read_game_by_id(game_id: int, db: DbSession) -> schemas.Game:
    game = await crud.get_game_by_id(db, game_id=game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
