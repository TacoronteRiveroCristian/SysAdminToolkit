"""
Generador de datos heterogéneos para testing
===========================================

Genera datos de prueba realistas con diferentes tipos de datos,
distribuciones y patrones temporales para testing de backup.
"""

import logging
import random
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
from faker import Faker


class DataGenerator:
    """
    Generador de datos heterogéneos para testing.

    Genera datos realistas con diferentes tipos de datos,
    distribuciones estadísticas y patrones temporales.
    """

    def __init__(self, seed: Optional[int] = None):
        """
        Inicializa el generador de datos.

        Args:
            seed: Semilla para reproducibilidad
        """
        self.seed = seed
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)

        self.logger = logging.getLogger(__name__)

    def generate_numeric_data(
        self, count: int, data_type: str = "normal", **kwargs
    ) -> List[float]:
        """
        Genera datos numéricos con diferentes distribuciones.

        Args:
            count: Número de puntos a generar
            data_type: Tipo de distribución ('normal', 'uniform', 'exponential', 'linear', 'seasonal')
            **kwargs: Parámetros específicos de la distribución

        Returns:
            List[float]: Lista de valores numéricos
        """
        if data_type == "normal":
            mean = kwargs.get("mean", 0.0)
            std = kwargs.get("std", 1.0)
            return np.random.normal(mean, std, count).tolist()

        elif data_type == "uniform":
            low = kwargs.get("low", 0.0)
            high = kwargs.get("high", 1.0)
            return np.random.uniform(low, high, count).tolist()

        elif data_type == "exponential":
            scale = kwargs.get("scale", 1.0)
            return np.random.exponential(scale, count).tolist()

        elif data_type == "linear":
            start = kwargs.get("start", 0.0)
            end = kwargs.get("end", 100.0)
            noise = kwargs.get("noise", 0.1)
            base = np.linspace(start, end, count)
            noise_data = np.random.normal(0, noise * (end - start), count)
            return (base + noise_data).tolist()

        elif data_type == "seasonal":
            amplitude = kwargs.get("amplitude", 1.0)
            period = kwargs.get("period", 24)  # horas
            offset = kwargs.get("offset", 0.0)
            noise = kwargs.get("noise", 0.1)

            t = np.linspace(0, count * 2 * np.pi / period, count)
            seasonal = amplitude * np.sin(t) + offset
            noise_data = np.random.normal(0, noise * amplitude, count)
            return (seasonal + noise_data).tolist()

        else:
            raise ValueError(f"Tipo de datos no soportado: {data_type}")

    def generate_boolean_data(
        self, count: int, true_probability: float = 0.5
    ) -> List[bool]:
        """
        Genera datos booleanos.

        Args:
            count: Número de puntos a generar
            true_probability: Probabilidad de True

        Returns:
            List[bool]: Lista de valores booleanos
        """
        return [random.random() < true_probability for _ in range(count)]

    def generate_string_data(
        self, count: int, data_type: str = "random", **kwargs
    ) -> List[str]:
        """
        Genera datos de cadenas.

        Args:
            count: Número de puntos a generar
            data_type: Tipo de cadena ('random', 'name', 'email', 'uuid', 'enum')
            **kwargs: Parámetros específicos

        Returns:
            List[str]: Lista de cadenas
        """
        if data_type == "random":
            length = kwargs.get("length", 10)
            return [
                "".join(
                    random.choices(
                        string.ascii_letters + string.digits, k=length
                    )
                )
                for _ in range(count)
            ]

        elif data_type == "name":
            return [self.fake.name() for _ in range(count)]

        elif data_type == "email":
            return [self.fake.email() for _ in range(count)]

        elif data_type == "uuid":
            return [self.fake.uuid4() for _ in range(count)]

        elif data_type == "enum":
            values = kwargs.get("values", ["A", "B", "C"])
            return [random.choice(values) for _ in range(count)]

        elif data_type == "city":
            return [self.fake.city() for _ in range(count)]

        elif data_type == "country":
            return [self.fake.country() for _ in range(count)]

        else:
            raise ValueError(f"Tipo de cadena no soportado: {data_type}")

    def generate_timestamp_series(
        self,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1m",
        jitter: bool = False,
    ) -> List[datetime]:
        """
        Genera una serie temporal de timestamps.

        Args:
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            interval: Intervalo entre puntos ('1s', '1m', '1h', '1d')
            jitter: Añadir variación aleatoria

        Returns:
            List[datetime]: Lista de timestamps
        """
        # Convertir intervalo a timedelta
        if interval.endswith("s"):
            delta = timedelta(seconds=int(interval[:-1]))
        elif interval.endswith("m"):
            delta = timedelta(minutes=int(interval[:-1]))
        elif interval.endswith("h"):
            delta = timedelta(hours=int(interval[:-1]))
        elif interval.endswith("d"):
            delta = timedelta(days=int(interval[:-1]))
        else:
            raise ValueError(f"Formato de intervalo no soportado: {interval}")

        timestamps = []
        current_time = start_time

        while current_time <= end_time:
            if jitter:
                # Añadir variación aleatoria de ±10% del intervalo
                jitter_seconds = delta.total_seconds() * 0.1
                jitter_offset = timedelta(
                    seconds=random.uniform(-jitter_seconds, jitter_seconds)
                )
                timestamps.append(current_time + jitter_offset)
            else:
                timestamps.append(current_time)

            current_time += delta

        return timestamps

    def generate_measurement_data(
        self,
        measurement_name: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = "1m",
        field_configs: Dict[str, Dict[str, Any]] = None,
        tag_configs: Dict[str, Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Genera datos completos para una medición.

        Args:
            measurement_name: Nombre de la medición
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            interval: Intervalo entre puntos
            field_configs: Configuraciones de campos
            tag_configs: Configuraciones de tags

        Returns:
            List[Dict]: Lista de registros
        """
        # Generar timestamps
        timestamps = self.generate_timestamp_series(
            start_time, end_time, interval
        )
        count = len(timestamps)

        # Configuraciones por defecto
        if field_configs is None:
            field_configs = {
                "value": {"type": "normal", "mean": 50.0, "std": 10.0},
                "status": {"type": "boolean", "true_probability": 0.8},
            }

        if tag_configs is None:
            tag_configs = {
                "host": {
                    "type": "enum",
                    "values": ["server1", "server2", "server3"],
                },
                "region": {
                    "type": "enum",
                    "values": ["us-east", "us-west", "eu-central"],
                },
            }

        # Generar datos de campos
        field_data = {}
        for field_name, config in field_configs.items():
            field_type = config.get("type", "normal")

            if field_type in [
                "normal",
                "uniform",
                "exponential",
                "linear",
                "seasonal",
            ]:
                field_data[field_name] = self.generate_numeric_data(
                    count, field_type, **config
                )
            elif field_type == "boolean":
                field_data[field_name] = self.generate_boolean_data(
                    count, **config
                )
            else:
                field_data[field_name] = self.generate_string_data(
                    count, field_type, **config
                )

        # Generar datos de tags
        tag_data = {}
        for tag_name, config in tag_configs.items():
            tag_type = config.get("type", "enum")
            tag_data[tag_name] = self.generate_string_data(
                count, tag_type, **config
            )

        # Combinar en registros
        records = []
        for i in range(count):
            record = {
                "measurement": measurement_name,
                "time": timestamps[i],
                "fields": {
                    field: values[i] for field, values in field_data.items()
                },
                "tags": {tag: values[i] for tag, values in tag_data.items()},
            }
            records.append(record)

        return records

    def generate_complex_dataset(
        self,
        database_name: str,
        start_time: datetime,
        end_time: datetime,
        measurements: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Genera un dataset complejo con múltiples mediciones.

        Args:
            database_name: Nombre de la base de datos
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            measurements: Configuraciones de mediciones

        Returns:
            Dict: Dataset con todas las mediciones
        """
        dataset = {}

        for measurement_name, config in measurements.items():
            self.logger.info(
                f"Generando datos para medición: {measurement_name}"
            )

            records = self.generate_measurement_data(
                measurement_name=measurement_name,
                start_time=start_time,
                end_time=end_time,
                interval=config.get("interval", "1m"),
                field_configs=config.get("fields", None),
                tag_configs=config.get("tags", None),
            )

            dataset[measurement_name] = records
            self.logger.info(
                f"Generados {len(records)} registros para {measurement_name}"
            )

        return dataset

    def generate_anomalies(
        self,
        data: List[float],
        anomaly_rate: float = 0.05,
        anomaly_type: str = "outlier",
    ) -> List[float]:
        """
        Introduce anomalías en los datos.

        Args:
            data: Datos originales
            anomaly_rate: Tasa de anomalías (0.0 a 1.0)
            anomaly_type: Tipo de anomalía ('outlier', 'missing', 'spike')

        Returns:
            List[float]: Datos con anomalías
        """
        result = data.copy()
        num_anomalies = int(len(data) * anomaly_rate)
        anomaly_indices = random.sample(range(len(data)), num_anomalies)

        for idx in anomaly_indices:
            if anomaly_type == "outlier":
                # Valor extremo
                std = np.std(data)
                mean = np.mean(data)
                result[idx] = mean + random.choice(
                    [-1, 1]
                ) * std * random.uniform(5, 10)

            elif anomaly_type == "missing":
                # Valor faltante (None)
                result[idx] = None

            elif anomaly_type == "spike":
                # Pico repentino
                result[idx] = result[idx] * random.uniform(10, 50)

        return result
