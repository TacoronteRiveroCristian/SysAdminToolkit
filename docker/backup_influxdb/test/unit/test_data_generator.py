"""
Tests unitarios para el generador de datos
==========================================

Tests para verificar el funcionamiento del generador de datos heterogéneos.
"""

import unittest
from datetime import datetime, timedelta
from test.data.data_generator import DataGenerator
from test.data.test_datasets import get_dataset_config

import numpy as np


class TestDataGenerator(unittest.TestCase):
    """Tests para el generador de datos."""

    def setUp(self):
        """Configuración inicial para cada test."""
        self.generator = DataGenerator(seed=42)

    def test_numeric_data_normal(self):
        """Test para datos numéricos con distribución normal."""
        data = self.generator.generate_numeric_data(
            count=1000, data_type="normal", mean=50.0, std=10.0
        )

        # Verificar longitud
        self.assertEqual(len(data), 1000)

        # Verificar que son números
        self.assertTrue(all(isinstance(x, (int, float)) for x in data))

        # Verificar distribución aproximada
        mean = np.mean(data)
        std = np.std(data)
        self.assertAlmostEqual(mean, 50.0, delta=2.0)
        self.assertAlmostEqual(std, 10.0, delta=2.0)

    def test_numeric_data_uniform(self):
        """Test para datos numéricos con distribución uniforme."""
        data = self.generator.generate_numeric_data(
            count=1000, data_type="uniform", low=0.0, high=100.0
        )

        # Verificar longitud
        self.assertEqual(len(data), 1000)

        # Verificar rango
        self.assertTrue(all(0.0 <= x <= 100.0 for x in data))

        # Verificar distribución aproximada
        mean = np.mean(data)
        self.assertAlmostEqual(mean, 50.0, delta=5.0)

    def test_numeric_data_seasonal(self):
        """Test para datos numéricos con patrón estacional."""
        data = self.generator.generate_numeric_data(
            count=1440,  # 1 día con resolución de 1 minuto
            data_type="seasonal",
            amplitude=10.0,
            period=1440,
            offset=20.0,
        )

        # Verificar longitud
        self.assertEqual(len(data), 1440)

        # Verificar que oscila alrededor del offset
        mean = np.mean(data)
        self.assertAlmostEqual(mean, 20.0, delta=3.0)

    def test_boolean_data(self):
        """Test para datos booleanos."""
        data = self.generator.generate_boolean_data(
            count=1000, true_probability=0.7
        )

        # Verificar longitud
        self.assertEqual(len(data), 1000)

        # Verificar que son booleanos
        self.assertTrue(all(isinstance(x, bool) for x in data))

        # Verificar proporción aproximada
        true_count = sum(data)
        true_ratio = true_count / len(data)
        self.assertAlmostEqual(true_ratio, 0.7, delta=0.1)

    def test_string_data_random(self):
        """Test para datos de cadenas aleatorias."""
        data = self.generator.generate_string_data(
            count=100, data_type="random", length=10
        )

        # Verificar longitud
        self.assertEqual(len(data), 100)

        # Verificar que son cadenas
        self.assertTrue(all(isinstance(x, str) for x in data))

        # Verificar longitud de cadenas
        self.assertTrue(all(len(x) == 10 for x in data))

    def test_string_data_enum(self):
        """Test para datos de cadenas con valores enumerados."""
        values = ["A", "B", "C", "D"]
        data = self.generator.generate_string_data(
            count=100, data_type="enum", values=values
        )

        # Verificar longitud
        self.assertEqual(len(data), 100)

        # Verificar que todos los valores están en la lista
        self.assertTrue(all(x in values for x in data))

        # Verificar que se usan todos los valores
        unique_values = set(data)
        self.assertEqual(len(unique_values), len(values))

    def test_timestamp_series(self):
        """Test para series temporales."""
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 1, 2)

        timestamps = self.generator.generate_timestamp_series(
            start_time=start_time, end_time=end_time, interval="1h"
        )

        # Verificar longitud (24 horas + 1 punto inicial)
        self.assertEqual(len(timestamps), 25)

        # Verificar que son datetime
        self.assertTrue(all(isinstance(x, datetime) for x in timestamps))

        # Verificar orden temporal
        self.assertEqual(timestamps, sorted(timestamps))

        # Verificar rango
        self.assertEqual(timestamps[0], start_time)
        self.assertEqual(timestamps[-1], end_time)

    def test_measurement_data_generation(self):
        """Test para generación de datos de medición completa."""
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 1, 1, 1, 0)  # 1 hora

        field_configs = {
            "temperature": {"type": "normal", "mean": 25.0, "std": 5.0},
            "humidity": {"type": "uniform", "low": 40.0, "high": 80.0},
            "active": {"type": "boolean", "true_probability": 0.8},
        }

        tag_configs = {
            "sensor_id": {"type": "enum", "values": ["s1", "s2", "s3"]},
            "location": {"type": "enum", "values": ["room1", "room2"]},
        }

        records = self.generator.generate_measurement_data(
            measurement_name="sensor_data",
            start_time=start_time,
            end_time=end_time,
            interval="1m",
            field_configs=field_configs,
            tag_configs=tag_configs,
        )

        # Verificar longitud (60 minutos + 1 punto inicial)
        self.assertEqual(len(records), 61)

        # Verificar estructura de registros
        for record in records:
            self.assertIn("measurement", record)
            self.assertIn("time", record)
            self.assertIn("fields", record)
            self.assertIn("tags", record)

            # Verificar campos
            self.assertEqual(
                set(record["fields"].keys()), set(field_configs.keys())
            )
            self.assertEqual(
                set(record["tags"].keys()), set(tag_configs.keys())
            )

    def test_complex_dataset_generation(self):
        """Test para generación de dataset complejo."""
        # Usar configuración de dataset IoT
        dataset_config = get_dataset_config("iot")

        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 1, 1, 1, 0)  # 1 hora

        dataset = self.generator.generate_complex_dataset(
            database_name="test_db",
            start_time=start_time,
            end_time=end_time,
            measurements=dataset_config,
        )

        # Verificar que se generaron todas las mediciones
        expected_measurements = set(dataset_config.keys())
        actual_measurements = set(dataset.keys())
        self.assertEqual(expected_measurements, actual_measurements)

        # Verificar que cada medición tiene registros
        for measurement_name, records in dataset.items():
            self.assertGreater(len(records), 0)

            # Verificar estructura de primer registro
            first_record = records[0]
            self.assertIn("measurement", first_record)
            self.assertIn("time", first_record)
            self.assertIn("fields", first_record)
            self.assertIn("tags", first_record)

            self.assertEqual(first_record["measurement"], measurement_name)

    def test_anomaly_injection(self):
        """Test para inyección de anomalías."""
        # Generar datos normales
        normal_data = self.generator.generate_numeric_data(
            count=1000, data_type="normal", mean=50.0, std=10.0
        )

        # Inyectar anomalías
        anomalous_data = self.generator.generate_anomalies(
            data=normal_data, anomaly_rate=0.1, anomaly_type="outlier"
        )

        # Verificar longitud
        self.assertEqual(len(anomalous_data), len(normal_data))

        # Verificar que hay valores extremos
        normal_std = np.std(normal_data)
        anomalous_std = np.std([x for x in anomalous_data if x is not None])

        # Los datos con anomalías deberían tener mayor dispersión
        self.assertGreater(anomalous_std, normal_std)

    def test_reproducibility(self):
        """Test para verificar reproducibilidad con semilla."""
        # Generar datos con la misma semilla
        gen1 = DataGenerator(seed=123)
        gen2 = DataGenerator(seed=123)

        data1 = gen1.generate_numeric_data(count=100, data_type="normal")
        data2 = gen2.generate_numeric_data(count=100, data_type="normal")

        # Deberían ser idénticos
        self.assertEqual(data1, data2)

        # Generar datos con semilla diferente
        gen3 = DataGenerator(seed=456)
        data3 = gen3.generate_numeric_data(count=100, data_type="normal")

        # Deberían ser diferentes
        self.assertNotEqual(data1, data3)

    def test_edge_cases(self):
        """Test para casos extremos."""
        # Datos con count=0
        data = self.generator.generate_numeric_data(count=0, data_type="normal")
        self.assertEqual(len(data), 0)

        # Datos con parámetros extremos
        data = self.generator.generate_numeric_data(
            count=10, data_type="normal", mean=0.0, std=0.0
        )
        # Todos los valores deberían ser iguales
        self.assertTrue(all(x == data[0] for x in data))

        # Probabilidad extrema para booleanos
        data = self.generator.generate_boolean_data(
            count=100, true_probability=0.0
        )
        self.assertTrue(all(x == False for x in data))

        data = self.generator.generate_boolean_data(
            count=100, true_probability=1.0
        )
        self.assertTrue(all(x == True for x in data))


if __name__ == "__main__":
    unittest.main()
