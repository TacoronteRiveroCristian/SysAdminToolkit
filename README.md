# SysAdminToolkit

SysAdminToolkit es una colección de utilidades y scripts diseñados para facilitar las operaciones diarias de programadores y administradores de sistemas. Este repositorio funciona como una biblioteca de herramientas reutilizables que cualquier programador puede incorporar fácilmente en su flujo de trabajo.

## Propósito

El objetivo principal de este proyecto es proporcionar soluciones simples y reutilizables para tareas repetitivas o complejas que los programadores y administradores enfrentan regularmente. Cada herramienta está diseñada para:

- Resolver un problema específico sin complicaciones
- Ser independiente y fácil de integrar
- Ahorrar tiempo al evitar "reinventar la rueda"
- Servir como ejemplo práctico de implementación

## Uso

Cada submódulo en este repositorio funciona como un componente independiente. Puedes clonar solo la utilidad específica que necesitas sin tener que descargar todo el repositorio:

```bash
# Clonar todo el repositorio
git clone https://github.com/username/SysAdminToolkit.git

# Clonar solo un directorio/utilidad específica (usando sparse-checkout)
mkdir SysAdminToolkit
cd SysAdminToolkit
git init
git remote add origin https://github.com/username/SysAdminToolkit.git
git config core.sparseCheckout true
echo "docker/backup_influxdb" >> .git/info/sparse-checkout  # Reemplazar con la ruta deseada
git pull origin main
```

## Herramientas disponibles

### Docker

#### backup_influxdb
Herramienta para crear backups entre instancias de InfluxDB, permitiendo filtrar y transferir datos selectivamente.

**Uso**: Navega a `docker/backup_influxdb`, personaliza el archivo de configuración y ejecuta con Docker Compose.

#### backup_postgres
Herramienta API para explorar bases de datos PostgreSQL, empaquetada con Docker Compose y perfiles para desarrollo, producción y testing.

**Uso**: Navega a `docker/backup_postgres` y sigue las instrucciones en su `README.md` local para construir, ejecutar y testear la aplicación.

#### host_monitoring
Sistema de monitorización para hosts usando Prometheus y Grafana.

**Uso**: Navega a `docker/host_monitoring` y sigue las instrucciones en el README local.

### Linux

#### code-server
Configuración para desplegar VS Code en un servidor remoto mediante contenedores.

**Uso**: Consulta los Dockerfiles en `linux/code-server/Dockerfiles` y ajusta según tus necesidades.

#### docker
Scripts y utilidades para gestionar contenedores Docker en entornos Linux.

#### ohmyzsh
Configuraciones y plugins personalizados para Oh My Zsh.

### Miscellaneous

#### backup_influxdb
Versión alternativa de la herramienta de backup para InfluxDB.

#### check_ping
Herramienta para monitorizar conectividad de red y reportar a Telegraf/InfluxDB.

**Uso**: Configura los archivos en `miscellaneous/check_ping/volumes/telegraf` y despliega usando Docker.

#### email_sender
Utilidad simple para enviar correos electrónicos programados o basados en eventos.

#### setup_python_project
Script para configurar rápidamente la estructura de un nuevo proyecto Python con buenas prácticas.

# PostgreSQL Data Explorer API with Docker Compose Profiles

This project provides a FastAPI application for exploring PostgreSQL databases, packaged with Docker Compose for easy environment management.

## Prerequisites

*   Docker
*   Docker Compose (usually included with Docker Desktop)

## Project Structure

*   `docker-compose.yaml`: Defines the services and profiles.
*   `docker/backup_postgres/app/`: Contains the FastAPI application code.
    *   `.env`: **MANUAL STEP REQUIRED**. Create this file based on `.env.example` (if provided) or with your PostgreSQL credentials. It should include:
        ```env
        POSTGRES_SERVER=postgres_db_container # Or your DB host if external
        POSTGRES_USER=your_postgres_user
        POSTGRES_PASSWORD=your_postgres_password
        POSTGRES_DB=your_postgres_db_name
        POSTGRES_PORT=5432
        # Optional: For API configuration
        # PROJECT_NAME="PostgreSQL Data Explorer API"
        # ACTIVE_API_VERSIONS='["v2"]' # JSON-style list as a string: '["v1", "v2"]' or '["v2"]'
        ```
    *   `Dockerfile`: Used to build the FastAPI application and test runner images.
    *   `requirements.txt`: Python dependencies.
    *   `main.py`: FastAPI application entry point.
    *   `tests/`: Contains Pytest integration tests.
*   `docker/backup_postgres/volumes/`: Stores persistent data for PostgreSQL and the application.

## Docker Compose Profiles

This project uses Docker Compose profiles to manage different runtime configurations: `dev`, `prod`, and `test`.

You can activate one or more profiles using the `--profile` flag with `docker-compose` commands.

### 1. Development (`dev`)

This profile is for local development of the FastAPI application.

*   **Services Started:**
    *   `postgres_db`: The PostgreSQL database.
    *   `fastapi_app_dev`: The FastAPI application running with Uvicorn, with hot-reloading enabled. Code changes in `docker/backup_postgres/app/` will automatically restart the server.
*   **API Port (Host):** `8001` (maps to `8000` in the container)
*   **Database Port (Host):** `5432` (or as configured in `.env` via `POSTGRES_PORT`)

**How to Use:**

```bash
# Start services for the dev profile in detached mode
docker-compose --profile dev up -d

# View logs for the dev app
docker-compose --profile dev logs -f fastapi_app_dev

# View logs for the database
docker-compose --profile dev logs -f postgres_db

# Access the API docs (once running)
# Open your browser to: http://localhost:8001/docs

# Stop services
docker-compose --profile dev down
```

### 2. Production-like (`prod`)

This profile simulates a more production-oriented setup for the FastAPI application.

*   **Services Started:**
    *   `postgres_db`: The PostgreSQL database.
    *   `fastapi_app`: The FastAPI application running with Uvicorn (no hot-reloading).
*   **API Port (Host):** `8000`
*   **Database Port (Host):** `5432` (or as configured in `.env` via `POSTGRES_PORT`)

**How to Use:**

```bash
# Start services for the prod profile in detached mode
docker-compose --profile prod up -d

# View logs for the app
docker-compose --profile prod logs -f fastapi_app

# Access the API docs (once running)
# Open your browser to: http://localhost:8000/docs

# Stop services
docker-compose --profile prod down
```

**Note:** For a true production deployment, you would typically use a more robust setup, potentially involving a production-grade ASGI server like Gunicorn managed by Uvicorn workers, HTTPS termination (e.g., via a reverse proxy like Nginx or Traefik), and more sophisticated logging and monitoring.

### 3. Testing (`test`)

This profile is dedicated to running the integration tests.

*   **Services Started:**
    *   `postgres_db`: The PostgreSQL database (tests will create their own schemas/data).
    *   `test_runner`: A container that executes `pytest` against the tests in `docker/backup_postgres/app/tests/`.

**How to Use:**

```bash
# Run the tests. This will build images if needed, start the DB, run tests, then stop.
# The --build flag is good to ensure fresh image for tests.
# The --abort-on-container-exit flag ensures docker-compose exits after tests complete.
docker-compose --profile test up --build --abort-on-container-exit

# If you want to see logs while tests run (or after if not using --abort-on-container-exit):
docker-compose --profile test logs -f test_runner
docker-compose --profile test logs -f postgres_db

# To clean up after tests if you didn't use --abort-on-container-exit or if something was left running:
docker-compose --profile test down
```

## General Docker Compose Commands

*   **Build images without starting containers:**
    ```bash
    docker-compose --profile <profile_name> build
    ```
*   **List running containers for a profile:**
    ```bash
    docker-compose --profile <profile_name> ps
    ```
*   **Stop and remove containers, networks, and volumes (use with caution for volumes):**
    ```bash
    docker-compose --profile <profile_name> down -v # The -v removes named volumes
    ```

## .env File Configuration

Ensure the `.env` file at `docker/backup_postgres/app/.env` is correctly configured with your PostgreSQL credentials and any other necessary settings before running any Docker Compose commands. The `POSTGRES_SERVER` should typically be `postgres_db_container` when running within Docker Compose, as this is the service name for the PostgreSQL container.

For `ACTIVE_API_VERSIONS` in `.env`, use a JSON-style list within a string, for example:
`ACTIVE_API_VERSIONS='["v1", "v2"]'` or `ACTIVE_API_VERSIONS='["v2"]'`.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue o un pull request para mejorar este proyecto. Si quieres añadir una nueva utilidad:

1. Crea un directorio con un nombre descriptivo
2. Incluye un README.md explicando el propósito y uso de la herramienta
3. Organiza el código de manera que sea fácil de entender y reutilizar
4. Agrega ejemplos de uso cuando sea posible

## Licencia

Ver archivo [LICENSE](LICENSE) para más detalles.
