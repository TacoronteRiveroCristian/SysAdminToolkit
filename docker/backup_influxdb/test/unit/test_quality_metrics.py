"""
Tests unitarios para el sistema de métricas de calidad
=====================================================

Tests para verificar el funcionamiento del sistema de métricas de calidad.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta
from test.utils.quality_metrics import (
    MetricResult,
    MetricType,
    QualityMetrics,
    QualityReport,
)

import numpy as np


class TestQualityMetrics(unittest.TestCase):
    """Tests para las métricas de calidad."""

    def setUp(self):
        """Configuración inicial para cada test."""
        self.quality_metrics = QualityMetrics(tolerance=0.01)

    def test_numeric_metrics_identical_data(self):
        """Test para métricas numéricas con datos idénticos."""
        source_data = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        dest_data = source_data.copy()

        metrics = self.quality_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )

        # Verificar que todas las métricas pasaron
        for metric_name, metric in metrics.items():
            self.assertTrue(metric.passed, f"Métrica {metric_name} falló")
            self.assertEqual(
                metric.difference, 0.0, f"Diferencia no cero en {metric_name}"
            )

    def test_numeric_metrics_different_data(self):
        """Test para métricas numéricas con datos diferentes."""
        source_data = [1.0, 2.0, 3.0, 4.0, 5.0] * 100
        dest_data = [
            1.1,
            2.1,
            3.1,
            4.1,
            5.1,
        ] * 100  # Datos con pequeña diferencia

        metrics = self.quality_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )

        # Verificar que algunas métricas fallaron
        failed_metrics = [m for m in metrics.values() if not m.passed]
        self.assertGreater(
            len(failed_metrics), 0, "Debería haber métricas fallidas"
        )

    def test_numeric_metrics_with_nulls(self):
        """Test para métricas numéricas con valores None."""
        source_data = [1.0, 2.0, None, 4.0, 5.0]
        dest_data = [1.0, 2.0, None, 4.0, 5.0]

        metrics = self.quality_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )

        # Verificar que la métrica de conteo considera los nulls
        count_metric = metrics["count"]
        self.assertEqual(count_metric.source_value, 4)
        self.assertEqual(count_metric.destination_value, 4)
        self.assertEqual(count_metric.details["source_nulls"], 1)
        self.assertEqual(count_metric.details["dest_nulls"], 1)

    def test_numeric_metrics_percentiles(self):
        """Test para métricas de percentiles."""
        source_data = list(range(1, 101))  # 1 a 100
        dest_data = source_data.copy()

        metrics = self.quality_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )

        # Verificar que existen métricas de percentiles
        percentile_metrics = [m for m in metrics.keys() if m.startswith("p")]
        expected_percentiles = ["p25", "p50", "p75", "p90", "p95", "p99"]

        for perc in expected_percentiles:
            self.assertIn(
                perc, percentile_metrics, f"Percentil {perc} no encontrado"
            )

    def test_boolean_metrics_identical_data(self):
        """Test para métricas booleanas con datos idénticos."""
        source_data = [True, False, True, False, True] * 100
        dest_data = source_data.copy()

        metrics = self.quality_metrics.calculate_boolean_metrics(
            source_data, dest_data
        )

        # Verificar que todas las métricas pasaron
        for metric_name, metric in metrics.items():
            self.assertTrue(metric.passed, f"Métrica {metric_name} falló")

    def test_boolean_metrics_different_data(self):
        """Test para métricas booleanas con datos diferentes."""
        source_data = [True, False, True, False, True] * 100
        dest_data = [True, True, True, True, True] * 100  # Más True

        metrics = self.quality_metrics.calculate_boolean_metrics(
            source_data, dest_data
        )

        # Verificar que algunas métricas fallaron
        failed_metrics = [m for m in metrics.values() if not m.passed]
        self.assertGreater(
            len(failed_metrics), 0, "Debería haber métricas fallidas"
        )

        # Verificar conteos específicos
        true_count_metric = metrics["true_count"]
        self.assertEqual(true_count_metric.source_value, 250)
        self.assertEqual(true_count_metric.destination_value, 500)

    def test_string_metrics_identical_data(self):
        """Test para métricas de cadenas con datos idénticos."""
        source_data = ["apple", "banana", "cherry", "date"] * 100
        dest_data = source_data.copy()

        metrics = self.quality_metrics.calculate_string_metrics(
            source_data, dest_data
        )

        # Verificar que todas las métricas pasaron
        for metric_name, metric in metrics.items():
            self.assertTrue(metric.passed, f"Métrica {metric_name} falló")

    def test_string_metrics_different_data(self):
        """Test para métricas de cadenas con datos diferentes."""
        source_data = ["apple", "banana", "cherry", "date"] * 100
        dest_data = [
            "apple",
            "banana",
            "cherry",
            "elderberry",
        ] * 100  # Valor diferente

        metrics = self.quality_metrics.calculate_string_metrics(
            source_data, dest_data
        )

        # Verificar que algunas métricas fallaron
        failed_metrics = [m for m in metrics.values() if not m.passed]
        self.assertGreater(
            len(failed_metrics), 0, "Debería haber métricas fallidas"
        )

        # Verificar valores únicos
        unique_count_metric = metrics["unique_count"]
        self.assertEqual(unique_count_metric.source_value, 4)
        self.assertEqual(unique_count_metric.destination_value, 4)
        self.assertIn("date", unique_count_metric.details["missing_values"])
        self.assertIn("elderberry", unique_count_metric.details["extra_values"])

    def test_temporal_metrics_identical_data(self):
        """Test para métricas temporales con datos idénticos."""
        base_time = datetime(2023, 1, 1)
        source_data = [base_time + timedelta(hours=i) for i in range(24)]
        dest_data = source_data.copy()

        metrics = self.quality_metrics.calculate_temporal_metrics(
            source_data, dest_data
        )

        # Verificar que todas las métricas pasaron
        for metric_name, metric in metrics.items():
            self.assertTrue(metric.passed, f"Métrica {metric_name} falló")

    def test_temporal_metrics_different_data(self):
        """Test para métricas temporales con datos diferentes."""
        base_time = datetime(2023, 1, 1)
        source_data = [base_time + timedelta(hours=i) for i in range(24)]
        dest_data = [
            base_time + timedelta(hours=i, seconds=30) for i in range(24)
        ]  # 30 segundos de diferencia

        metrics = self.quality_metrics.calculate_temporal_metrics(
            source_data, dest_data
        )

        # Verificar que algunas métricas fallaron (diferencia > 1 segundo)
        failed_metrics = [m for m in metrics.values() if not m.passed]
        self.assertGreater(
            len(failed_metrics), 0, "Debería haber métricas fallidas"
        )

    def test_compare_datasets_complete(self):
        """Test para comparación completa de datasets."""
        source_data = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [60.0, 61.0, 62.0, 63.0, 64.0],
            "active": [True, True, False, True, False],
            "location": ["room1", "room2", "room1", "room2", "room1"],
        }

        dest_data = source_data.copy()

        report = self.quality_metrics.compare_datasets(
            source_data=source_data,
            dest_data=dest_data,
            measurement_name="test_measurement",
            database_name="test_db",
        )

        # Verificar estructura del reporte
        self.assertIsInstance(report, QualityReport)
        self.assertEqual(report.database_name, "test_db")
        self.assertEqual(report.measurement_name, "test_measurement")
        self.assertGreater(report.total_metrics, 0)
        self.assertEqual(report.passed_metrics, report.total_metrics)
        self.assertEqual(report.failed_metrics, 0)
        self.assertEqual(report.success_rate, 1.0)

    def test_compare_datasets_with_differences(self):
        """Test para comparación de datasets con diferencias."""
        source_data = {
            "temperature": [20.0, 21.0, 22.0, 23.0, 24.0],
            "humidity": [60.0, 61.0, 62.0, 63.0, 64.0],
        }

        dest_data = {
            "temperature": [20.1, 21.1, 22.1, 23.1, 24.1],  # Pequeña diferencia
            "humidity": [60.0, 61.0, 62.0, 63.0, 64.0],
        }

        report = self.quality_metrics.compare_datasets(
            source_data=source_data,
            dest_data=dest_data,
            measurement_name="test_measurement",
            database_name="test_db",
        )

        # Verificar que hay métricas fallidas
        self.assertGreater(report.failed_metrics, 0)
        self.assertLess(report.success_rate, 1.0)

    def test_compare_datasets_missing_fields(self):
        """Test para comparación de datasets con campos faltantes."""
        source_data = {
            "temperature": [20.0, 21.0, 22.0],
            "humidity": [60.0, 61.0, 62.0],
            "pressure": [1013.0, 1014.0, 1015.0],
        }

        dest_data = {
            "temperature": [20.0, 21.0, 22.0],
            "humidity": [60.0, 61.0, 62.0],
            # pressure faltante
        }

        report = self.quality_metrics.compare_datasets(
            source_data=source_data,
            dest_data=dest_data,
            measurement_name="test_measurement",
            database_name="test_db",
        )

        # Verificar que se detectaron campos faltantes
        self.assertIn("pressure", report.summary["missing_fields"])
        self.assertEqual(
            report.summary["total_fields"], 2
        )  # Solo temperature y humidity

    def test_data_type_analysis(self):
        """Test para análisis de tipos de datos."""
        test_data = {
            "numeric_field": [1.0, 2.0, 3.0],
            "boolean_field": [True, False, True],
            "string_field": ["a", "b", "c"],
            "temporal_field": [
                datetime(2023, 1, 1),
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
            ],
            "null_field": [None, None, None],
        }

        data_types = self.quality_metrics._analyze_data_types(test_data)

        self.assertEqual(data_types["numeric_field"], "numeric")
        self.assertEqual(data_types["boolean_field"], "boolean")
        self.assertEqual(data_types["string_field"], "string")
        self.assertEqual(data_types["temporal_field"], "temporal")
        self.assertEqual(data_types["null_field"], "null")

    def test_report_summary_generation(self):
        """Test para generación de resumen de reporte."""
        source_data = {
            "temperature": [20.0, 21.0, 22.0],
            "humidity": [60.0, 61.0, 62.0],
        }

        dest_data = source_data.copy()

        report = self.quality_metrics.compare_datasets(
            source_data=source_data,
            dest_data=dest_data,
            measurement_name="test_measurement",
            database_name="test_db",
        )

        summary = self.quality_metrics.generate_report_summary(report)

        # Verificar que el resumen contiene información clave
        self.assertIn("test_db", summary)
        self.assertIn("test_measurement", summary)
        self.assertIn("Total de métricas", summary)
        self.assertIn("Tasa de éxito", summary)

    def test_report_json_export(self):
        """Test para exportación de reporte a JSON."""
        source_data = {
            "temperature": [20.0, 21.0, 22.0],
            "humidity": [60.0, 61.0, 62.0],
        }

        dest_data = source_data.copy()

        report = self.quality_metrics.compare_datasets(
            source_data=source_data,
            dest_data=dest_data,
            measurement_name="test_measurement",
            database_name="test_db",
        )

        # Crear archivo temporal
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            temp_filename = f.name

        try:
            # Exportar reporte
            self.quality_metrics.export_report_json(report, temp_filename)

            # Verificar que el archivo se creó
            self.assertTrue(os.path.exists(temp_filename))

            # Verificar que el archivo tiene contenido
            with open(temp_filename, "r") as f:
                content = f.read()
                self.assertGreater(len(content), 0)
                self.assertIn("test_db", content)
                self.assertIn("test_measurement", content)

        finally:
            # Limpiar archivo temporal
            if os.path.exists(temp_filename):
                os.unlink(temp_filename)

    def test_tolerance_configuration(self):
        """Test para configuración de tolerancia."""
        # Crear instancia con tolerancia alta
        high_tolerance_metrics = QualityMetrics(tolerance=0.1)

        source_data = [100.0, 200.0, 300.0]
        dest_data = [101.0, 201.0, 301.0]  # 1% de diferencia

        # Con tolerancia alta, debería pasar
        metrics_high = high_tolerance_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )
        high_tolerance_passed = all(m.passed for m in metrics_high.values())

        # Con tolerancia baja, debería fallar
        metrics_low = self.quality_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )
        low_tolerance_passed = all(m.passed for m in metrics_low.values())

        self.assertTrue(
            high_tolerance_passed, "Con tolerancia alta debería pasar"
        )
        self.assertFalse(
            low_tolerance_passed, "Con tolerancia baja debería fallar"
        )

    def test_empty_data_handling(self):
        """Test para manejo de datos vacíos."""
        empty_data = []

        # Métricas numéricas con datos vacíos
        metrics = self.quality_metrics.calculate_numeric_metrics(
            empty_data, empty_data
        )
        count_metric = metrics["count"]
        self.assertEqual(count_metric.source_value, 0)
        self.assertEqual(count_metric.destination_value, 0)
        self.assertTrue(count_metric.passed)

        # Verificar que no se generan otras métricas
        self.assertEqual(len(metrics), 1)  # Solo count

    def test_metric_result_structure(self):
        """Test para estructura de resultados de métricas."""
        source_data = [1.0, 2.0, 3.0]
        dest_data = [1.0, 2.0, 3.0]

        metrics = self.quality_metrics.calculate_numeric_metrics(
            source_data, dest_data
        )

        # Verificar estructura de cada métrica
        for metric_name, metric in metrics.items():
            self.assertIsInstance(metric, MetricResult)
            self.assertIsInstance(metric.metric_name, str)
            self.assertIsInstance(metric.metric_type, MetricType)
            self.assertIsInstance(metric.passed, bool)
            self.assertIsInstance(metric.tolerance, (int, float))
            self.assertIsInstance(metric.details, dict)


if __name__ == "__main__":
    unittest.main()
