from fastapi import FastAPI
from core.config import settings
from api.v1.api import api_router as api_router_v1
# from db.session import engine # We might need this if we use Alembic or create tables directly
# from db.base_class import Base # If we have models to create

# Base.metadata.create_all(bind=engine) # Create database tables - might not be needed if we only inspect

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.include_router(api_router_v1, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint for the API.

    Returns:
        dict: A welcome message.
    """
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# For debugging: print loaded settings
# from pydantic_settings import BaseSettings
# print("Loaded settings:", settings.model_dump())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
