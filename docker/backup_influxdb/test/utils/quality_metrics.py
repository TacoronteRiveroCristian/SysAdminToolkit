"""
Sistema de métricas de calidad de datos
=====================================

Verifica la integridad y calidad de los datos tras el backup
mediante métricas estadísticas y comparaciones detalladas.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import json


class MetricType(Enum):
    """Tipos de métricas disponibles."""
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    STRING = "string"
    TEMPORAL = "temporal"
    COUNT = "count"


@dataclass
class MetricResult:
    """Resultado de una métrica de calidad."""
    metric_name: str
    metric_type: MetricType
    source_value: Any
    destination_value: Any
    difference: Any
    tolerance: float
    passed: bool
    details: Dict[str, Any]


@dataclass
class QualityReport:
    """Reporte completo de calidad de datos."""
    database_name: str
    measurement_name: str
    timestamp: datetime
    total_metrics: int
    passed_metrics: int
    failed_metrics: int
    success_rate: float
    metrics: List[MetricResult]
    summary: Dict[str, Any]


class QualityMetrics:
    """
    Sistema de métricas de calidad de datos.

    Verifica la integridad y calidad de los datos comparando
    origen y destino tras el backup.
    """

    def __init__(self, tolerance: float = 0.01):
        """
        Inicializa el sistema de métricas.

        Args:
            tolerance: Tolerancia por defecto para comparaciones
        """
        self.tolerance = tolerance
        self.logger = logging.getLogger(__name__)

    def calculate_numeric_metrics(self,
                                source_data: List[float],
                                dest_data: List[float],
                                tolerance: float = None) -> Dict[str, MetricResult]:
        """
        Calcula métricas para datos numéricos.

        Args:
            source_data: Datos origen
            dest_data: Datos destino
            tolerance: Tolerancia específica

        Returns:
            Dict[str, MetricResult]: Métricas calculadas
        """
        if tolerance is None:
            tolerance = self.tolerance

        # Limpiar datos None
        source_clean = [x for x in source_data if x is not None]
        dest_clean = [x for x in dest_data if x is not None]

        metrics = {}

        # Conteo de registros
        count_metric = MetricResult(
            metric_name="count",
            metric_type=MetricType.COUNT,
            source_value=len(source_clean),
            destination_value=len(dest_clean),
            difference=len(dest_clean) - len(source_clean),
            tolerance=0,
            passed=len(source_clean) == len(dest_clean),
            details={
                "source_nulls": len(source_data) - len(source_clean),
                "dest_nulls": len(dest_data) - len(dest_clean)
            }
        )
        metrics["count"] = count_metric

        if len(source_clean) == 0 or len(dest_clean) == 0:
            self.logger.warning("No hay datos para comparar")
            return metrics

        # Convertir a numpy arrays
        source_array = np.array(source_clean)
        dest_array = np.array(dest_clean)

        # Media
        source_mean = np.mean(source_array)
        dest_mean = np.mean(dest_array)
        mean_diff = abs(dest_mean - source_mean)
        mean_tolerance = abs(source_mean * tolerance)

        mean_metric = MetricResult(
            metric_name="mean",
            metric_type=MetricType.NUMERIC,
            source_value=source_mean,
            destination_value=dest_mean,
            difference=mean_diff,
            tolerance=mean_tolerance,
            passed=mean_diff <= mean_tolerance,
            details={"relative_error": mean_diff / abs(source_mean) if source_mean != 0 else 0}
        )
        metrics["mean"] = mean_metric

        # Mediana
        source_median = np.median(source_array)
        dest_median = np.median(dest_array)
        median_diff = abs(dest_median - source_median)
        median_tolerance = abs(source_median * tolerance)

        median_metric = MetricResult(
            metric_name="median",
            metric_type=MetricType.NUMERIC,
            source_value=source_median,
            destination_value=dest_median,
            difference=median_diff,
            tolerance=median_tolerance,
            passed=median_diff <= median_tolerance,
            details={"relative_error": median_diff / abs(source_median) if source_median != 0 else 0}
        )
        metrics["median"] = median_metric

        # Desviación estándar
        source_std = np.std(source_array)
        dest_std = np.std(dest_array)
        std_diff = abs(dest_std - source_std)
        std_tolerance = abs(source_std * tolerance)

        std_metric = MetricResult(
            metric_name="std",
            metric_type=MetricType.NUMERIC,
            source_value=source_std,
            destination_value=dest_std,
            difference=std_diff,
            tolerance=std_tolerance,
            passed=std_diff <= std_tolerance,
            details={"relative_error": std_diff / abs(source_std) if source_std != 0 else 0}
        )
        metrics["std"] = std_metric

        # Percentiles
        for percentile in [25, 50, 75, 90, 95, 99]:
            source_perc = np.percentile(source_array, percentile)
            dest_perc = np.percentile(dest_array, percentile)
            perc_diff = abs(dest_perc - source_perc)
            perc_tolerance = abs(source_perc * tolerance)

            perc_metric = MetricResult(
                metric_name=f"p{percentile}",
                metric_type=MetricType.NUMERIC,
                source_value=source_perc,
                destination_value=dest_perc,
                difference=perc_diff,
                tolerance=perc_tolerance,
                passed=perc_diff <= perc_tolerance,
                details={"relative_error": perc_diff / abs(source_perc) if source_perc != 0 else 0}
            )
            metrics[f"p{percentile}"] = perc_metric

        # Mínimo y máximo
        source_min = np.min(source_array)
        dest_min = np.min(dest_array)
        min_diff = abs(dest_min - source_min)
        min_tolerance = abs(source_min * tolerance)

        min_metric = MetricResult(
            metric_name="min",
            metric_type=MetricType.NUMERIC,
            source_value=source_min,
            destination_value=dest_min,
            difference=min_diff,
            tolerance=min_tolerance,
            passed=min_diff <= min_tolerance,
            details={"relative_error": min_diff / abs(source_min) if source_min != 0 else 0}
        )
        metrics["min"] = min_metric

        source_max = np.max(source_array)
        dest_max = np.max(dest_array)
        max_diff = abs(dest_max - source_max)
        max_tolerance = abs(source_max * tolerance)

        max_metric = MetricResult(
            metric_name="max",
            metric_type=MetricType.NUMERIC,
            source_value=source_max,
            destination_value=dest_max,
            difference=max_diff,
            tolerance=max_tolerance,
            passed=max_diff <= max_tolerance,
            details={"relative_error": max_diff / abs(source_max) if source_max != 0 else 0}
        )
        metrics["max"] = max_metric

        return metrics

    def calculate_boolean_metrics(self,
                                source_data: List[bool],
                                dest_data: List[bool]) -> Dict[str, MetricResult]:
        """
        Calcula métricas para datos booleanos.

        Args:
            source_data: Datos origen
            dest_data: Datos destino

        Returns:
            Dict[str, MetricResult]: Métricas calculadas
        """
        metrics = {}

        # Limpiar datos None
        source_clean = [x for x in source_data if x is not None]
        dest_clean = [x for x in dest_data if x is not None]

        # Conteo de registros
        count_metric = MetricResult(
            metric_name="count",
            metric_type=MetricType.COUNT,
            source_value=len(source_clean),
            destination_value=len(dest_clean),
            difference=len(dest_clean) - len(source_clean),
            tolerance=0,
            passed=len(source_clean) == len(dest_clean),
            details={
                "source_nulls": len(source_data) - len(source_clean),
                "dest_nulls": len(dest_data) - len(dest_clean)
            }
        )
        metrics["count"] = count_metric

        if len(source_clean) == 0 or len(dest_clean) == 0:
            return metrics

        # Conteo de True
        source_true_count = sum(source_clean)
        dest_true_count = sum(dest_clean)
        true_count_diff = abs(dest_true_count - source_true_count)

        true_count_metric = MetricResult(
            metric_name="true_count",
            metric_type=MetricType.BOOLEAN,
            source_value=source_true_count,
            destination_value=dest_true_count,
            difference=true_count_diff,
            tolerance=0,
            passed=true_count_diff == 0,
            details={}
        )
        metrics["true_count"] = true_count_metric

        # Conteo de False
        source_false_count = len(source_clean) - source_true_count
        dest_false_count = len(dest_clean) - dest_true_count
        false_count_diff = abs(dest_false_count - source_false_count)

        false_count_metric = MetricResult(
            metric_name="false_count",
            metric_type=MetricType.BOOLEAN,
            source_value=source_false_count,
            destination_value=dest_false_count,
            difference=false_count_diff,
            tolerance=0,
            passed=false_count_diff == 0,
            details={}
        )
        metrics["false_count"] = false_count_metric

        # Proporción de True
        source_true_ratio = source_true_count / len(source_clean)
        dest_true_ratio = dest_true_count / len(dest_clean)
        true_ratio_diff = abs(dest_true_ratio - source_true_ratio)

        true_ratio_metric = MetricResult(
            metric_name="true_ratio",
            metric_type=MetricType.BOOLEAN,
            source_value=source_true_ratio,
            destination_value=dest_true_ratio,
            difference=true_ratio_diff,
            tolerance=self.tolerance,
            passed=true_ratio_diff <= self.tolerance,
            details={}
        )
        metrics["true_ratio"] = true_ratio_metric

        return metrics

    def calculate_string_metrics(self,
                               source_data: List[str],
                               dest_data: List[str]) -> Dict[str, MetricResult]:
        """
        Calcula métricas para datos de cadenas.

        Args:
            source_data: Datos origen
            dest_data: Datos destino

        Returns:
            Dict[str, MetricResult]: Métricas calculadas
        """
        metrics = {}

        # Limpiar datos None
        source_clean = [x for x in source_data if x is not None]
        dest_clean = [x for x in dest_data if x is not None]

        # Conteo de registros
        count_metric = MetricResult(
            metric_name="count",
            metric_type=MetricType.COUNT,
            source_value=len(source_clean),
            destination_value=len(dest_clean),
            difference=len(dest_clean) - len(source_clean),
            tolerance=0,
            passed=len(source_clean) == len(dest_clean),
            details={
                "source_nulls": len(source_data) - len(source_clean),
                "dest_nulls": len(dest_data) - len(dest_clean)
            }
        )
        metrics["count"] = count_metric

        if len(source_clean) == 0 or len(dest_clean) == 0:
            return metrics

        # Valores únicos
        source_unique = set(source_clean)
        dest_unique = set(dest_clean)
        unique_count_diff = abs(len(dest_unique) - len(source_unique))

        unique_count_metric = MetricResult(
            metric_name="unique_count",
            metric_type=MetricType.STRING,
            source_value=len(source_unique),
            destination_value=len(dest_unique),
            difference=unique_count_diff,
            tolerance=0,
            passed=unique_count_diff == 0,
            details={
                "source_unique_values": sorted(list(source_unique)),
                "dest_unique_values": sorted(list(dest_unique)),
                "missing_values": sorted(list(source_unique - dest_unique)),
                "extra_values": sorted(list(dest_unique - source_unique))
            }
        )
        metrics["unique_count"] = unique_count_metric

        # Longitud promedio de cadenas
        source_avg_length = np.mean([len(str(x)) for x in source_clean])
        dest_avg_length = np.mean([len(str(x)) for x in dest_clean])
        avg_length_diff = abs(dest_avg_length - source_avg_length)

        avg_length_metric = MetricResult(
            metric_name="avg_length",
            metric_type=MetricType.STRING,
            source_value=source_avg_length,
            destination_value=dest_avg_length,
            difference=avg_length_diff,
            tolerance=source_avg_length * self.tolerance,
            passed=avg_length_diff <= source_avg_length * self.tolerance,
            details={}
        )
        metrics["avg_length"] = avg_length_metric

        # Distribución de valores (top 10)
        source_counts = pd.Series(source_clean).value_counts().head(10)
        dest_counts = pd.Series(dest_clean).value_counts().head(10)

        distribution_metric = MetricResult(
            metric_name="distribution",
            metric_type=MetricType.STRING,
            source_value=source_counts.to_dict(),
            destination_value=dest_counts.to_dict(),
            difference=None,
            tolerance=0,
            passed=source_counts.to_dict() == dest_counts.to_dict(),
            details={
                "source_top_10": source_counts.to_dict(),
                "dest_top_10": dest_counts.to_dict()
            }
        )
        metrics["distribution"] = distribution_metric

        return metrics

    def calculate_temporal_metrics(self,
                                 source_data: List[datetime],
                                 dest_data: List[datetime]) -> Dict[str, MetricResult]:
        """
        Calcula métricas para datos temporales.

        Args:
            source_data: Datos origen
            dest_data: Datos destino

        Returns:
            Dict[str, MetricResult]: Métricas calculadas
        """
        metrics = {}

        # Limpiar datos None
        source_clean = [x for x in source_data if x is not None]
        dest_clean = [x for x in dest_data if x is not None]

        # Conteo de registros
        count_metric = MetricResult(
            metric_name="count",
            metric_type=MetricType.COUNT,
            source_value=len(source_clean),
            destination_value=len(dest_clean),
            difference=len(dest_clean) - len(source_clean),
            tolerance=0,
            passed=len(source_clean) == len(dest_clean),
            details={
                "source_nulls": len(source_data) - len(source_clean),
                "dest_nulls": len(dest_data) - len(dest_clean)
            }
        )
        metrics["count"] = count_metric

        if len(source_clean) == 0 or len(dest_clean) == 0:
            return metrics

        # Rango temporal
        source_min = min(source_clean)
        source_max = max(source_clean)
        dest_min = min(dest_clean)
        dest_max = max(dest_clean)

        min_diff = abs((dest_min - source_min).total_seconds())
        max_diff = abs((dest_max - source_max).total_seconds())

        time_range_metric = MetricResult(
            metric_name="time_range",
            metric_type=MetricType.TEMPORAL,
            source_value={"min": source_min, "max": source_max},
            destination_value={"min": dest_min, "max": dest_max},
            difference={"min_diff_seconds": min_diff, "max_diff_seconds": max_diff},
            tolerance=1.0,  # 1 segundo de tolerancia
            passed=min_diff <= 1.0 and max_diff <= 1.0,
            details={
                "source_range_seconds": (source_max - source_min).total_seconds(),
                "dest_range_seconds": (dest_max - dest_min).total_seconds()
            }
        )
        metrics["time_range"] = time_range_metric

        return metrics

    def compare_datasets(self,
                        source_data: Dict[str, List[Any]],
                        dest_data: Dict[str, List[Any]],
                        measurement_name: str,
                        database_name: str = "unknown") -> QualityReport:
        """
        Compara dos datasets completos.

        Args:
            source_data: Datos origen
            dest_data: Datos destino
            measurement_name: Nombre de la medición
            database_name: Nombre de la base de datos

        Returns:
            QualityReport: Reporte de calidad
        """
        all_metrics = []

        # Verificar que ambos datasets tengan las mismas columnas
        source_fields = set(source_data.keys())
        dest_fields = set(dest_data.keys())

        if source_fields != dest_fields:
            self.logger.warning(f"Campos diferentes - Origen: {source_fields}, Destino: {dest_fields}")

        # Procesar cada campo
        for field_name in source_fields.intersection(dest_fields):
            source_values = source_data[field_name]
            dest_values = dest_data[field_name]

            # Determinar el tipo de datos
            if all(isinstance(x, (int, float)) or x is None for x in source_values):
                field_metrics = self.calculate_numeric_metrics(source_values, dest_values)
            elif all(isinstance(x, bool) or x is None for x in source_values):
                field_metrics = self.calculate_boolean_metrics(source_values, dest_values)
            elif all(isinstance(x, datetime) or x is None for x in source_values):
                field_metrics = self.calculate_temporal_metrics(source_values, dest_values)
            else:
                field_metrics = self.calculate_string_metrics(
                    [str(x) for x in source_values],
                    [str(x) for x in dest_values]
                )

            # Agregar prefijo del campo a las métricas
            for metric_name, metric_result in field_metrics.items():
                metric_result.metric_name = f"{field_name}_{metric_name}"
                all_metrics.append(metric_result)

        # Calcular estadísticas del reporte
        passed_metrics = sum(1 for m in all_metrics if m.passed)
        failed_metrics = len(all_metrics) - passed_metrics
        success_rate = passed_metrics / len(all_metrics) if all_metrics else 0.0

        # Crear resumen
        summary = {
            "total_fields": len(source_fields.intersection(dest_fields)),
            "missing_fields": list(source_fields - dest_fields),
            "extra_fields": list(dest_fields - source_fields),
            "data_types": self._analyze_data_types(source_data),
            "record_counts": {
                "source": len(list(source_data.values())[0]) if source_data else 0,
                "destination": len(list(dest_data.values())[0]) if dest_data else 0
            }
        }

        return QualityReport(
            database_name=database_name,
            measurement_name=measurement_name,
            timestamp=datetime.now(),
            total_metrics=len(all_metrics),
            passed_metrics=passed_metrics,
            failed_metrics=failed_metrics,
            success_rate=success_rate,
            metrics=all_metrics,
            summary=summary
        )

    def _analyze_data_types(self, data: Dict[str, List[Any]]) -> Dict[str, str]:
        """
        Analiza los tipos de datos en un dataset.

        Args:
            data: Dataset a analizar

        Returns:
            Dict[str, str]: Tipos de datos por campo
        """
        data_types = {}

        for field_name, values in data.items():
            non_null_values = [v for v in values if v is not None]

            if not non_null_values:
                data_types[field_name] = "null"
            elif all(isinstance(v, bool) for v in non_null_values):
                data_types[field_name] = "boolean"
            elif all(isinstance(v, (int, float)) for v in non_null_values):
                data_types[field_name] = "numeric"
            elif all(isinstance(v, datetime) for v in non_null_values):
                data_types[field_name] = "temporal"
            else:
                data_types[field_name] = "string"

        return data_types

    def generate_report_summary(self, report: QualityReport) -> str:
        """
        Genera un resumen textual del reporte.

        Args:
            report: Reporte de calidad

        Returns:
            str: Resumen textual
        """
        summary = f"""
=== REPORTE DE CALIDAD DE DATOS ===
Base de datos: {report.database_name}
Medición: {report.measurement_name}
Timestamp: {report.timestamp}

RESUMEN GENERAL:
- Total de métricas: {report.total_metrics}
- Métricas exitosas: {report.passed_metrics}
- Métricas fallidas: {report.failed_metrics}
- Tasa de éxito: {report.success_rate:.2%}

DETALLE DE DATOS:
- Campos comparados: {report.summary['total_fields']}
- Registros origen: {report.summary['record_counts']['source']}
- Registros destino: {report.summary['record_counts']['destination']}
"""

        if report.summary['missing_fields']:
            summary += f"\nCampos faltantes en destino: {report.summary['missing_fields']}"

        if report.summary['extra_fields']:
            summary += f"\nCampos extra en destino: {report.summary['extra_fields']}"

        # Agregar detalles de métricas fallidas
        failed_metrics = [m for m in report.metrics if not m.passed]
        if failed_metrics:
            summary += "\n\nMÉTRICAS FALLIDAS:"
            for metric in failed_metrics:
                summary += f"\n- {metric.metric_name}: Origen={metric.source_value}, Destino={metric.destination_value}, Diferencia={metric.difference}"

        return summary

    def export_report_json(self, report: QualityReport, filename: str) -> None:
        """
        Exporta el reporte a JSON.

        Args:
            report: Reporte de calidad
            filename: Nombre del archivo
        """
        report_dict = {
            "database_name": report.database_name,
            "measurement_name": report.measurement_name,
            "timestamp": report.timestamp.isoformat(),
            "total_metrics": report.total_metrics,
            "passed_metrics": report.passed_metrics,
            "failed_metrics": report.failed_metrics,
            "success_rate": report.success_rate,
            "summary": report.summary,
            "metrics": []
        }

        for metric in report.metrics:
            metric_dict = {
                "metric_name": metric.metric_name,
                "metric_type": metric.metric_type.value,
                "source_value": self._serialize_value(metric.source_value),
                "destination_value": self._serialize_value(metric.destination_value),
                "difference": self._serialize_value(metric.difference),
                "tolerance": metric.tolerance,
                "passed": metric.passed,
                "details": metric.details
            }
            report_dict["metrics"].append(metric_dict)

        with open(filename, 'w') as f:
            json.dump(report_dict, f, indent=2, default=str)

    def _serialize_value(self, value: Any) -> Any:
        """
        Serializa un valor para JSON.

        Args:
            value: Valor a serializar

        Returns:
            Any: Valor serializable
        """
        if isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (np.integer, np.floating)):
            return value.item()
        elif isinstance(value, np.ndarray):
            return value.tolist()
        else:
            return value
