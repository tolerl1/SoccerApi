from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models


async def get_club_by_id(db: AsyncSession, club_id: int) -> models.Club | None:
    result = await db.execute(select(models.Club).where(models.Club.club_id == club_id))
    return result.scalar_one_or_none()


async def get_multi_club(db: AsyncSession, skip: int = 0, limit: int | None = None) -> list[models.Club]:
    q = select(models.Club).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_competition_by_id(db: AsyncSession, competition_id: str) -> models.Competition | None:
    result = await db.execute(
        select(models.Competition).where(models.Competition.competition_id == competition_id.upper())
    )
    return result.scalar_one_or_none()


async def get_multi_competition(db: AsyncSession, skip: int = 0, limit: int | None = None) -> list[models.Competition]:
    q = select(models.Competition).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_game_by_id(db: AsyncSession, game_id: int) -> models.Game | None:
    result = await db.execute(select(models.Game).where(models.Game.game_id == game_id))
    return result.scalar_one_or_none()


async def get_multi_game(db: AsyncSession, skip: int = 0, limit: int | None = None) -> list[models.Game]:
    q = select(models.Game).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


async def get_player_by_id(db: AsyncSession, player_id: int) -> models.Player | None:
    result = await db.execute(select(models.Player).where(models.Player.player_id == player_id))
    return result.scalar_one_or_none()


async def get_multi_player(db: AsyncSession, skip: int = 0, limit: int | None = None) -> list[models.Player]:
    q = select(models.Player).offset(skip)
    if limit is not None:
        q = q.limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())
