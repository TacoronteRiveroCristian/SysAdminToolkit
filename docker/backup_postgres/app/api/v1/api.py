from fastapi import APIRouter

from .endpoints import database, data

api_router = APIRouter()

api_router.include_router(database.router, prefix="/db-info", tags=["Database Info (v1)"])
api_router.include_router(data.router, prefix="/data", tags=["Data Extraction (v1)"])
