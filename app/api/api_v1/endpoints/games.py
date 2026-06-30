from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.api.deps import get_db

router = APIRouter()


@router.get("/", response_model=list[schemas.Game])
async def read_games(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int | None = None):
    """Retrieve list of games."""
    games = await crud.get_multi_game(db, skip=skip, limit=limit)
    if games is None:
        raise HTTPException(status_code=404, detail="some error")
    return games


@router.get("/{game_id}", response_model=schemas.Game)
async def read_game_by_id(game_id: int, db: AsyncSession = Depends(get_db)):
    game = await crud.get_game_by_id(db, game_id=game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    return game
