"""
Configuration module for the PostgreSQL backup service.
Loads configuration from YAML file and environment variables.
"""

import logging
import os
import sys
from typing import Dict, Any

import yaml
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

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
                process_config(item) if isinstance(item, dict) else item
                for item in value
            ]
        elif isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            # Simple environment variable substitution
            env_var = value[2:-1]
            result[key] = os.getenv(env_var, value)
        else:
            result[key] = value

    return result

def load_config(config_path):
    """Load configuration from YAML file with environment variable substitution."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        config = process_config(config)
        print(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        print(f"Error loading YAML configuration: {str(e)}")
        raise

def setup_logging(log_level="INFO", log_file=None):
    """Setup logging configuration for PostgreSQL backup service."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler if log_file is specified
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except Exception as e:
                print(f"Warning: Could not create log directory {log_dir}: {str(e)}")

        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not create file handler for {log_file}: {str(e)}")

    return logger
