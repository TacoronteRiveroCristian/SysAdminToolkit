"""
Configuration module for the InfluxDB backup service.
Loads configuration from YAML file and environment variables.
"""

import logging
import os
import re
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Constants
DEFAULT_CONFIG_PATH = "/app/backup_config.yaml"
ENV_CONFIG_PATH = os.getenv("BACKUP_CONFIG_PATH", DEFAULT_CONFIG_PATH)

# Load configuration
config = {}

# Function to replace environment variables in YAML strings
def replace_env_vars(value: str) -> str:
    """
    Replace ${ENV_VAR} or $ENV_VAR patterns with their environment variable values.

    :param value: String containing environment variable patterns
    :return: String with environment variables replaced
    """
    pattern = r'\$\{([^}^{]+)\}|\$([a-zA-Z_][a-zA-Z0-9_]*)'

    def replace_var(match):
        env_var = match.group(1) or match.group(2)
        # Extract default value if present (${VAR:-default})
        if ':-' in env_var:
            env_var, default = env_var.split(':-', 1)
        else:
            default = ''
        return os.getenv(env_var, default)

    return re.sub(pattern, replace_var, value)

# Function to process YAML config with environment variable substitution
def process_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process configuration dictionary, replacing environment variables.

    :param config_dict: Configuration dictionary
    :return: Processed configuration dictionary
    """
    result = {}

    for key, value in config_dict.items():
        if isinstance(value, dict):
            result[key] = process_config(value)
        elif isinstance(value, list):
            result[key] = [
                process_config(item) if isinstance(item, dict) else
                replace_env_vars(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, str):
            result[key] = replace_env_vars(value)
        else:
            result[key] = value

    return result

# Try to load YAML config
config_path = ENV_CONFIG_PATH
if os.path.isfile(config_path):
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        config = process_config(config)
        print(f"Loaded configuration from {config_path}")
    except Exception as e:
        print(f"Error loading YAML configuration: {str(e)}")
        # Continue without YAML config, will use environment variables
else:
    # Try to find backup_config.yaml in the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    local_config = os.path.join(current_dir, "backup_config.yaml")

    if os.path.isfile(local_config):
        try:
            with open(local_config, 'r') as f:
                config = yaml.safe_load(f)
            config = process_config(config)
            print(f"Loaded configuration from {local_config}")
        except Exception as e:
            print(f"Error loading local YAML configuration: {str(e)}")

# Set up backwards compatibility with environment variables
# Source InfluxDB configuration
SOURCE_URL = os.getenv("SOURCE_URL") or config.get('source', {}).get('url')
SOURCE_USER = os.getenv("SOURCE_USER") or config.get('source', {}).get('user')
SOURCE_PASSWORD = os.getenv("SOURCE_PASSWORD") or config.get('source', {}).get('password')

# Allow empty group_by, but only for non-paginated operations
SOURCE_GROUP_BY = os.getenv("SOURCE_GROUP_BY")
if SOURCE_GROUP_BY is None:
    # If not in env var, check config
    SOURCE_GROUP_BY = config.get('source', {}).get('group_by')
    # If it's empty string or None or just whitespace, make it None
    if SOURCE_GROUP_BY is None or (isinstance(SOURCE_GROUP_BY, str) and not SOURCE_GROUP_BY.strip()):
        SOURCE_GROUP_BY = None
    # Default to '5m' only if not explicitly set to empty or None
    if SOURCE_GROUP_BY is None:
        SOURCE_GROUP_BY = '5m'

# Get databases from either env vars or config
if os.getenv("SOURCE_DBS"):
    SOURCE_DBS = os.getenv("SOURCE_DBS", "").split(",") if os.getenv("SOURCE_DBS") else []
    DEST_DBS = os.getenv("DEST_DBS", "").split(",") if os.getenv("DEST_DBS") else []
elif config.get('source', {}).get('databases'):
    SOURCE_DBS = [db['name'] for db in config.get('source', {}).get('databases', [])]
    DEST_DBS = [db['destination'] for db in config.get('source', {}).get('databases', [])]
else:
    SOURCE_DBS = []
    DEST_DBS = []

# Destination InfluxDB configuration
DEST_URL = os.getenv("DEST_URL") or config.get('destination', {}).get('url')
DEST_USER = os.getenv("DEST_USER") or config.get('destination', {}).get('user')
DEST_PASSWORD = os.getenv("DEST_PASSWORD") or config.get('destination', {}).get('password')

# Measurements to back up (empty means all)
MEASUREMENTS_INCLUDE = config.get('measurements', {}).get('include', [])
MEASUREMENTS_EXCLUDE = config.get('measurements', {}).get('exclude', [])

if os.getenv("MEASUREMENTS"):
    MEASUREMENTS = os.getenv("MEASUREMENTS", "").split(",") if os.getenv("MEASUREMENTS") else []
else:
    MEASUREMENTS = MEASUREMENTS_INCLUDE

# Measurement specific configurations
MEASUREMENTS_CONFIG = config.get('measurements', {}).get('specific', {})

# Backup options
DAYS_OF_PAGINATION = int(os.getenv("DAYS_OF_PAGINATION") or config.get('options', {}).get('days_of_pagination', 7))
TIMEOUT_CLIENT = int(os.getenv("TIMEOUT_CLIENT") or config.get('options', {}).get('timeout_client', 20))

# Cron schedule for backups
BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE") or config.get('options', {}).get('backup_schedule', '')

# Logging configuration
LOG_FILE = os.getenv("LOG_FILE") or config.get('options', {}).get('log_file', '/var/log/backup_influxdb/backup.log')
LOG_LEVEL = os.getenv("LOG_LEVEL") or config.get('options', {}).get('log_level', 'INFO')

# Set up logging
log_dir = os.path.dirname(LOG_FILE)
if not os.path.exists(log_dir):
    try:
        os.makedirs(log_dir)
    except Exception as e:
        print(f"Warning: Could not create log directory {log_dir}: {str(e)}")

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

# Log configuration summary
logger.info("Configuration loaded:")
logger.info(f"SOURCE_URL: {SOURCE_URL}")
logger.info(f"SOURCE_DBS: {SOURCE_DBS}")
logger.info(f"DEST_URL: {DEST_URL}")
logger.info(f"DEST_DBS: {DEST_DBS}")
logger.info(f"MEASUREMENTS include: {MEASUREMENTS_INCLUDE}")
logger.info(f"MEASUREMENTS exclude: {MEASUREMENTS_EXCLUDE}")
logger.info(f"Specific measurement config: {len(MEASUREMENTS_CONFIG)} measurements")

# Validation
if len(SOURCE_DBS) != len(DEST_DBS):
    logger.error("Source and destination databases must have the same number of elements")
    raise ValueError("Source and destination databases must have the same number of elements")

if not SOURCE_URL or not DEST_URL:
    logger.error("Source and destination URLs are required")
    raise ValueError("Source and destination URLs are required")

def get_source_client_params():
    """
    Return parameters for creating a source InfluxDB client.

    :return: Dictionary of parameters for InfluxDBClient
    """
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
    """
    Return parameters for creating a destination InfluxDB client.

    :return: Dictionary of parameters for InfluxDBClient
    """
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


def should_include_measurement(measurement: str) -> bool:
    """
    Determine whether a measurement should be included in the backup.

    :param measurement: Name of the measurement
    :return: True if the measurement should be included, False otherwise
    """
    # If MEASUREMENTS_INCLUDE is not empty, only include measurements in that list
    if MEASUREMENTS_INCLUDE:
        return measurement in MEASUREMENTS_INCLUDE

    # Otherwise, include all measurements except those in MEASUREMENTS_EXCLUDE
    return measurement not in MEASUREMENTS_EXCLUDE


def should_include_field(measurement: str, field_name: str, field_type: str) -> bool:
    """
    Determine whether a field should be included in the backup.

    :param measurement: Name of the measurement
    :param field_name: Name of the field
    :param field_type: Type of the field (numeric, string, boolean)
    :return: True if the field should be included, False otherwise
    """
    # Check if there is specific configuration for this measurement
    if measurement in MEASUREMENTS_CONFIG:
        measurement_config = MEASUREMENTS_CONFIG[measurement]

        # Check if there is specific field configuration
        if 'fields' in measurement_config:
            fields_config = measurement_config['fields']

            # Check if this field type should be included
            if 'types' in fields_config and field_type not in fields_config['types']:
                return False

            # Check include/exclude lists
            include_fields = fields_config.get('include', [])
            exclude_fields = fields_config.get('exclude', [])

            # If include list is not empty, only include fields in that list
            if include_fields:
                return field_name in include_fields

            # Otherwise, include all fields except those in exclude_fields
            return field_name not in exclude_fields

    # No specific configuration for this measurement, include all fields
    return True
