"""
Procesador principal de backup para InfluxDB
===========================================

Orquesta todo el proceso de backup usando los demás componentes del sistema.
Maneja tanto el modo incremental como el modo range, con filtrado de mediciones
y campos, paginación, y todas las funcionalidades avanzadas.
"""

import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import logging

from .config_manager import ConfigManager
from .logger_manager import LoggerManager
from .influxdb_client import InfluxDBClient
from .scheduler import BackupScheduler
from .utils import (
    generate_time_ranges, parse_duration,
    classify_influxdb_type, calculate_memory_usage_mb
)


class BackupProcessor:
    """
    Procesador principal de backup para InfluxDB.

    Coordina todos los componentes del sistema para realizar backups
    completos de bases de datos InfluxDB.
    """

    def __init__(self, config_path: str):
        """
        Inicializa el procesador de backup.

        Args:
            config_path: Ruta al archivo de configuración
        """
        self.config_path = config_path

        # Cargar configuración
        self.config = ConfigManager(config_path)

        # Configurar logging
        self.logger_manager = LoggerManager(
            self.config.get_config_name(),
            {
                'log_directory': self.config.get_log_directory(),
                'log_level': self.config.get_log_level(),
                'log_rotation': self.config.get_log_rotation_config(),
                'loki': self.config.get_loki_config()
            }
        )

        # Obtener loggers
        self.logger = self.logger_manager.get_main_logger()
        self.influxdb_logger = self.logger_manager.get_influxdb_logger()

        # Crear clientes InfluxDB
        self.source_client = self._create_influxdb_client('source')
        self.dest_client = self._create_influxdb_client('destination')

        # Scheduler para modo incremental
        self.scheduler = None

        # Estadísticas
        self.stats = {
            'start_time': None,
            'end_time': None,
            'databases_processed': 0,
            'measurements_processed': 0,
            'records_transferred': 0,
            'errors': []
        }

    def _create_influxdb_client(self, server_type: str) -> InfluxDBClient:
        """
        Crea un cliente InfluxDB para source o destination.

        Args:
            server_type: 'source' o 'destination'

        Returns:
            InfluxDBClient: Cliente configurado
        """
        if server_type == 'source':
            config = self.config.get_source_config()
            auth = self.config.get_source_auth()
        else:
            config = self.config.get_destination_config()
            auth = self.config.get_destination_auth()

        return InfluxDBClient(
            url=config['url'],
            username=auth['user'] if auth else None,
            password=auth['password'] if auth else None,
            ssl_verify=self.config.should_verify_ssl(server_type),
            timeout=self.config.get_timeout_client(),
            max_retries=self.config.get_retries(),
            retry_delay=self.config.get_retry_delay(),
            logger=self.influxdb_logger
        )

    def _wait_for_connections(self) -> bool:
        """
        Espera a que las conexiones estén disponibles.

        Returns:
            bool: True si las conexiones están disponibles
        """
        retry_delay = self.config.get_initial_connection_retry_delay()

        while True:
            # Probar conexión origen
            self.logger.info("Testing source connection...")
            if not self.source_client.test_connection():
                self.logger.warning(f"Source connection failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue

            self.logger.info("Source connection successful")

            # Probar conexión destino
            self.logger.info("Testing destination connection...")
            if not self.dest_client.test_connection():
                self.logger.warning(f"Destination connection failed, retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                continue

            self.logger.info("Destination connection successful")
            return True

    def _prepare_destination_databases(self) -> bool:
        """
        Prepara las bases de datos de destino.

        Returns:
            bool: True si fue exitoso
        """
        databases = self.config.get_databases_to_backup()

        for db_config in databases:
            source_name = db_config['name']
            dest_name = self.config.get_final_database_name(
                source_name, db_config['destination']
            )

            self.logger.info(f"Creating destination database: {dest_name}")

            if not self.dest_client.create_database(dest_name):
                self.logger.error(f"Failed to create destination database: {dest_name}")
                return False

        return True

    def _get_databases_to_process(self) -> List[Dict[str, str]]:
        """
        Obtiene la lista de bases de datos a procesar.

        Returns:
            List[Dict]: Lista de configuraciones de bases de datos
        """
        configured_databases = self.config.get_databases_to_backup()

        if configured_databases:
            return configured_databases

        # Si no hay bases de datos configuradas, obtener todas
        self.logger.info("No databases configured, getting all databases from source")
        source_databases = self.source_client.get_databases()

        databases = []
        for db_name in source_databases:
            final_name = self.config.get_final_database_name(db_name)
            databases.append({
                'name': db_name,
                'destination': final_name
            })

        return databases

    def _should_process_measurement(self, measurement: str) -> bool:
        """
        Determina si una medición debe ser procesada.

        Args:
            measurement: Nombre de la medición

        Returns:
            bool: True si debe ser procesada
        """
        return self.config.should_backup_measurement(measurement)

    def _filter_fields(self, measurement: str, fields: Dict[str, str]) -> Dict[str, str]:
        """
        Filtra campos basado en la configuración.

        Args:
            measurement: Nombre de la medición
            fields: Diccionario campo -> tipo

        Returns:
            Dict[str, str]: Campos filtrados
        """
        filtered_fields = {}

        for field_name, field_type in fields.items():
            if self.config.should_backup_field(measurement, field_name, field_type):
                filtered_fields[field_name] = field_type

        return filtered_fields

    def _is_field_obsolete(self, database: str, measurement: str, field: str) -> bool:
        """
        Determina si un campo está obsoleto.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición
            field: Nombre del campo

        Returns:
            bool: True si está obsoleto
        """
        threshold_str = self.config.get_field_obsolete_threshold()
        if not threshold_str:
            return False

        try:
            threshold = parse_duration(threshold_str)
            cutoff_time = datetime.now() - threshold

            # Obtener último timestamp del campo en destino
            dest_db = self.config.get_final_database_name(database)
            last_timestamp = self.dest_client.get_field_last_timestamp(
                dest_db, measurement, field
            )

            if last_timestamp and last_timestamp < cutoff_time:
                self.logger.debug(f"Field {field} is obsolete (last data: {last_timestamp})")
                return True

            return False

        except Exception as e:
            self.logger.warning(f"Failed to check field obsolescence: {e}")
            return False

    def _get_incremental_start_time(self, dest_database: str, measurement: str) -> Optional[datetime]:
        """
        Obtiene el tiempo de inicio para backup incremental.

        Args:
            dest_database: Base de datos destino
            measurement: Nombre de la medición

        Returns:
            datetime: Tiempo de inicio o None para backup completo
        """
        try:
            last_timestamp = self.dest_client.get_last_timestamp(dest_database, measurement)

            if last_timestamp:
                # Empezar desde el último timestamp + 1 nanosegundo
                start_time = last_timestamp + timedelta(microseconds=1)
                self.logger.info(f"Incremental backup starting from: {start_time}")
                return start_time
            else:
                self.logger.info("No existing data found, performing full backup")
                return None

        except Exception as e:
            self.logger.warning(f"Failed to get incremental start time: {e}")
            return None

    def _backup_measurement(self, source_db: str, dest_db: str, measurement: str,
                          start_time: datetime, end_time: datetime) -> int:
        """
        Realiza el backup de una medición específica.

        Args:
            source_db: Base de datos origen
            dest_db: Base de datos destino
            measurement: Nombre de la medición
            start_time: Tiempo de inicio
            end_time: Tiempo de fin

        Returns:
            int: Número de registros transferidos
        """
        self.logger.info(f"Processing measurement: {measurement}")

        # Obtener metadatos
        fields = self.source_client.get_field_keys(source_db, measurement)
        tags = self.source_client.get_tag_keys(source_db, measurement)

        if not fields:
            self.logger.warning(f"No fields found for measurement {measurement}")
            return 0

        # Filtrar campos
        filtered_fields = self._filter_fields(measurement, fields)

        if not filtered_fields:
            self.logger.warning(f"No fields to backup for measurement {measurement} after filtering")
            return 0

        # Verificar campos obsoletos
        active_fields = {}
        for field_name, field_type in filtered_fields.items():
            if not self._is_field_obsolete(source_db, measurement, field_name):
                active_fields[field_name] = field_type

        if not active_fields:
            self.logger.info(f"All fields are obsolete for measurement {measurement}")
            return 0

        self.logger_manager.log_measurement_info(
            self.logger, measurement, len(active_fields), len(tags), (start_time, end_time)
        )

        # Contar registros totales
        total_records = self.source_client.count_records(source_db, measurement, start_time, end_time)

        if total_records == 0:
            self.logger.info(f"No records found for measurement {measurement} in time range")
            return 0

        self.logger.info(f"Found {total_records} records to transfer")

        # Configurar paginación
        chunk_days = self.config.get_days_of_pagination()
        time_ranges = generate_time_ranges(start_time, end_time, chunk_days)

        records_transferred = 0

        for i, (chunk_start, chunk_end) in enumerate(time_ranges):
            self.logger_manager.log_pagination_info(
                self.logger, i + 1, len(time_ranges), 0
            )

            # Consultar datos
            field_names = list(active_fields.keys())

            start_query = time.time()
            records = self.source_client.query_data(
                source_db, measurement, chunk_start, chunk_end,
                fields=field_names, tags=tags,
                group_by=self.config.get_group_by()
            )
            query_duration = time.time() - start_query

            if records:
                self.logger_manager.log_query_execution(
                    self.logger, f"SELECT from {measurement}", query_duration, len(records)
                )

                # Escribir datos al destino
                start_write = time.time()
                success = self.dest_client.write_data(dest_db, measurement, records)
                write_duration = time.time() - start_write

                if success:
                    records_transferred += len(records)
                    self.logger_manager.log_batch_write(
                        self.logger, dest_db, measurement, len(records), write_duration
                    )
                else:
                    self.logger.error(f"Failed to write batch for measurement {measurement}")
                    break

            # Log de progreso
            self.logger_manager.log_database_progress(
                self.logger, source_db, measurement, records_transferred, total_records
            )

            # Log de memoria
            self.logger_manager.log_memory_usage(self.logger, f"After chunk {i+1}")

        return records_transferred

    def _backup_database(self, db_config: Dict[str, str]) -> int:
        """
        Realiza el backup de una base de datos.

        Args:
            db_config: Configuración de la base de datos

        Returns:
            int: Número de registros transferidos
        """
        source_db = db_config['name']
        dest_db = self.config.get_final_database_name(
            source_db, db_config['destination']
        )

        self.logger.info(f"Starting backup: {source_db} -> {dest_db}")

        # Obtener mediciones
        measurements = self.source_client.get_measurements(source_db)

        if not measurements:
            self.logger.warning(f"No measurements found in database {source_db}")
            return 0

        # Filtrar mediciones
        filtered_measurements = [m for m in measurements if self._should_process_measurement(m)]

        if not filtered_measurements:
            self.logger.warning(f"No measurements to backup in database {source_db} after filtering")
            return 0

        self.logger.info(f"Found {len(filtered_measurements)} measurements to backup")

        total_records = 0

        # Determinar rango de tiempo
        if self.config.get_backup_mode() == 'range':
            range_config = self.config.get_range_config()
            start_time = datetime.fromisoformat(range_config['start_date'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(range_config['end_date'].replace('Z', '+00:00'))
        else:
            # Modo incremental
            start_time = None
            end_time = datetime.now()

        # Procesar cada medición
        for measurement in filtered_measurements:
            try:
                # Para modo incremental, obtener tiempo de inicio específico
                if self.config.get_backup_mode() == 'incremental':
                    measurement_start = self._get_incremental_start_time(dest_db, measurement)

                    if measurement_start is None:
                        # Backup completo de la medición
                        first_time, last_time = self.source_client.get_time_range(source_db, measurement)
                        measurement_start = first_time if first_time else datetime.now() - timedelta(days=30)
                else:
                    measurement_start = start_time

                if measurement_start and measurement_start < end_time:
                    records = self._backup_measurement(
                        source_db, dest_db, measurement, measurement_start, end_time
                    )
                    total_records += records
                    self.stats['measurements_processed'] += 1
                else:
                    self.logger.info(f"Skipping measurement {measurement} (no new data)")

            except Exception as e:
                error_msg = f"Failed to backup measurement {measurement}: {e}"
                self.logger.error(error_msg)
                self.stats['errors'].append(error_msg)

        self.logger.info(f"Completed backup of database {source_db}: {total_records} records")
        return total_records

    def run_backup(self) -> Dict[str, Any]:
        """
        Ejecuta el proceso de backup.

        Returns:
            Dict: Resultado del backup
        """
        self.stats['start_time'] = datetime.now()

        try:
            # Registrar inicio
            databases = self._get_databases_to_process()
            self.logger_manager.log_backup_start(
                self.logger, self.config.get_backup_mode(),
                databases, self.stats['start_time']
            )

            # Esperar conexiones
            if not self._wait_for_connections():
                raise Exception("Failed to establish connections")

            # Preparar bases de datos destino
            if not self._prepare_destination_databases():
                raise Exception("Failed to prepare destination databases")

            # Procesar cada base de datos
            for db_config in databases:
                records = self._backup_database(db_config)
                self.stats['records_transferred'] += records
                self.stats['databases_processed'] += 1

            # Registrar fin exitoso
            self.stats['end_time'] = datetime.now()
            self.logger_manager.log_backup_end(
                self.logger, True, self.stats, self.stats['end_time']
            )

            return {
                'success': True,
                'stats': self.stats.copy()
            }

        except Exception as e:
            self.stats['end_time'] = datetime.now()
            error_msg = f"Backup failed: {e}"
            self.logger.error(error_msg)
            self.stats['errors'].append(error_msg)

            self.logger_manager.log_backup_end(
                self.logger, False, self.stats, self.stats['end_time']
            )

            return {
                'success': False,
                'error': str(e),
                'stats': self.stats.copy()
            }

    def run_scheduled_backup(self) -> None:
        """
        Ejecuta backup con scheduler para modo incremental.
        """
        schedule = self.config.get_schedule()

        if not schedule:
            # Ejecutar una sola vez
            self.logger.info("Running single incremental backup")
            result = self.run_backup()
            return result

        # Crear scheduler
        self.scheduler = BackupScheduler(
            self.config.get_config_name(),
            self.logger_manager.get_scheduler_logger()
        )

        try:
            # Programar backup
            self.scheduler.schedule_backup(schedule, self.run_backup)

            # Mantener el proceso vivo
            while self.scheduler.is_running:
                time.sleep(60)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping scheduler...")
            if self.scheduler:
                self.scheduler.stop()
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")
            if self.scheduler:
                self.scheduler.stop()

    def run(self) -> Any:
        """
        Ejecuta el backup según el modo configurado.

        Returns:
            Any: Resultado del backup
        """
        backup_mode = self.config.get_backup_mode()

        if backup_mode == 'range':
            return self.run_backup()
        elif backup_mode == 'incremental':
            return self.run_scheduled_backup()
        else:
            raise ValueError(f"Unknown backup mode: {backup_mode}")

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene las estadísticas del backup.

        Returns:
            Dict: Estadísticas
        """
        return self.stats.copy()

    def cleanup(self) -> None:
        """Limpia recursos."""
        if self.scheduler:
            self.scheduler.stop()

        if self.source_client:
            self.source_client.close()

        if self.dest_client:
            self.dest_client.close()

        if self.logger_manager:
            self.logger_manager.cleanup()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()

    def __repr__(self) -> str:
        """Representación en string del procesador."""
        return f"BackupProcessor(config='{self.config.get_config_name()}', mode='{self.config.get_backup_mode()}')"
