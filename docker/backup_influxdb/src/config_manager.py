"""
Gestor de configuración para el sistema de backup de InfluxDB
============================================================

Maneja la carga, validación y parsing de archivos de configuración YAML
con esquemas robustos y validaciones específicas para InfluxDB.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import yaml
from schema import And
from schema import Optional as SchemaOptional
from schema import Or, Schema, SchemaError

from .utils import (
    get_config_name_from_path,
    parse_duration,
    safe_get_nested_dict,
    validate_influxdb_database_name,
    validate_influxdb_measurement_name,
    validate_url,
)


class ConfigurationError(Exception):
    """Excepción para errores de configuración"""

    pass


class ConfigManager:
    """
    Gestor de configuración para el sistema de backup de InfluxDB.

    Maneja la carga, validación y parsing de archivos de configuración YAML.
    """

    def __init__(self, config_path: str):
        """
        Inicializa el gestor de configuración.

        Args:
            config_path: Ruta al archivo de configuración YAML
        """
        self.config_path = config_path
        self.config_name = get_config_name_from_path(config_path)
        self.config_data = None
        self.logger = logging.getLogger(f"ConfigManager.{self.config_name}")

        # Cargar configuración
        self._load_config()
        self._validate_config()

    def _load_config(self) -> None:
        """Carga el archivo de configuración YAML."""
        try:
            with open(self.config_path, "r", encoding="utf-8") as file:
                self.config_data = yaml.safe_load(file)

            if not self.config_data:
                raise ConfigurationError(
                    f"Empty configuration file: {self.config_path}"
                )

        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}"
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML syntax in {self.config_path}: {e}"
            )
        except Exception as e:
            raise ConfigurationError(
                f"Error loading configuration {self.config_path}: {e}"
            )

    def _get_config_schema(self) -> Schema:
        """
        Define el esquema de validación para la configuración.

        Returns:
            Schema: Esquema de validación
        """
        return Schema(
            {
                "global": {"network": And(str, len)},
                "source": {
                    "url": And(str, validate_url),
                    "ssl": bool,
                    "verify_ssl": bool,
                    "databases": [
                        {
                            "name": And(str, validate_influxdb_database_name),
                            "destination": And(
                                str, validate_influxdb_database_name
                            ),
                        }
                    ],
                    "prefix": str,
                    "suffix": str,
                    "user": str,
                    "password": str,
                    "group_by": str,
                },
                "destination": {
                    "url": And(str, validate_url),
                    "ssl": bool,
                    "verify_ssl": bool,
                    "user": str,
                    "password": str,
                },
                "measurements": {
                    "include": [str],
                    "exclude": [str],
                    SchemaOptional("specific", default={}): {
                        str: {
                            "fields": {
                                "include": [str],
                                "exclude": [str],
                                "types": [
                                    And(
                                        str,
                                        lambda x: x
                                        in ["numeric", "string", "boolean"],
                                    )
                                ],
                            }
                        }
                    },
                },
                "options": {
                    "backup_mode": And(
                        str, lambda x: x in ["incremental", "range"]
                    ),
                    SchemaOptional("range", default={}): {
                        "start_date": And(str, self._validate_iso_date),
                        "end_date": And(str, self._validate_iso_date),
                    },
                    SchemaOptional("incremental", default={}): {
                        "schedule": str
                    },
                    "timeout_client": And(int, lambda x: x > 0),
                    "retries": And(int, lambda x: x >= 0),
                    "retry_delay": And((int, float), lambda x: x >= 0),
                    "days_of_pagination": And(int, lambda x: x > 0),
                    "field_obsolete_threshold": str,
                    "initial_connection_retry_delay": And(
                        (int, float), lambda x: x >= 0
                    ),
                    "log_directory": str,
                    "log_rotation": {
                        "enabled": bool,
                        "when": And(str, lambda x: x in ["D", "H", "M", "S"]),
                        "interval": And(int, lambda x: x > 0),
                        "backup_count": And(int, lambda x: x >= 0),
                    },
                    "loki": {
                        "enabled": bool,
                        "url": str,
                        "port": And(int, lambda x: 1 <= x <= 65535),
                        "tags": {str: str},
                    },
                    "log_level": And(
                        str,
                        lambda x: x
                        in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    ),
                },
            }
        )

    def _validate_iso_date(self, date_str: str) -> bool:
        """
        Valida que una fecha esté en formato ISO 8601.

        Args:
            date_str: Fecha a validar

        Returns:
            bool: True si es válida
        """
        try:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    def _validate_config(self) -> None:
        """Valida la configuración contra el esquema."""
        try:
            schema = self._get_config_schema()
            schema.validate(self.config_data)

            # Validaciones adicionales
            self._validate_additional_rules()

        except SchemaError as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")

    def _validate_additional_rules(self) -> None:
        """Valida reglas adicionales de configuración."""
        # Validar que si backup_mode es 'range', range esté configurado
        if self.get_backup_mode() == "range":
            if not self.get_range_config():
                raise ConfigurationError(
                    "Range configuration is required when backup_mode is 'range'"
                )

        # Validar que las fechas de range sean coherentes
        if self.get_backup_mode() == "range":
            range_config = self.get_range_config()
            start_date = datetime.fromisoformat(
                range_config["start_date"].replace("Z", "+00:00")
            )
            end_date = datetime.fromisoformat(
                range_config["end_date"].replace("Z", "+00:00")
            )

            if start_date >= end_date:
                raise ConfigurationError(
                    "Range start_date must be before end_date"
                )

        # Validar field_obsolete_threshold
        obsolete_threshold = self.get_field_obsolete_threshold()
        if obsolete_threshold:
            try:
                parse_duration(obsolete_threshold)
            except ValueError as e:
                raise ConfigurationError(
                    f"Invalid field_obsolete_threshold: {e}"
                )

        # Validar measurements
        measurements = self.get_measurements_config()
        if measurements.get("include") and measurements.get("exclude"):
            raise ConfigurationError(
                "Cannot use both include and exclude measurement lists"
            )

        # Validar measurements específicas
        specific_measurements = measurements.get("specific", {})
        for measurement_name in specific_measurements.keys():
            if not validate_influxdb_measurement_name(measurement_name):
                raise ConfigurationError(
                    f"Invalid measurement name: {measurement_name}"
                )

    def get_config_name(self) -> str:
        """Retorna el nombre de la configuración."""
        return self.config_name

    def get_network(self) -> str:
        """Retorna la red Docker configurada."""
        return self.config_data["global"]["network"]

    def get_source_config(self) -> Dict:
        """Retorna la configuración del servidor origen."""
        return self.config_data["source"]

    def get_destination_config(self) -> Dict:
        """Retorna la configuración del servidor destino."""
        return self.config_data["destination"]

    def get_measurements_config(self) -> Dict:
        """Retorna la configuración de mediciones."""
        return self.config_data["measurements"]

    def get_options_config(self) -> Dict:
        """Retorna la configuración de opciones."""
        return self.config_data["options"]

    def get_backup_mode(self) -> str:
        """Retorna el modo de backup."""
        return self.config_data["options"]["backup_mode"]

    def get_range_config(self) -> Optional[Dict]:
        """Retorna la configuración de rango si existe."""
        return self.config_data["options"].get("range")

    def get_incremental_config(self) -> Optional[Dict]:
        """Retorna la configuración incremental si existe."""
        return self.config_data["options"].get("incremental")

    def get_databases_to_backup(self) -> List[Dict]:
        """
        Retorna la lista de bases de datos a respaldar.

        Returns:
            List[Dict]: Lista de diccionarios con 'name' y 'destination'
        """
        return self.config_data["source"]["databases"]

    def get_database_prefix(self) -> str:
        """Retorna el prefijo para nombres de bases de datos."""
        return self.config_data["source"].get("prefix", "")

    def get_database_suffix(self) -> str:
        """Retorna el sufijo para nombres de bases de datos."""
        return self.config_data["source"].get("suffix", "")

    def get_final_database_name(
        self, source_name: str, destination_name: str = None
    ) -> str:
        """
        Calcula el nombre final de la base de datos en destino.

        Args:
            source_name: Nombre original en origen
            destination_name: Nombre destino (opcional)

        Returns:
            str: Nombre final con prefijo/sufijo aplicado
        """
        base_name = destination_name or source_name
        prefix = self.get_database_prefix()
        suffix = self.get_database_suffix()

        return f"{prefix}{base_name}{suffix}"

    def get_source_auth(self) -> Optional[Dict]:
        """Retorna la autenticación del origen si está configurada."""
        source = self.get_source_config()
        if source.get("user") and source.get("password"):
            return {"user": source["user"], "password": source["password"]}
        return None

    def get_destination_auth(self) -> Optional[Dict]:
        """Retorna la autenticación del destino si está configurada."""
        destination = self.get_destination_config()
        if destination.get("user") and destination.get("password"):
            return {
                "user": destination["user"],
                "password": destination["password"],
            }
        return None

    def get_group_by(self) -> Optional[str]:
        """Retorna el GROUP BY configurado."""
        group_by = self.get_source_config().get("group_by", "")
        return group_by if group_by else None

    def get_measurements_to_include(self) -> List[str]:
        """Retorna las mediciones a incluir."""
        return self.get_measurements_config().get("include", [])

    def get_measurements_to_exclude(self) -> List[str]:
        """Retorna las mediciones a excluir."""
        return self.get_measurements_config().get("exclude", [])

    def get_measurement_specific_config(
        self, measurement: str
    ) -> Optional[Dict]:
        """
        Retorna la configuración específica de una medición.

        Args:
            measurement: Nombre de la medición

        Returns:
            Dict: Configuración específica o None
        """
        specific = self.get_measurements_config().get("specific", {})
        return specific.get(measurement)

    def get_timeout_client(self) -> int:
        """Retorna el timeout del cliente."""
        return self.get_options_config()["timeout_client"]

    def get_retries(self) -> int:
        """Retorna el número de reintentos."""
        return self.get_options_config()["retries"]

    def get_retry_delay(self) -> float:
        """Retorna el delay entre reintentos."""
        return float(self.get_options_config()["retry_delay"])

    def get_days_of_pagination(self) -> int:
        """Retorna los días de paginación."""
        return self.get_options_config()["days_of_pagination"]

    def get_field_obsolete_threshold(self) -> str:
        """Retorna el umbral de campos obsoletos."""
        return self.get_options_config()["field_obsolete_threshold"]

    def get_initial_connection_retry_delay(self) -> float:
        """Retorna el delay inicial de conexión."""
        return float(
            self.get_options_config()["initial_connection_retry_delay"]
        )

    def get_log_directory(self) -> str:
        """Retorna el directorio de logs."""
        return self.get_options_config()["log_directory"]

    def get_log_rotation_config(self) -> Dict:
        """Retorna la configuración de rotación de logs."""
        return self.get_options_config()["log_rotation"]

    def get_loki_config(self) -> Dict:
        """Retorna la configuración de Loki."""
        return self.get_options_config()["loki"]

    def get_log_level(self) -> str:
        """Retorna el nivel de log."""
        return self.get_options_config()["log_level"]

    def get_schedule(self) -> Optional[str]:
        """Retorna el schedule de cron si existe."""
        incremental = self.get_incremental_config()
        if incremental:
            schedule = incremental.get("schedule", "")
            return schedule if schedule else None
        return None

    def should_backup_measurement(self, measurement: str) -> bool:
        """
        Determina si una medición debe ser respaldada.

        Args:
            measurement: Nombre de la medición

        Returns:
            bool: True si debe ser respaldada
        """
        include_list = self.get_measurements_to_include()
        exclude_list = self.get_measurements_to_exclude()

        # Si hay lista de inclusión, solo respaldar las que están en la lista
        if include_list:
            return measurement in include_list

        # Si no hay lista de inclusión, respaldar todas excepto las excluidas
        return measurement not in exclude_list

    def get_allowed_field_types(self, measurement: str) -> List[str]:
        """
        Retorna los tipos de campos permitidos para una medición.

        Args:
            measurement: Nombre de la medición

        Returns:
            List[str]: Lista de tipos permitidos
        """
        config = self.get_measurement_specific_config(measurement)
        if config and "fields" in config:
            return config["fields"].get(
                "types", ["numeric", "string", "boolean"]
            )
        return ["numeric", "string", "boolean"]

    def get_fields_to_include(self, measurement: str) -> List[str]:
        """
        Retorna los campos a incluir para una medición.

        Args:
            measurement: Nombre de la medición

        Returns:
            List[str]: Lista de campos a incluir (vacía = todos)
        """
        config = self.get_measurement_specific_config(measurement)
        if config and "fields" in config:
            return config["fields"].get("include", [])
        return []

    def get_fields_to_exclude(self, measurement: str) -> List[str]:
        """
        Retorna los campos a excluir para una medición.

        Args:
            measurement: Nombre de la medición

        Returns:
            List[str]: Lista de campos a excluir
        """
        config = self.get_measurement_specific_config(measurement)
        if config and "fields" in config:
            return config["fields"].get("exclude", [])
        return []

    def should_backup_field(
        self, measurement: str, field_name: str, field_type: str
    ) -> bool:
        """
        Determina si un campo debe ser respaldado.

        Args:
            measurement: Nombre de la medición
            field_name: Nombre del campo
            field_type: Tipo del campo

        Returns:
            bool: True si debe ser respaldado
        """
        # Verificar tipos permitidos
        allowed_types = self.get_allowed_field_types(measurement)
        if field_type not in allowed_types:
            return False

        # Verificar campos a incluir
        include_list = self.get_fields_to_include(measurement)
        if include_list:
            return field_name in include_list

        # Verificar campos a excluir
        exclude_list = self.get_fields_to_exclude(measurement)
        return field_name not in exclude_list

    def get_full_log_path(self) -> str:
        """
        Retorna la ruta completa del directorio de logs.

        Returns:
            str: Ruta completa incluyendo subdirectorio por configuración
        """
        base_dir = self.get_log_directory()
        return os.path.join(base_dir, self.config_name)

    def is_ssl_enabled(self, server_type: str) -> bool:
        """
        Verifica si SSL está habilitado para un servidor.

        Args:
            server_type: 'source' o 'destination'

        Returns:
            bool: True si SSL está habilitado
        """
        if server_type == "source":
            return self.get_source_config()["ssl"]
        elif server_type == "destination":
            return self.get_destination_config()["ssl"]
        else:
            raise ValueError(f"Invalid server_type: {server_type}")

    def should_verify_ssl(self, server_type: str) -> bool:
        """
        Verifica si se debe verificar el certificado SSL.

        Args:
            server_type: 'source' o 'destination'

        Returns:
            bool: True si se debe verificar
        """
        if server_type == "source":
            return self.get_source_config()["verify_ssl"]
        elif server_type == "destination":
            return self.get_destination_config()["verify_ssl"]
        else:
            raise ValueError(f"Invalid server_type: {server_type}")

    def to_dict(self) -> Dict:
        """
        Retorna la configuración completa como diccionario.

        Returns:
            Dict: Configuración completa
        """
        return self.config_data.copy()

    def __repr__(self) -> str:
        """Representación en string del objeto."""
        return f"ConfigManager(config_name='{self.config_name}', backup_mode='{self.get_backup_mode()}')"
