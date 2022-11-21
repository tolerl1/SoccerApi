from fastapi import FastAPI
from app.api.api_v1.api import api_router


app = FastAPI(
    title='SoccerApi', openapi_url='/api/v1/openapi.json'
)

app.include_router(api_router, prefix='/api/v1')