from fastapi import APIRouter

from app.api.api_v1.endpoints import clubs, competitions, games, players

api_router = APIRouter()
api_router.include_router(clubs.router, prefix='/clubs', tags=['clubs'])
api_router.include_router(competitions.router, prefix='/competitions', tags=['competitions'])
api_router.include_router(games.router, prefix='/games', tags=['games'])
api_router.include_router(players.router, prefix='/players', tags=['players'])