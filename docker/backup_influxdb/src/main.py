import logging
import os
import sys

# Añadir el directorio 'src' al sys.path para importaciones relativas
# Esto es útil si el script se ejecuta desde el directorio raíz del proyecto
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)

from src.backup import BackupManager
from src.config import config
from src.influx_client import InfluxClient
from src.logger_config import setup_logging
from src.scheduler import Scheduler, run_job_once

# Configuración inicial del logger para capturar errores tempranos
# Se reconfigurará después de cargar el archivo de configuración
setup_logging("INFO", None)

logger = logging.getLogger(__name__)


def main():
    """
    Función principal que orquesta todo el proceso de backup.
    """
    # Salir si la configuración no se pudo cargar
    if config is None:
        logger.critical(
            "No se pudo cargar la configuración. Revise los logs para más detalles. Abortando."
        )
        sys.exit(1)

    # Reconfigurar el logging con los valores del archivo de configuración
    log_level = config.get("options.log_level", "INFO")
    log_file = config.get(
        "options.log_file", "/var/log/backup_influxdb/backup.log"
    )
    setup_logging(log_level, log_file)

    try:
        # Inicializar clientes de InfluxDB
        logger.info("Inicializando clientes de InfluxDB...")
        source_client = InfluxClient(
            url=config.get("source.url"),
            user=config.get("source.user", ""),
            password=config.get("source.password", ""),
            timeout=config.get("options.timeout_client", 20),
            ssl=config.get("source.ssl", False),
            verify_ssl=config.get("source.verify_ssl", True),
        )

        dest_client = InfluxClient(
            url=config.get("destination.url"),
            user=config.get("destination.user", ""),
            password=config.get("destination.password", ""),
            timeout=config.get("options.timeout_client", 20),
            ssl=config.get("destination.ssl", False),
            verify_ssl=config.get("destination.verify_ssl", True),
        )
        logger.info("Clientes de InfluxDB inicializados correctamente.")

        # Inicializar el gestor de backup
        backup_manager = BackupManager(config, source_client, dest_client)

        # Determinar el modo de ejecución
        backup_mode = config.get("options.backup_mode")

        if backup_mode == "range":
            # Ejecutar una vez para el rango y salir
            run_job_once(backup_manager.run_backup)

        elif backup_mode == "incremental":
            cron_schedule = config.get("incremental.schedule", "")
            if cron_schedule:
                # Ejecución programada
                scheduler = Scheduler(backup_manager.run_backup, cron_schedule)
                scheduler.start()
            else:
                # Ejecutar una vez en modo incremental y salir
                run_job_once(backup_manager.run_backup)

    except (ConnectionError, ValueError) as e:
        logger.critical(
            f"Error de inicialización: {e}. El programa no puede continuar."
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"Ha ocurrido un error inesperado en el flujo principal: {e}",
            exc_info=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
