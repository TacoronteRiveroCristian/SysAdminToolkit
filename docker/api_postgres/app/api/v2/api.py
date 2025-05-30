from fastapi import APIRouter

from .endpoints import database, data

api_router = APIRouter()

api_router.include_router(database.router, prefix="/db-info", tags=["Database Info"])
api_router.include_router(data.router, prefix="/data", tags=["Data Extraction"])

# You can add a specific health check for v2 if needed
# @api_router.get("/health", tags=["Health"])
# async def health_check_v2():
#     return {"status": "healthy", "version": "v2"}
