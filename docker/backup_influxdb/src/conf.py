"""
Configuration module for the InfluxDB backup service.
Loads environment variables and provides constants for the application.
"""

import logging
import os
from typing import List, Optional

from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Source InfluxDB configuration
SOURCE_URL = os.getenv("SOURCE_URL")
SOURCE_DBS = os.getenv("SOURCE_DBS", "").split(",") if os.getenv("SOURCE_DBS") else []
SOURCE_USER = os.getenv("SOURCE_USER")
SOURCE_PASSWORD = os.getenv("SOURCE_PASSWORD")
SOURCE_GROUP_BY = os.getenv("SOURCE_GROUP_BY", "5m")

# Destination InfluxDB configuration
DEST_URL = os.getenv("DEST_URL")
DEST_DBS = os.getenv("DEST_DBS", "").split(",") if os.getenv("DEST_DBS") else []
DEST_USER = os.getenv("DEST_USER")
DEST_PASSWORD = os.getenv("DEST_PASSWORD")

# Measurements to back up (empty means all)
MEASUREMENTS = os.getenv("MEASUREMENTS", "").split(",") if os.getenv("MEASUREMENTS") else []

# Backup options
DAYS_OF_PAGINATION = int(os.getenv("DAYS_OF_PAGINATION", "7"))
TIMEOUT_CLIENT = int(os.getenv("TIMEOUT_CLIENT", "20"))

# Cron schedule for backups
BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE", "")

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE", "/var/log/backup_influxdb/backup.log")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Set up logging
logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("backup_influxdb")

# Also log to console
console_handler = logging.StreamHandler()
console_handler.setLevel(getattr(logging, LOG_LEVEL))
console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)

# Validation
if len(SOURCE_DBS) != len(DEST_DBS):
    logger.error("Source and destination databases must have the same number of elements")
    raise ValueError("Source and destination databases must have the same number of elements")

if not SOURCE_URL or not DEST_URL:
    logger.error("Source and destination URLs are required")
    raise ValueError("Source and destination URLs are required")

def get_source_client_params():
    """Return parameters for creating a source InfluxDB client."""
    host = SOURCE_URL.split("://")[-1].split(":")[0]
    port = int(SOURCE_URL.split(":")[-1]) if ":" in SOURCE_URL else 8086

    params = {
        "host": host,
        "port": port,
        "timeout": TIMEOUT_CLIENT,
    }

    if SOURCE_USER:
        params["username"] = SOURCE_USER
    if SOURCE_PASSWORD:
        params["password"] = SOURCE_PASSWORD

    return params

def get_dest_client_params():
    """Return parameters for creating a destination InfluxDB client."""
    host = DEST_URL.split("://")[-1].split(":")[0]
    port = int(DEST_URL.split(":")[-1]) if ":" in DEST_URL else 8086

    params = {
        "host": host,
        "port": port,
        "timeout": TIMEOUT_CLIENT,
    }

    if DEST_USER:
        params["username"] = DEST_USER
    if DEST_PASSWORD:
        params["password"] = DEST_PASSWORD

    return params
