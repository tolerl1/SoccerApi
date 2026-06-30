from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api.deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.Player])
async def read_players(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int | None = None):
    """Retrieve list of players."""
    players = await crud.get_multi_player(db, skip=skip, limit=limit)
    if players is None:
        raise HTTPException(status_code=404, detail="some error")
    return players


@router.get("/{player_id}", response_model=schemas.Player)
async def read_player_by_id(player_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve a player by id."""
    player = await crud.get_player_by_id(db, player_id=player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player
