# PostgreSQL Data Explorer API (backup_postgres Tool)

This directory contains a Dockerized FastAPI application designed to explore PostgreSQL databases. It includes API endpoints for database introspection and data extraction, along with a testing suite.

## Prerequisites

*   Docker
*   Docker Compose (usually included with Docker Desktop)

## Project Structure within `docker/backup_postgres/`

*   `docker-compose.yaml`: Defines the services (`postgres_db`, `fastapi_app_dev`, `fastapi_app`, `test_runner`) and Docker Compose profiles (`dev`, `prod`, `test`) for this specific tool.
*   `app/`: Contains the FastAPI application code.
    *   `.env`: **MANUAL STEP REQUIRED**. Create this file based on the example below or `.env.example` (if provided). It should be placed at `docker/backup_postgres/app/.env`.
        **Example `.env` content for `docker/backup_postgres/app/.env`:**
        ```env
        POSTGRES_SERVER=postgres_db_container_bp # Service name from this docker-compose.yaml
        POSTGRES_USER=your_postgres_user         # Your desired PostgreSQL username
        POSTGRES_PASSWORD=your_postgres_password   # Your desired PostgreSQL password
        POSTGRES_DB=your_postgres_db_name         # Your desired PostgreSQL database name
        POSTGRES_PORT=5432                       # Default PostgreSQL port

        # Optional: For API configuration
        PROJECT_NAME="PostgreSQL Data Explorer API (backup_postgres)"
        # ACTIVE_API_VERSIONS should be a JSON-style list within a string:
        ACTIVE_API_VERSIONS='["v2"]' # e.g., '["v1", "v2"]' or '["v2"]'
        ```
    *   `Dockerfile`: Used to build the FastAPI application and test runner images.
    *   `requirements.txt`: Python dependencies for the application and tests.
    *   `main.py`: FastAPI application entry point.
    *   `core/`, `api/`, `db/`, `schemas/`, `crud/`: Application modules.
    *   `tests/`: Contains Pytest integration tests.
*   `volumes/`: Stores persistent data for PostgreSQL (`postgres_data`) and potentially the application (`fastapi_app_data`), relative to this directory.

## How to Use (Run commands from `docker/backup_postgres/` directory)

**Important:** Navigate to the `docker/backup_postgres/` directory in your terminal before running any `docker-compose` commands for this tool.

```bash
cd docker/backup_postgres
```

### 1. Development (`dev`)

This profile is for local development of the FastAPI application.

*   **Services Started:** `postgres_db`, `fastapi_app_dev` (with hot-reloading).
*   **API Port (Host):** `8001` (maps to `8000` in the container)

**Commands:**

```bash
# Start services for the dev profile (run from docker/backup_postgres/)
docker-compose --profile dev up -d --build

# View logs for the dev app
docker-compose --profile dev logs -f fastapi_app_dev

# Access the API docs (once running)
# Open your browser to: http://localhost:8001/docs

# Stop services
docker-compose --profile dev down
```

### 2. Production-like (`prod`)

This profile simulates a more production-oriented setup.

*   **Services Started:** `postgres_db`, `fastapi_app` (no hot-reloading).
*   **API Port (Host):** `8000`

**Commands:**

```bash
# Start services for the prod profile (run from docker/backup_postgres/)
docker-compose --profile prod up -d --build

# View logs for the app
docker-compose --profile prod logs -f fastapi_app

# Access the API docs (once running)
# Open your browser to: http://localhost:8000/docs

# Stop services
docker-compose --profile prod down
```

### 3. Testing (`test`)

This profile is for running the integration tests.

*   **Services Started:** `postgres_db`, `test_runner`.

**Commands:**

```bash
# Run the tests (run from docker/backup_postgres/)
docker-compose --profile test up --build --abort-on-container-exit

# View logs while tests run (or after if not using --abort-on-container-exit):
docker-compose --profile test logs -f test_runner

# Clean up after tests (if needed):
docker-compose --profile test down
```

## General Docker Compose Commands (run from `docker/backup_postgres/`)

*   **Build images:** `docker-compose --profile <profile_name> build`
*   **List running containers:** `docker-compose --profile <profile_name> ps`
*   **Stop and remove (including volumes):** `docker-compose --profile <profile_name> down -v`

## Dockerfile

The `app/Dockerfile` is used to build the Python environment for both the FastAPI application and the `test_runner` service. It installs dependencies from `app/requirements.txt`.
