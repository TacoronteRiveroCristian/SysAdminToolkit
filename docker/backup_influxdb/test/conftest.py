"""
Configuración global para pytest
================================

Fixtures y configuraciones globales para todos los tests.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configurar variables de entorno para testing
os.environ["TESTING"] = "true"
os.environ["LOG_LEVEL"] = "DEBUG"


@pytest.fixture(scope="session")
def test_data_dir():
    """Directorio temporal para datos de testing."""
    temp_dir = tempfile.mkdtemp(prefix="influxdb_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_config_dir():
    """Directorio temporal para configuraciones de testing."""
    temp_dir = tempfile.mkdtemp(prefix="influxdb_config_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_log_dir():
    """Directorio temporal para logs de testing."""
    temp_dir = tempfile.mkdtemp(prefix="influxdb_log_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_config_data():
    """Datos de configuración de ejemplo para testing."""
    return {
        "source_server": {
            "url": "http://localhost:8086",
            "user": "admin",
            "password": "password",
            "ssl_verify": False,
        },
        "destination_server": {
            "url": "http://localhost:8087",
            "user": "admin",
            "password": "password",
            "ssl_verify": False,
        },
        "backup_config": {"mode": "full", "page_size": 1000, "timeout": 30},
        "databases": [{"name": "test_db", "destination": "test_db_backup"}],
    }


def pytest_configure(config):
    """Configuración inicial de pytest."""
    # Registrar marcadores personalizados
    config.addinivalue_line(
        "markers", "slow: marca los tests que tardan más tiempo"
    )
    config.addinivalue_line(
        "markers", "integration: marca los tests de integración"
    )
    config.addinivalue_line(
        "markers", "docker: marca los tests que requieren Docker"
    )


def pytest_collection_modifyitems(config, items):
    """Modifica los items de la colección de tests."""
    # Agregar marcadores automáticamente basado en el nombre del archivo
    for item in items:
        if "integration" in item.fspath.basename:
            item.add_marker(pytest.mark.integration)
        if "docker" in item.fspath.basename:
            item.add_marker(pytest.mark.docker)
