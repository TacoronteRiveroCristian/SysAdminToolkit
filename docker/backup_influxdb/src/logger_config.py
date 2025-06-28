import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(log_level_str, log_file):
    """
    Configura el logging para la aplicación.
    """
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

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
            # Rotación de 10MB por archivo, manteniendo 5 archivos de backup
            file_handler = RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            logging.info(
                f"Logging configurado para escribir en el archivo: {log_file}"
            )
        except Exception as e:
            logging.error(
                f"No se pudo configurar el logging en el archivo {log_file}: {e}"
            )
            logging.error("Los logs solo se mostrarán en la consola.")

    logging.info(f"Nivel de log establecido en: {log_level_str.upper()}")
