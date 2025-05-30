from fastapi import FastAPI
from core.config import settings
# from api.v1.api import api_router as api_router_v1 # REMOVED V1 ROUTER IMPORT
# from db.session import engine # We might need this if we use Alembic or create tables directly
# from db.base_class import Base # If we have models to create

# Base.metadata.create_all(bind=engine) # Create database tables - might not be needed if we only inspect

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0", # Explicitly set version for OpenAPI doc
    openapi_url=f"/openapi.json" # Main openapi.json, individual versions can have their own too
)

# Conditionally include API versions
if "v1" in settings.ACTIVE_API_VERSIONS:
    from api.v1.api import api_router as api_router_v1
    app.include_router(api_router_v1, prefix=settings.API_V1_STR)
    print("API v1 is active.") # For logging/debugging

if "v2" in settings.ACTIVE_API_VERSIONS:
    from api.v2.api import api_router as api_router_v2
    app.include_router(api_router_v2, prefix=settings.API_V2_STR)
    print("API v2 is active.") # For logging/debugging

if not settings.ACTIVE_API_VERSIONS:
    print("Warning: No API versions are active.")

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
    uvicorn.run(app, host="0.0.0.0", port=settings.FASTAPI_APP_PORT, reload=True)
