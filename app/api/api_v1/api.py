from fastapi import APIRouter

from app.api.api_v1.endpoints import analytics, clubs, competitions, games, players, simulator
from app.api.api_v1.endpoints import competition_sim

api_router = APIRouter()
api_router.include_router(clubs.router)
api_router.include_router(competitions.router)
api_router.include_router(games.router)
api_router.include_router(players.router)
api_router.include_router(simulator.router)
api_router.include_router(competition_sim.router)
api_router.include_router(analytics.router)
