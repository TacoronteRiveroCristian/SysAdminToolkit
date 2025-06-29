import logging
import sys
from logging import FileHandler
from logging.handlers import TimedRotatingFileHandler

from logging_loki import LokiHandler


def setup_logging(
    log_level_str,
    log_file,
    process_name=None,
    rotation_config=None,
    loki_config=None,
):
    """
    Configura el logging para la aplicación.
    """
    if rotation_config is None:
        rotation_config = {}
    if loki_config is None:
        loki_config = {}

    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    if process_name:
        log_format = f"%(asctime)s - [{process_name}] - %(name)s - %(levelname)s - %(message)s"
    else:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    formatter = logging.Formatter(log_format)

    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Limpiar handlers existentes para evitar duplicados
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # Handler para la consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Handler para el archivo de log con rotación
    if log_file:
        try:
            rotation_enabled = rotation_config.get("enabled", False)

            if rotation_enabled:
                # Rotación basada en tiempo
                when = rotation_config.get("when", "D")
                interval = rotation_config.get("interval", 1)
                backup_count = rotation_config.get("backup_count", 5)

                file_handler = TimedRotatingFileHandler(
                    log_file,
                    when=when,
                    interval=interval,
                    backupCount=backup_count,
                    encoding="utf-8",
                )

            else:
                # Handler simple sin rotación si está deshabilitado
                file_handler = FileHandler(log_file, encoding="utf-8")

            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

            if rotation_enabled:
                logging.info(
                    f"Logging con rotación de tiempo configurado para '{log_file}'. "
                    f"BackupCount={backup_count}"
                )
            else:
                logging.info(
                    f"Logging sin rotación configurado para '{log_file}'."
                )

        except Exception as e:
            logging.error(
                f"No se pudo configurar el logging en el archivo {log_file}: {e}"
            )
            logging.error("Los logs solo se mostrarán en la consola.")

    # Handler para Loki
    if loki_config.get("enabled"):
        try:
            loki_url = loki_config.get("url", "loki")
            loki_port = loki_config.get("port", 3100)

            # Las etiquetas base vienen de la config, y añadimos una dinámica
            tags = loki_config.get("tags", {})
            if process_name:
                tags["config_name"] = process_name

            loki_handler = LokiHandler(
                url=f"http://{loki_url}:{loki_port}/loki/api/v1/push",
                tags=tags,
                version="1",
            )

            root_logger.addHandler(loki_handler)
            logging.info(
                f"Logging hacia Loki ({loki_url}:{loki_port}) habilitado."
            )

        except Exception as e:
            logging.error(f"No se pudo configurar el handler para Loki: {e}")

    logging.info(f"Nivel de log establecido en: {log_level_str.upper()}")
