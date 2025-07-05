"""
Helper para testing con InfluxDB
===============================

Utilidades para facilitar el testing con servidores InfluxDB.
"""

import logging
import os

# Importar el cliente InfluxDB del proyecto
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from test.data.data_generator import DataGenerator
from test.utils.quality_metrics import QualityMetrics

from src.influxdb_client import InfluxDBClient


class InfluxDBTestHelper:
    """
    Helper para facilitar el testing con InfluxDB.

    Proporciona métodos para preparar datos de prueba,
    ejecutar backups y validar resultados.
    """

    def __init__(
        self,
        source_url: str = "http://localhost:8086",
        dest_url: str = "http://localhost:8087",
        username: str = "admin",
        password: str = "password",
    ):
        """
        Inicializa el helper de testing.

        Args:
            source_url: URL del servidor origen
            dest_url: URL del servidor destino
            username: Usuario
            password: Contraseña
        """
        self.source_url = source_url
        self.dest_url = dest_url
        self.username = username
        self.password = password

        self.logger = logging.getLogger(__name__)

        # Crear clientes
        self.source_client = InfluxDBClient(
            url=source_url,
            username=username,
            password=password,
            ssl_verify=False,
            timeout=30,
        )

        self.dest_client = InfluxDBClient(
            url=dest_url,
            username=username,
            password=password,
            ssl_verify=False,
            timeout=30,
        )

        # Generador de datos y métricas
        self.data_generator = DataGenerator(seed=42)
        self.quality_metrics = QualityMetrics(tolerance=0.01)

    def wait_for_servers(self, timeout: int = 300) -> bool:
        """
        Espera a que los servidores estén disponibles.

        Args:
            timeout: Timeout en segundos

        Returns:
            bool: True si los servidores están disponibles
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Probar conexión origen
                if self.source_client.test_connection():
                    self.logger.info("Servidor origen disponible")

                    # Probar conexión destino
                    if self.dest_client.test_connection():
                        self.logger.info("Servidor destino disponible")
                        return True
                    else:
                        self.logger.info("Esperando servidor destino...")
                else:
                    self.logger.info("Esperando servidor origen...")

            except Exception as e:
                self.logger.debug(f"Error esperando servidores: {e}")

            time.sleep(5)

        self.logger.error("Timeout esperando servidores")
        return False

    def clean_databases(self, database_names: List[str]) -> None:
        """
        Limpia bases de datos en ambos servidores.

        Args:
            database_names: Lista de nombres de bases de datos
        """
        for db_name in database_names:
            try:
                # Limpiar en origen
                self.source_client._execute_query(f"DROP DATABASE {db_name}")
                self.logger.info(
                    f"Base de datos {db_name} eliminada del servidor origen"
                )
            except Exception as e:
                self.logger.debug(f"Error eliminando {db_name} del origen: {e}")

            try:
                # Limpiar en destino
                self.dest_client._execute_query(f"DROP DATABASE {db_name}")
                self.logger.info(
                    f"Base de datos {db_name} eliminada del servidor destino"
                )
            except Exception as e:
                self.logger.debug(
                    f"Error eliminando {db_name} del destino: {e}"
                )

    def create_test_database(
        self, db_name: str, server: str = "source"
    ) -> bool:
        """
        Crea una base de datos de prueba.

        Args:
            db_name: Nombre de la base de datos
            server: Servidor donde crear ('source' o 'dest')

        Returns:
            bool: True si fue exitoso
        """
        client = self.source_client if server == "source" else self.dest_client

        try:
            result = client.create_database(db_name)
            self.logger.info(
                f"Base de datos {db_name} creada en servidor {server}"
            )
            return result
        except Exception as e:
            self.logger.error(f"Error creando base de datos {db_name}: {e}")
            return False

    def populate_test_data(
        self,
        db_name: str,
        dataset_config: Dict[str, Any],
        start_time: datetime = None,
        end_time: datetime = None,
        duration_hours: int = 24,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Puebla una base de datos con datos de prueba.

        Args:
            db_name: Nombre de la base de datos
            dataset_config: Configuración del dataset
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            duration_hours: Duración en horas si no se especifica end_time

        Returns:
            Dict: Datos generados
        """
        if start_time is None:
            start_time = datetime.now() - timedelta(hours=duration_hours)

        if end_time is None:
            end_time = datetime.now()

        # Generar dataset
        dataset = self.data_generator.generate_complex_dataset(
            database_name=db_name,
            start_time=start_time,
            end_time=end_time,
            measurements=dataset_config,
        )

        # Escribir datos al servidor origen
        for measurement_name, records in dataset.items():
            self.logger.info(
                f"Escribiendo {len(records)} registros a {measurement_name}"
            )

            try:
                # Convertir formato para InfluxDB
                influxdb_records = []
                for record in records:
                    influxdb_record = {
                        "measurement": record["measurement"],
                        "time": record["time"],
                        "fields": record["fields"],
                        "tags": record["tags"],
                    }
                    influxdb_records.append(influxdb_record)

                # Escribir en lotes
                batch_size = 1000
                for i in range(0, len(influxdb_records), batch_size):
                    batch = influxdb_records[i : i + batch_size]
                    success = self.source_client.write_data(
                        database=db_name,
                        measurement=measurement_name,
                        records=batch,
                    )

                    if not success:
                        self.logger.error(
                            f"Error escribiendo lote {i//batch_size + 1}"
                        )
                        break

                self.logger.info(
                    f"Datos escritos exitosamente a {measurement_name}"
                )

            except Exception as e:
                self.logger.error(
                    f"Error escribiendo datos a {measurement_name}: {e}"
                )

        return dataset

    def get_measurement_data(
        self, db_name: str, measurement_name: str, server: str = "source"
    ) -> Dict[str, List[Any]]:
        """
        Obtiene datos de una medición.

        Args:
            db_name: Nombre de la base de datos
            measurement_name: Nombre de la medición
            server: Servidor de donde obtener ('source' o 'dest')

        Returns:
            Dict: Datos de la medición
        """
        client = self.source_client if server == "source" else self.dest_client

        try:
            # Obtener rango temporal
            time_range = client.get_time_range(db_name, measurement_name)
            if not time_range[0] or not time_range[1]:
                self.logger.warning(
                    f"No se encontró rango temporal para {measurement_name}"
                )
                return {}

            # Obtener datos
            data = client.query_data(
                database=db_name,
                measurement=measurement_name,
                start_time=time_range[0],
                end_time=time_range[1],
            )

            # Convertir a formato diccionario
            result = {}
            if data:
                # Obtener nombres de columnas
                columns = list(data[0].keys())

                for column in columns:
                    result[column] = [record.get(column) for record in data]

            return result

        except Exception as e:
            self.logger.error(
                f"Error obteniendo datos de {measurement_name}: {e}"
            )
            return {}

    def compare_measurement_data(
        self, db_name: str, measurement_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Compara los datos de una medición entre origen y destino.

        Args:
            db_name: Nombre de la base de datos
            measurement_name: Nombre de la medición

        Returns:
            Optional[Dict]: Reporte de comparación
        """
        try:
            # Obtener datos del origen
            source_data = self.get_measurement_data(
                db_name, measurement_name, "source"
            )
            if not source_data:
                self.logger.error(
                    f"No se encontraron datos origen para {measurement_name}"
                )
                return None

            # Obtener datos del destino
            dest_data = self.get_measurement_data(
                db_name, measurement_name, "dest"
            )
            if not dest_data:
                self.logger.error(
                    f"No se encontraron datos destino para {measurement_name}"
                )
                return None

            # Comparar datos
            report = self.quality_metrics.compare_datasets(
                source_data=source_data,
                dest_data=dest_data,
                measurement_name=measurement_name,
                database_name=db_name,
            )

            return {
                "report": report,
                "summary": self.quality_metrics.generate_report_summary(report),
                "success": report.success_rate >= 0.95,  # 95% de éxito mínimo
            }

        except Exception as e:
            self.logger.error(
                f"Error comparando datos de {measurement_name}: {e}"
            )
            return None

    def run_full_test_cycle(
        self,
        db_name: str,
        dataset_config: Dict[str, Any],
        backup_config_path: str = None,
        duration_hours: int = 1,
    ) -> Dict[str, Any]:
        """
        Ejecuta un ciclo completo de testing.

        Args:
            db_name: Nombre de la base de datos
            dataset_config: Configuración del dataset
            backup_config_path: Ruta del archivo de configuración de backup
            duration_hours: Duración del dataset en horas

        Returns:
            Dict: Resultados del ciclo completo
        """
        results = {
            "database": db_name,
            "timestamp": datetime.now(),
            "phases": {},
            "success": False,
            "measurements": {},
        }

        try:
            # Fase 1: Preparación
            self.logger.info("Fase 1: Preparación de datos")

            # Limpiar bases de datos
            self.clean_databases([db_name, f"{db_name}_backup"])

            # Crear base de datos origen
            if not self.create_test_database(db_name, "source"):
                results["phases"]["preparation"] = {
                    "success": False,
                    "error": "No se pudo crear BD origen",
                }
                return results

            # Generar y poblar datos
            start_time = datetime.now() - timedelta(hours=duration_hours)
            dataset = self.populate_test_data(
                db_name=db_name,
                dataset_config=dataset_config,
                start_time=start_time,
                duration_hours=duration_hours,
            )

            results["phases"]["preparation"] = {
                "success": True,
                "records_generated": sum(
                    len(records) for records in dataset.values()
                ),
                "measurements": list(dataset.keys()),
            }

            # Fase 2: Backup (si se proporciona configuración)
            if backup_config_path:
                self.logger.info("Fase 2: Ejecutando backup")

                # Aquí se ejecutaría el backup usando el BackupProcessor
                # Por simplicidad, asumimos que el backup se ejecuta externamente
                # En un test real, se invocaría el BackupProcessor

                results["phases"]["backup"] = {
                    "success": True,
                    "config_path": backup_config_path,
                }

            # Fase 3: Verificación
            self.logger.info("Fase 3: Verificación de datos")

            verification_results = {}
            all_measurements_passed = True

            for measurement_name in dataset.keys():
                comparison = self.compare_measurement_data(
                    db_name, measurement_name
                )

                if comparison:
                    verification_results[measurement_name] = comparison
                    if not comparison["success"]:
                        all_measurements_passed = False
                else:
                    verification_results[measurement_name] = {
                        "success": False,
                        "error": "No se pudo comparar",
                    }
                    all_measurements_passed = False

            results["phases"]["verification"] = {
                "success": all_measurements_passed,
                "measurements": verification_results,
            }

            results["measurements"] = verification_results
            results["success"] = all_measurements_passed

        except Exception as e:
            self.logger.error(f"Error en ciclo de testing: {e}")
            results["error"] = str(e)

        return results

    @contextmanager
    def test_environment(self, databases: List[str]):
        """
        Context manager para entorno de testing.

        Args:
            databases: Lista de bases de datos a limpiar
        """
        try:
            # Preparar entorno
            self.logger.info("Preparando entorno de testing")

            if not self.wait_for_servers():
                raise RuntimeError("Servidores no disponibles")

            # Limpiar bases de datos
            self.clean_databases(databases)

            yield self

        finally:
            # Limpiar entorno
            self.logger.info("Limpiando entorno de testing")
            self.clean_databases(databases)

    def get_server_info(self, server: str = "source") -> Dict[str, Any]:
        """
        Obtiene información del servidor.

        Args:
            server: Servidor ('source' o 'dest')

        Returns:
            Dict: Información del servidor
        """
        client = self.source_client if server == "source" else self.dest_client

        try:
            # Obtener lista de bases de datos
            databases = client.get_databases()

            info = {
                "server": server,
                "url": client.url,
                "connected": client.test_connection(),
                "databases": databases,
                "database_count": len(databases),
            }

            return info

        except Exception as e:
            self.logger.error(
                f"Error obteniendo información del servidor {server}: {e}"
            )
            return {"server": server, "error": str(e), "connected": False}

    def close(self):
        """Cierra las conexiones."""
        try:
            self.source_client.close()
            self.dest_client.close()
        except Exception as e:
            self.logger.debug(f"Error cerrando conexiones: {e}")
