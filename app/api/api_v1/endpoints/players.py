from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from app import crud, schemas
from app.api.deps import DbSession

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/")
async def read_players(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int | None, Query(ge=1, le=10_000)] = None,
) -> list[schemas.Player]:
    """Retrieve list of players."""
    return await crud.get_multi_player(db, skip=skip, limit=limit)


@router.get("/{player_id}")
async def read_player_by_id(player_id: int, db: DbSession) -> schemas.Player:
    """Retrieve a player by id."""
    player = await crud.get_player_by_id(db, player_id=player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player
