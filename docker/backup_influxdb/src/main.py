import glob
import logging
import multiprocessing
import os
import sys
import time
from pathlib import Path

# Añadir el directorio 'src' al sys.path para importaciones relativas
# Esto es útil si el script se ejecuta desde el directorio raíz del proyecto
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from src.backup import BackupManager
from src.config import Config
from src.influx_client import InfluxClient
from src.logger_config import setup_logging
from src.scheduler import Scheduler, run_job_once

# Configuración inicial del logger para el proceso principal
setup_logging("INFO", None, process_name="main")
logger = logging.getLogger(__name__)


def initialize_clients(config: Config):
    """
    Intenta inicializar los clientes de InfluxDB con reintentos indefinidos.
    """
    retry_delay = config.get("options.initial_connection_retry_delay", 60)

    source_url = config.get("source.url")
    dest_url = config.get("destination.url")

    if not source_url or not dest_url:
        logger.critical(
            "Las URLs de origen y destino son obligatorias en la configuración."
        )
        # Salir del proceso worker si falta configuración esencial.
        # No se puede continuar sin URLs.
        raise ValueError(
            "URLs de InfluxDB no especificadas en la configuración."
        )

    while True:
        try:
            logger.info("Inicializando clientes de InfluxDB...")
            source_client = InfluxClient(
                url=source_url,
                user=config.get("source.user", ""),
                password=config.get("source.password", ""),
                timeout=config.get("options.timeout_client", 20),  # type: ignore
                ssl=config.get("source.ssl", False),  # type: ignore
                verify_ssl=config.get("source.verify_ssl", True),  # type: ignore
            )

            dest_client = InfluxClient(
                url=dest_url,
                user=config.get("destination.user", ""),
                password=config.get("destination.password", ""),
                timeout=config.get("options.timeout_client", 20),  # type: ignore
                ssl=config.get("destination.ssl", False),  # type: ignore
                verify_ssl=config.get("destination.verify_ssl", True),  # type: ignore
            )
            logger.info("Clientes de InfluxDB inicializados correctamente.")
            return source_client, dest_client

        except Exception as e:
            logger.warning(
                f"No se pudo conectar a InfluxDB: {e}. "
                f"Reintentando en {retry_delay} segundos..."
            )
            time.sleep(retry_delay)  # type: ignore


def run_worker(config_path: str):
    """
    Función trabajadora que ejecuta un único proceso de backup para una configuración.
    """
    config_name = Path(config_path).stem

    # Configuración de logging para este proceso específico
    # Esto se hace aquí para que cada proceso tenga su logger configurado correctamente.
    try:
        config = Config(config_path)
    except (FileNotFoundError, ValueError) as e:
        # Usamos el logger principal para notificar este error
        logger.error(
            f"Error al cargar la configuración {config_path}: {e}. Saltando este backup."
        )
        return

    log_level = config.get("options.log_level", "INFO")
    log_rotation_config = config.get("options.log_rotation", {})
    loki_config = config.get("options.loki", {})

    # Crear la ruta del log a partir del directorio y el nombre de la config
    base_log_dir = (
        config.get("options.log_directory") or "/var/log/backup_influxdb/"
    )
    log_dir = os.path.join(base_log_dir, config_name)

    # Asegurarse de que el directorio de logs exista
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, f"{config_name}.log")

    setup_logging(
        log_level,
        log_file,
        process_name=config_name,
        rotation_config=log_rotation_config,
        loki_config=loki_config,
    )

    logger.info(f"Iniciando proceso de backup para '{config_name}'")

    try:
        # Inicializar clientes de InfluxDB con reintentos
        source_client, dest_client = initialize_clients(config)

        # Inicializar el gestor de backup
        backup_manager = BackupManager(config, source_client, dest_client)

        # Determinar el modo de ejecución
        backup_mode = config.get("options.backup_mode")

        if backup_mode == "range":
            run_job_once(backup_manager.run_backup)
            logger.info(f"Backup 'range' completado para '{config_name}'.")

        elif backup_mode == "incremental":
            cron_schedule = config.get("options.incremental.schedule", "")
            if cron_schedule:
                logger.info(
                    f"Iniciando planificador (cron) para '{config_name}'."
                )
                scheduler = Scheduler(backup_manager.run_backup, cron_schedule)
                scheduler.start()  # Esta llamada es bloqueante y el proceso se quedará aquí
            else:
                run_job_once(backup_manager.run_backup)
                logger.info(
                    f"Backup 'incremental' único completado para '{config_name}'."
                )

    except (ConnectionError, ValueError) as e:
        logger.critical(
            f"Error de inicialización en '{config_name}': {e}. El proceso no puede continuar."
        )
    except Exception as e:
        logger.critical(
            f"Ha ocurrido un error inesperado en el proceso de '{config_name}': {e}",
            exc_info=True,
        )


def main():
    """
    Función principal que busca archivos de configuración y lanza un proceso
    de backup para cada uno en paralelo.
    """
    logger.info("Iniciando el Orquestador de Backups de InfluxDB.")

    config_dir = os.path.join(os.path.dirname(__file__), "..", "config")
    config_files = glob.glob(os.path.join(config_dir, "*.yaml"))

    # Excluir archivos de plantilla
    config_files = [f for f in config_files if not f.endswith(".template.yaml")]

    if not config_files:
        logger.warning(
            "No se encontraron archivos de configuración .yaml en el directorio /config. No se iniciará ningún backup."
        )
        return

    logger.info(
        f"Se encontraron {len(config_files)} archivos de configuración: {[Path(f).name for f in config_files]}"
    )

    processes = []
    for config_file in config_files:
        process = multiprocessing.Process(
            target=run_worker, args=(config_file,)
        )
        processes.append(process)
        process.start()
        logger.info(
            f"Lanzado proceso para {Path(config_file).name} (PID: {process.pid})"
        )

    for process in processes:
        process.join()

    logger.info("Todos los procesos de backup han finalizado.")


if __name__ == "__main__":
    # La protección de __name__ == "__main__" es crucial para multiprocessing
    multiprocessing.set_start_method(
        "fork", force=True
    )  # Recomendado en algunos entornos Linux/Docker
    main()
