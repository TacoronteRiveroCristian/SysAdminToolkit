from fastapi import APIRouter

from .endpoints import database, data # We will create these endpoint files next

api_router = APIRouter()

api_router.include_router(database.router, prefix="/db-info", tags=["Database Info"])
api_router.include_router(data.router, prefix="/data", tags=["Data Extraction"])

# @api_router.get("/health", tags=["Health"])
# async def health_check():
#     return {"status": "healthy"}
