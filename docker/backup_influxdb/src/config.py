import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class Config:
    """
    Carga y gestiona la configuración desde el archivo backup_config.yaml.
    """

    def __init__(self, config_path="config/backup_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self):
        """Carga el archivo de configuración YAML."""
        logger.info(f"Cargando configuración desde: {self.config_path}")
        if not self.config_path.is_file():
            logger.error(
                f"El archivo de configuración no se encuentra en: {self.config_path}"
            )
            raise FileNotFoundError(
                f"El archivo de configuración no se encuentra en: {self.config_path}"
            )

        with open(self.config_path, "r") as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                logger.error(f"Error al parsear el archivo YAML: {e}")
                raise

    def _validate_config(self):
        """Valida que la configuración contenga las claves esenciales."""
        required_keys = ["source", "destination", "options"]
        for key in required_keys:
            if key not in self.config:
                raise ValueError(
                    f"Clave de configuración requerida '{key}' no encontrada."
                )

        if "url" not in self.config.get("source", {}):
            raise ValueError(
                "La URL del InfluxDB de origen ('source.url') es requerida."
            )

        if "url" not in self.config.get("destination", {}):
            raise ValueError(
                "La URL del InfluxDB de destino ('destination.url') es requerida."
            )

        backup_mode = self.get("options.backup_mode")
        if backup_mode not in ["incremental", "range"]:
            raise ValueError(
                f"El modo de backup '{backup_mode}' no es válido. Debe ser 'incremental' o 'range'."
            )

        logger.info("Configuración cargada y validada correctamente.")

    def get(self, key_path, default=None):
        """
        Obtiene un valor de la configuración usando una ruta de claves anidadas.
        Ejemplo: get('source.url')
        """
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value


# Instancia global para ser importada por otros módulos
try:
    config = Config()
except (FileNotFoundError, ValueError) as e:
    logger.critical(f"Error fatal al inicializar la configuración: {e}")
    config = None
