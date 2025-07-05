"""
Gestor de logging para el sistema de backup de InfluxDB
======================================================

Maneja la configuración de logging con rotación de archivos,
integración con Loki y soporte multi-proceso.
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .utils import get_process_id


class LoggerManager:
    """
    Gestor de logging para el sistema de backup.

    Configura loggers con rotación, formateo y envío a Loki.
    """

    def __init__(self, config_name: str, log_config: Dict[str, Any]):
        """
        Inicializa el gestor de logging.

        Args:
            config_name: Nombre de la configuración
            log_config: Configuración de logging
        """
        self.config_name = config_name
        self.log_config = log_config
        self.process_id = get_process_id()

        # Configurar logging
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configura el sistema de logging."""
        # Crear directorio de logs si no existe
        log_dir = self.log_config["log_directory"]
        config_log_dir = os.path.join(log_dir, self.config_name)
        os.makedirs(config_log_dir, exist_ok=True)

        # Configurar logger principal
        logger_name = f"backup.{self.config_name}"
        logger = logging.getLogger(logger_name)

        # Limpiar handlers existentes
        logger.handlers.clear()

        # Configurar nivel de log
        log_level = getattr(logging, self.log_config["log_level"].upper())
        logger.setLevel(log_level)

        # Configurar formato
        formatter = self._create_formatter()

        # Configurar file handler con rotación
        file_handler = self._create_file_handler(config_log_dir, formatter)
        logger.addHandler(file_handler)

        # Configurar console handler
        console_handler = self._create_console_handler(formatter)
        logger.addHandler(console_handler)

        # Configurar Loki handler si está habilitado
        if self.log_config["loki"]["enabled"]:
            try:
                loki_handler = self._create_loki_handler()
                if loki_handler:
                    logger.addHandler(loki_handler)
            except Exception as e:
                logger.warning(f"Failed to setup Loki handler: {e}")

        # Evitar propagación al logger raíz
        logger.propagate = False

    def _create_formatter(self) -> logging.Formatter:
        """
        Crea el formateador de logs.

        Returns:
            logging.Formatter: Formateador configurado
        """
        format_string = (
            "%(asctime)s - %(name)s - PID:%(process)d - "
            "%(levelname)s - %(message)s"
        )

        return logging.Formatter(fmt=format_string, datefmt="%Y-%m-%d %H:%M:%S")

    def _create_file_handler(
        self, log_dir: str, formatter: logging.Formatter
    ) -> logging.handlers.TimedRotatingFileHandler:
        """
        Crea el handler de archivos con rotación.

        Args:
            log_dir: Directorio de logs
            formatter: Formateador de logs

        Returns:
            TimedRotatingFileHandler: Handler configurado
        """
        log_file = os.path.join(log_dir, f"{self.config_name}.log")

        rotation_config = self.log_config["log_rotation"]

        handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when=rotation_config["when"],
            interval=rotation_config["interval"],
            backupCount=rotation_config["backup_count"],
            encoding="utf-8",
        )

        handler.setFormatter(formatter)
        return handler

    def _create_console_handler(
        self, formatter: logging.Formatter
    ) -> logging.StreamHandler:
        """
        Crea el handler de consola.

        Args:
            formatter: Formateador de logs

        Returns:
            StreamHandler: Handler configurado
        """
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        return handler

    def _create_loki_handler(self) -> Optional[logging.Handler]:
        """
        Crea el handler de Loki si está disponible.

        Returns:
            Handler: Handler de Loki o None si no está disponible
        """
        try:
            import logging_loki

            loki_config = self.log_config["loki"]

            # Preparar tags base
            tags = {
                "config_name": self.config_name,
                "process_id": str(self.process_id),
                "backup_system": "influxdb",
            }

            # Agregar tags personalizados
            if loki_config.get("tags"):
                tags.update(loki_config["tags"])

            # Crear handler
            handler = logging_loki.LokiHandler(
                url=f"http://{loki_config['url']}:{loki_config['port']}/loki/api/v1/push",
                tags=tags,
                version="1",
            )

            return handler

        except ImportError:
            return None
        except Exception as e:
            # Logger básico para errores de configuración
            basic_logger = logging.getLogger(__name__)
            basic_logger.error(f"Failed to create Loki handler: {e}")
            return None

    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Obtiene un logger configurado.

        Args:
            name: Nombre del logger (opcional)

        Returns:
            logging.Logger: Logger configurado
        """
        if name:
            logger_name = f"backup.{self.config_name}.{name}"
        else:
            logger_name = f"backup.{self.config_name}"

        return logging.getLogger(logger_name)

    def get_main_logger(self) -> logging.Logger:
        """
        Obtiene el logger principal del backup.

        Returns:
            logging.Logger: Logger principal
        """
        return self.get_logger("main")

    def get_influxdb_logger(self) -> logging.Logger:
        """
        Obtiene el logger para operaciones de InfluxDB.

        Returns:
            logging.Logger: Logger de InfluxDB
        """
        return self.get_logger("influxdb")

    def get_scheduler_logger(self) -> logging.Logger:
        """
        Obtiene el logger para el scheduler.

        Returns:
            logging.Logger: Logger del scheduler
        """
        return self.get_logger("scheduler")

    def log_backup_start(
        self,
        logger: logging.Logger,
        backup_mode: str,
        databases: list,
        start_time: datetime = None,
    ) -> None:
        """
        Registra el inicio de un backup.

        Args:
            logger: Logger a usar
            backup_mode: Modo de backup
            databases: Lista de bases de datos
            start_time: Tiempo de inicio (opcional)
        """
        if start_time is None:
            start_time = datetime.now()

        db_names = [db.get("name", "Unknown") for db in databases]

        logger.info(f"=== BACKUP STARTED ===")
        logger.info(f"Config: {self.config_name}")
        logger.info(f"Mode: {backup_mode}")
        logger.info(f"Databases: {', '.join(db_names)}")
        logger.info(f"Start time: {start_time}")
        logger.info(f"Process ID: {self.process_id}")

    def log_backup_end(
        self,
        logger: logging.Logger,
        success: bool,
        stats: Dict[str, Any],
        end_time: datetime = None,
    ) -> None:
        """
        Registra el fin de un backup.

        Args:
            logger: Logger a usar
            success: Si el backup fue exitoso
            stats: Estadísticas del backup
            end_time: Tiempo de fin (opcional)
        """
        if end_time is None:
            end_time = datetime.now()

        status = "SUCCESS" if success else "FAILED"

        logger.info(f"=== BACKUP {status} ===")
        logger.info(f"End time: {end_time}")

        if stats:
            logger.info("Backup statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")

    def log_database_progress(
        self,
        logger: logging.Logger,
        database: str,
        measurement: str,
        records_processed: int,
        total_records: int = None,
    ) -> None:
        """
        Registra el progreso de backup de una base de datos.

        Args:
            logger: Logger a usar
            database: Nombre de la base de datos
            measurement: Nombre de la medición
            records_processed: Registros procesados
            total_records: Total de registros (opcional)
        """
        if total_records:
            percentage = (records_processed / total_records) * 100
            logger.info(
                f"DB: {database}, Measurement: {measurement} - "
                f"{records_processed}/{total_records} ({percentage:.1f}%)"
            )
        else:
            logger.info(
                f"DB: {database}, Measurement: {measurement} - "
                f"{records_processed} records processed"
            )

    def log_error_with_context(
        self, logger: logging.Logger, error: Exception, context: Dict[str, Any]
    ) -> None:
        """
        Registra un error con contexto adicional.

        Args:
            logger: Logger a usar
            error: Excepción ocurrida
            context: Contexto adicional
        """
        logger.error(f"Error: {error}")
        logger.error(f"Error type: {type(error).__name__}")

        if context:
            logger.error("Context:")
            for key, value in context.items():
                logger.error(f"  {key}: {value}")

    def log_memory_usage(self, logger: logging.Logger, stage: str) -> None:
        """
        Registra el uso de memoria actual.

        Args:
            logger: Logger a usar
            stage: Etapa del proceso
        """
        try:
            from .utils import calculate_memory_usage_mb

            memory_mb = calculate_memory_usage_mb()
            logger.debug(f"Memory usage at {stage}: {memory_mb:.2f} MB")
        except Exception:
            pass

    def log_connection_status(
        self,
        logger: logging.Logger,
        server_type: str,
        url: str,
        status: str,
        details: str = None,
    ) -> None:
        """
        Registra el estado de conexión a un servidor.

        Args:
            logger: Logger a usar
            server_type: Tipo de servidor ('source' o 'destination')
            url: URL del servidor
            status: Estado de la conexión
            details: Detalles adicionales (opcional)
        """
        message = f"{server_type.upper()} connection to {url}: {status}"

        if details:
            message += f" - {details}"

        if status.lower() in ["connected", "success"]:
            logger.info(message)
        elif status.lower() in ["failed", "error"]:
            logger.error(message)
        else:
            logger.warning(message)

    def log_measurement_info(
        self,
        logger: logging.Logger,
        measurement: str,
        field_count: int,
        tag_count: int,
        time_range: tuple = None,
    ) -> None:
        """
        Registra información sobre una medición.

        Args:
            logger: Logger a usar
            measurement: Nombre de la medición
            field_count: Número de campos
            tag_count: Número de tags
            time_range: Rango de tiempo (opcional)
        """
        message = f"Measurement: {measurement} - Fields: {field_count}, Tags: {tag_count}"

        if time_range:
            start_time, end_time = time_range
            message += f", Time range: {start_time} to {end_time}"

        logger.info(message)

    def log_field_filtering(
        self,
        logger: logging.Logger,
        measurement: str,
        total_fields: int,
        filtered_fields: int,
        field_types: Dict[str, int],
    ) -> None:
        """
        Registra información sobre el filtrado de campos.

        Args:
            logger: Logger a usar
            measurement: Nombre de la medición
            total_fields: Total de campos
            filtered_fields: Campos después del filtro
            field_types: Conteo por tipos de campos
        """
        logger.debug(f"Field filtering for {measurement}:")
        logger.debug(f"  Total fields: {total_fields}")
        logger.debug(f"  Filtered fields: {filtered_fields}")
        logger.debug(f"  Field types: {field_types}")

    def log_query_execution(
        self,
        logger: logging.Logger,
        query: str,
        duration: float,
        record_count: int,
    ) -> None:
        """
        Registra la ejecución de una consulta.

        Args:
            logger: Logger a usar
            query: Consulta ejecutada
            duration: Duración en segundos
            record_count: Número de registros retornados
        """
        logger.debug(
            f"Query executed in {duration:.2f}s, returned {record_count} records"
        )
        logger.debug(f"Query: {query}")

    def log_batch_write(
        self,
        logger: logging.Logger,
        database: str,
        measurement: str,
        batch_size: int,
        duration: float,
    ) -> None:
        """
        Registra la escritura de un lote de datos.

        Args:
            logger: Logger a usar
            database: Base de datos destino
            measurement: Medición
            batch_size: Tamaño del lote
            duration: Duración en segundos
        """
        logger.debug(
            f"Batch write to {database}.{measurement}: "
            f"{batch_size} records in {duration:.2f}s"
        )

    def log_pagination_info(
        self,
        logger: logging.Logger,
        page: int,
        total_pages: int,
        records_in_page: int,
    ) -> None:
        """
        Registra información sobre paginación.

        Args:
            logger: Logger a usar
            page: Página actual
            total_pages: Total de páginas
            records_in_page: Registros en la página
        """
        logger.debug(
            f"Processing page {page}/{total_pages} "
            f"with {records_in_page} records"
        )

    def log_schedule_info(
        self, logger: logging.Logger, schedule: str, next_run: datetime
    ) -> None:
        """
        Registra información sobre el scheduling.

        Args:
            logger: Logger a usar
            schedule: Expresión cron
            next_run: Próxima ejecución
        """
        logger.info(f"Backup scheduled: {schedule}")
        logger.info(f"Next run: {next_run}")

    def cleanup(self) -> None:
        """Limpia los recursos del logger."""
        # Obtener todos los loggers asociados con esta configuración
        logger_name = f"backup.{self.config_name}"
        logger = logging.getLogger(logger_name)

        # Cerrar y remover handlers
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)

    def __del__(self) -> None:
        """Destructor para limpiar recursos."""
        try:
            self.cleanup()
        except:
            pass
