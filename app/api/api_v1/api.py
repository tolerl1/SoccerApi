from fastapi import APIRouter

from app.api.api_v1.endpoints import clubs, competitions, games, players, simulator
from app.api.api_v1.endpoints import competition_sim, ingest

api_router = APIRouter()
api_router.include_router(clubs.router, prefix='/clubs', tags=['clubs'])
api_router.include_router(competitions.router, prefix='/competitions', tags=['competitions'])
api_router.include_router(games.router, prefix='/games', tags=['games'])
api_router.include_router(players.router, prefix='/players', tags=['players'])
api_router.include_router(simulator.router, prefix='/simulator', tags=['simulator'])
api_router.include_router(competition_sim.router, prefix='/competition-sim', tags=['competition-sim'])
api_router.include_router(ingest.router, prefix='/ingest', tags=['ingest'])