"""
Tests unitarios para el cliente InfluxDB
========================================

Tests para verificar el funcionamiento del cliente InfluxDB usando mocks.
"""

import json
import os

# Importar el cliente desde el proyecto
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.influxdb_client import (
    InfluxDBClient,
    InfluxDBConnectionError,
    InfluxDBError,
    InfluxDBQueryError,
)


class TestInfluxDBClient(unittest.TestCase):
    """Tests para el cliente InfluxDB."""

    def setUp(self):
        """Configuración inicial para cada test."""
        self.client = InfluxDBClient(
            url="http://localhost:8086",
            username="admin",
            password="password",
            ssl_verify=False,
            timeout=30,
        )

    @patch("src.influxdb_client.requests.Session.get")
    def test_test_connection_success(self, mock_get):
        """Test para conexión exitosa."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # Ejecutar test
        result = self.client.test_connection()

        # Verificar resultado
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch("src.influxdb_client.requests.Session.get")
    def test_test_connection_failure(self, mock_get):
        """Test para fallo de conexión."""
        # Configurar mock para lanzar excepción
        mock_get.side_effect = requests.exceptions.ConnectionError(
            "Connection failed"
        )

        # Ejecutar test
        result = self.client.test_connection()

        # Verificar resultado
        self.assertFalse(result)

    @patch("src.influxdb_client.requests.Session.get")
    def test_create_database_success(self, mock_get):
        """Test para creación exitosa de base de datos."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_get.return_value = mock_response

        # Ejecutar test
        result = self.client.create_database("test_db")

        # Verificar resultado
        self.assertTrue(result)
        mock_get.assert_called_once()

    @patch("src.influxdb_client.requests.Session.get")
    def test_get_databases(self, mock_get):
        """Test para obtener lista de bases de datos."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "databases",
                            "columns": ["name"],
                            "values": [["db1"], ["db2"], ["db3"]],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        databases = self.client.get_databases()

        # Verificar resultado
        self.assertEqual(databases, ["db1", "db2", "db3"])
        mock_get.assert_called_once()

    @patch("src.influxdb_client.requests.Session.get")
    def test_get_measurements(self, mock_get):
        """Test para obtener lista de mediciones."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "measurements",
                            "columns": ["name"],
                            "values": [["measurement1"], ["measurement2"]],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        measurements = self.client.get_measurements("test_db")

        # Verificar resultado
        self.assertEqual(measurements, ["measurement1", "measurement2"])

    @patch("src.influxdb_client.requests.Session.get")
    def test_get_field_keys(self, mock_get):
        """Test para obtener claves de campos."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "measurement1",
                            "columns": ["fieldKey", "fieldType"],
                            "values": [
                                ["field1", "float"],
                                ["field2", "integer"],
                                ["field3", "string"],
                            ],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        field_keys = self.client.get_field_keys("test_db", "measurement1")

        # Verificar resultado
        expected = {"field1": "float", "field2": "integer", "field3": "string"}
        self.assertEqual(field_keys, expected)

    @patch("src.influxdb_client.requests.Session.get")
    def test_query_data_success(self, mock_get):
        """Test para consulta exitosa de datos."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "measurement1",
                            "columns": ["time", "field1", "field2"],
                            "values": [
                                ["2023-01-01T00:00:00Z", 10.5, 20],
                                ["2023-01-01T01:00:00Z", 11.5, 21],
                            ],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 1, 2)
        data = self.client.query_data(
            "test_db", "measurement1", start_time, end_time
        )

        # Verificar resultado
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["field1"], 10.5)
        self.assertEqual(data[0]["field2"], 20)

    @patch("src.influxdb_client.requests.Session.post")
    def test_write_data_success(self, mock_post):
        """Test para escritura exitosa de datos."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        # Preparar datos de prueba
        records = [
            {
                "measurement": "test_measurement",
                "time": datetime(2023, 1, 1),
                "fields": {"value": 10.5},
                "tags": {"host": "server1"},
            }
        ]

        # Ejecutar test
        result = self.client.write_data("test_db", "test_measurement", records)

        # Verificar resultado
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch("src.influxdb_client.requests.Session.post")
    def test_write_data_failure(self, mock_post):
        """Test para fallo en escritura de datos."""
        # Configurar mock response para error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        # Preparar datos de prueba
        records = [
            {
                "measurement": "test_measurement",
                "time": datetime(2023, 1, 1),
                "fields": {"value": 10.5},
                "tags": {"host": "server1"},
            }
        ]

        # Ejecutar test y verificar excepción
        with self.assertRaises(Exception):  # Debería lanzar InfluxDBWriteError
            self.client.write_data("test_db", "test_measurement", records)

    @patch("src.influxdb_client.requests.Session.get")
    def test_count_records(self, mock_get):
        """Test para contar registros."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "measurement1",
                            "columns": ["time", "count"],
                            "values": [["1970-01-01T00:00:00Z", 1000]],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        count = self.client.count_records("test_db", "measurement1")

        # Verificar resultado
        self.assertEqual(count, 1000)

    @patch("src.influxdb_client.requests.Session.get")
    def test_get_time_range(self, mock_get):
        """Test para obtener rango temporal."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "measurement1",
                            "columns": ["time", "min", "max"],
                            "values": [
                                [
                                    "1970-01-01T00:00:00Z",
                                    "2023-01-01T00:00:00Z",
                                    "2023-01-02T00:00:00Z",
                                ]
                            ],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        time_range = self.client.get_time_range("test_db", "measurement1")

        # Verificar resultado
        self.assertIsNotNone(time_range[0])
        self.assertIsNotNone(time_range[1])
        self.assertIsInstance(time_range[0], datetime)
        self.assertIsInstance(time_range[1], datetime)

    def test_url_building(self):
        """Test para construcción de URLs."""
        # Test query URL
        params = {"q": "SHOW DATABASES", "db": "test_db"}
        url = self.client._build_query_url(params)
        self.assertIn("query", url)
        self.assertIn("SHOW%20DATABASES", url)

        # Test write URL
        url = self.client._build_write_url("test_db", "ns")
        self.assertIn("write", url)
        self.assertIn("db=test_db", url)
        self.assertIn("precision=ns", url)

    @patch("src.influxdb_client.requests.Session.get")
    def test_query_error_handling(self, mock_get):
        """Test para manejo de errores en consultas."""
        # Configurar mock response con error
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Syntax error"
        mock_get.return_value = mock_response

        # Ejecutar test y verificar excepción
        with self.assertRaises(Exception):  # Debería lanzar InfluxDBQueryError
            self.client._execute_query("INVALID QUERY")

    @patch("src.influxdb_client.requests.Session.get")
    def test_json_response_error(self, mock_get):
        """Test para manejo de errores en response JSON."""
        # Configurar mock response con error en JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"error": "Database not found"}
        mock_get.return_value = mock_response

        # Ejecutar test y verificar excepción
        with self.assertRaises(Exception):  # Debería lanzar InfluxDBQueryError
            self.client._execute_query("SHOW DATABASES")

    @patch("src.influxdb_client.requests.Session.get")
    def test_connection_timeout(self, mock_get):
        """Test para timeout de conexión."""
        # Configurar mock para timeout
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        # Ejecutar test y verificar excepción
        with self.assertRaises(
            Exception
        ):  # Debería lanzar InfluxDBConnectionError
            self.client._execute_query("SHOW DATABASES")

    def test_client_configuration(self):
        """Test para configuración del cliente."""
        # Verificar configuración inicial
        self.assertEqual(self.client.url, "http://localhost:8086")
        self.assertEqual(self.client.username, "admin")
        self.assertEqual(self.client.password, "password")
        self.assertEqual(self.client.timeout, 30)
        self.assertEqual(self.client.ssl_verify, False)

        # Verificar sesión HTTP
        self.assertIsInstance(self.client.session, requests.Session)
        self.assertEqual(self.client.session.auth, ("admin", "password"))
        self.assertEqual(self.client.session.verify, False)

    def test_client_without_auth(self):
        """Test para cliente sin autenticación."""
        client = InfluxDBClient(url="http://localhost:8086")

        self.assertIsNone(client.username)
        self.assertIsNone(client.password)
        self.assertIsNone(client.session.auth)

    def test_repr_method(self):
        """Test para método __repr__."""
        repr_str = repr(self.client)
        self.assertIn("InfluxDBClient", repr_str)
        self.assertIn("localhost:8086", repr_str)

    def test_context_manager(self):
        """Test para uso como context manager."""
        with patch.object(self.client, "close") as mock_close:
            with self.client as client:
                self.assertEqual(client, self.client)
            mock_close.assert_called_once()

    @patch("src.influxdb_client.requests.Session.get")
    def test_database_exists_true(self, mock_get):
        """Test para verificar que base de datos existe."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "databases",
                            "columns": ["name"],
                            "values": [["test_db"], ["other_db"]],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        exists = self.client.database_exists("test_db")

        # Verificar resultado
        self.assertTrue(exists)

    @patch("src.influxdb_client.requests.Session.get")
    def test_database_exists_false(self, mock_get):
        """Test para verificar que base de datos no existe."""
        # Configurar mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "series": [
                        {
                            "name": "databases",
                            "columns": ["name"],
                            "values": [["other_db"]],
                        }
                    ]
                }
            ]
        }
        mock_get.return_value = mock_response

        # Ejecutar test
        exists = self.client.database_exists("test_db")

        # Verificar resultado
        self.assertFalse(exists)


if __name__ == "__main__":
    unittest.main()
