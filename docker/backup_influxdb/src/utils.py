"""
Utilidades para el sistema de backup de InfluxDB
================================================

Funciones de ayuda para fechas, paginación, parsing de duraciones,
validaciones y otras utilidades comunes.
"""

import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from dateutil.parser import parse as parse_datetime


def parse_duration(duration_str: str) -> timedelta:
    """
    Parsea una cadena de duración en un objeto timedelta.

    Formatos soportados:
    - "6M" (6 meses)
    - "2w" (2 semanas)
    - "30d" (30 días)
    - "12h" (12 horas)
    - "45m" (45 minutos)
    - "30s" (30 segundos)
    - "1y" (1 año)

    Args:
        duration_str: String de duración

    Returns:
        timedelta: Objeto timedelta correspondiente

    Raises:
        ValueError: Si el formato no es válido
    """
    if not duration_str:
        raise ValueError("Duration string cannot be empty")

    # Regex para parsear duración
    pattern = r"^(\d+)(s|m|h|d|w|M|y)$"
    match = re.match(pattern, duration_str.strip())

    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value = int(match.group(1))
    unit = match.group(2)

    # Conversiones
    if unit == "s":
        return timedelta(seconds=value)
    elif unit == "m":
        return timedelta(minutes=value)
    elif unit == "h":
        return timedelta(hours=value)
    elif unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    elif unit == "M":
        # Aproximación: 1 mes = 30 días
        return timedelta(days=value * 30)
    elif unit == "y":
        # Aproximación: 1 año = 365 días
        return timedelta(days=value * 365)
    else:
        raise ValueError(f"Unknown unit: {unit}")


def parse_influxdb_time(time_str: str) -> datetime:
    """
    Parsea una cadena de tiempo de InfluxDB en un objeto datetime.

    Args:
        time_str: String de tiempo (ISO 8601)

    Returns:
        datetime: Objeto datetime
    """
    return parse_datetime(time_str)


def format_influxdb_time(dt: datetime) -> str:
    """
    Formatea un datetime para InfluxDB.

    Args:
        dt: Objeto datetime

    Returns:
        str: String de tiempo en formato ISO 8601
    """
    return dt.isoformat() + "Z" if dt.tzinfo is None else dt.isoformat()


def generate_time_ranges(
    start_time: datetime, end_time: datetime, chunk_days: int
) -> List[Tuple[datetime, datetime]]:
    """
    Genera rangos de tiempo para paginación.

    Args:
        start_time: Tiempo de inicio
        end_time: Tiempo de fin
        chunk_days: Días por chunk

    Returns:
        List[Tuple[datetime, datetime]]: Lista de rangos (inicio, fin)
    """
    ranges = []
    current_start = start_time

    while current_start < end_time:
        current_end = min(current_start + timedelta(days=chunk_days), end_time)
        ranges.append((current_start, current_end))
        current_start = current_end

    return ranges


def validate_influxdb_measurement_name(name: str) -> bool:
    """
    Valida que el nombre de una medición de InfluxDB sea válido.

    Args:
        name: Nombre de la medición

    Returns:
        bool: True si es válido
    """
    if not name:
        return False

    # InfluxDB permite caracteres alfanuméricos, guiones y guiones bajos
    # No puede empezar con número
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_.-]*$"
    return bool(re.match(pattern, name))


def validate_influxdb_database_name(name: str) -> bool:
    """
    Valida que el nombre de una base de datos de InfluxDB sea válido.

    Args:
        name: Nombre de la base de datos

    Returns:
        bool: True si es válido
    """
    if not name:
        return False

    # Nombres reservados en InfluxDB
    reserved_names = ["_internal"]
    if name in reserved_names:
        return False

    # Similar a mediciones pero más restrictivo
    pattern = r"^[a-zA-Z_][a-zA-Z0-9_-]*$"
    return bool(re.match(pattern, name))


def escape_influxdb_identifier(identifier: str) -> str:
    """
    Escapa un identificador para InfluxDB agregando comillas si es necesario.

    Args:
        identifier: Identificador a escapar

    Returns:
        str: Identificador escapado
    """
    # Si contiene caracteres especiales, agregamos comillas
    if re.search(r"[^a-zA-Z0-9_]", identifier):
        return f'"{identifier}"'
    return identifier


def escape_influxdb_string_value(value: str) -> str:
    """
    Escapa un valor string para InfluxDB.

    Args:
        value: Valor a escapar

    Returns:
        str: Valor escapado
    """
    # Escapar comillas simples y backslashes
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def classify_influxdb_type(value: Any) -> str:
    """
    Clasifica el tipo de un valor para InfluxDB.

    Args:
        value: Valor a clasificar

    Returns:
        str: Tipo ('numeric', 'string', 'boolean')
    """
    if isinstance(value, bool):
        return "boolean"
    elif isinstance(value, (int, float)):
        return "numeric"
    else:
        return "string"


def format_influxdb_value(value: Any, field_type: str = None) -> str:
    """
    Formatea un valor para el Line Protocol de InfluxDB.

    Args:
        value: Valor a formatear
        field_type: Tipo del campo (opcional)

    Returns:
        str: Valor formateado
    """
    if value is None:
        return ""

    if isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        # String value
        return escape_influxdb_string_value(str(value))


def build_influxdb_line_protocol(
    measurement: str,
    tags: Dict[str, str],
    fields: Dict[str, Any],
    timestamp: Optional[int] = None,
) -> str:
    """
    Construye una línea de Line Protocol para InfluxDB.

    Args:
        measurement: Nombre de la medición
        tags: Diccionario de tags
        fields: Diccionario de fields
        timestamp: Timestamp en nanosegundos (opcional)

    Returns:
        str: Línea de Line Protocol
    """
    # Measurement
    line = escape_influxdb_identifier(measurement)

    # Tags (opcionales)
    if tags:
        tag_strs = []
        for key, value in sorted(tags.items()):
            escaped_key = escape_influxdb_identifier(key)
            escaped_value = (
                str(value)
                .replace(" ", "\\ ")
                .replace(",", "\\,")
                .replace("=", "\\=")
            )
            tag_strs.append(f"{escaped_key}={escaped_value}")
        line += "," + ",".join(tag_strs)

    # Fields (obligatorios)
    field_strs = []
    for key, value in fields.items():
        escaped_key = escape_influxdb_identifier(key)
        formatted_value = format_influxdb_value(value)
        if formatted_value:  # Solo agregar si el valor no está vacío
            field_strs.append(f"{escaped_key}={formatted_value}")

    if not field_strs:
        raise ValueError("At least one field is required")

    line += " " + ",".join(field_strs)

    # Timestamp (opcional)
    if timestamp is not None:
        line += f" {timestamp}"

    return line


def retry_with_backoff(
    max_retries: int,
    retry_delay: float,
    logger: Optional[logging.Logger] = None,
):
    """
    Decorador para reintentar una función con backoff exponencial.

    Args:
        max_retries: Número máximo de reintentos
        retry_delay: Delay inicial entre reintentos (segundos)
        logger: Logger para mensajes de reintento

    Returns:
        Decorador
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e

                    if attempt < max_retries:
                        wait_time = retry_delay * (2**attempt)
                        if logger:
                            logger.warning(
                                f"Attempt {attempt + 1} failed: {e}. "
                                f"Retrying in {wait_time:.2f} seconds..."
                            )
                        time.sleep(wait_time)
                    else:
                        if logger:
                            logger.error(
                                f"All {max_retries + 1} attempts failed"
                            )
                        raise last_exception

            raise last_exception

        return wrapper

    return decorator


def get_config_name_from_path(config_path: str) -> str:
    """
    Obtiene el nombre de configuración desde la ruta del archivo.

    Args:
        config_path: Ruta del archivo de configuración

    Returns:
        str: Nombre de la configuración (sin extensión)
    """
    import os

    return os.path.splitext(os.path.basename(config_path))[0]


def safe_get_nested_dict(data: Dict, path: str, default: Any = None) -> Any:
    """
    Obtiene un valor de un diccionario anidado usando una ruta con puntos.

    Args:
        data: Diccionario fuente
        path: Ruta con puntos (ej: "source.databases.0.name")
        default: Valor por defecto

    Returns:
        Any: Valor encontrado o default
    """
    try:
        keys = path.split(".")
        current = data

        for key in keys:
            if key.isdigit():
                current = current[int(key)]
            else:
                current = current[key]

        return current
    except (KeyError, IndexError, TypeError):
        return default


def validate_url(url: str) -> bool:
    """
    Valida que una URL sea válida.

    Args:
        url: URL a validar

    Returns:
        bool: True si es válida
    """
    url_pattern = re.compile(
        r"^https?://"  # http:// o https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    return bool(url_pattern.match(url))


def sanitize_tag_value(value: str) -> str:
    """
    Sanitiza un valor de tag para InfluxDB.

    Args:
        value: Valor a sanitizar

    Returns:
        str: Valor sanitizado
    """
    # Remover caracteres problemáticos
    sanitized = str(value).replace(" ", "_").replace(",", "_").replace("=", "_")
    return sanitized


def calculate_memory_usage_mb() -> float:
    """
    Calcula el uso de memoria actual en MB.

    Returns:
        float: Uso de memoria en MB
    """
    try:
        import psutil

        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return 0.0


def get_process_id() -> int:
    """
    Obtiene el ID del proceso actual.

    Returns:
        int: PID del proceso
    """
    import os

    return os.getpid()


def is_port_open(host: str, port: int, timeout: float = 5.0) -> bool:
    """
    Verifica si un puerto está abierto.

    Args:
        host: Host a verificar
        port: Puerto a verificar
        timeout: Timeout para la conexión

    Returns:
        bool: True si el puerto está abierto
    """
    import socket

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, socket.timeout):
        return False


def chunks(lst: List, chunk_size: int) -> List[List]:
    """
    Divide una lista en chunks de tamaño específico.

    Args:
        lst: Lista a dividir
        chunk_size: Tamaño de cada chunk

    Returns:
        List[List]: Lista de chunks
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]


def get_current_timestamp_ns() -> int:
    """
    Obtiene el timestamp actual en nanosegundos.

    Returns:
        int: Timestamp en nanosegundos
    """
    return int(time.time() * 1_000_000_000)


def ns_to_datetime(ns_timestamp: int) -> datetime:
    """
    Convierte un timestamp en nanosegundos a datetime.

    Args:
        ns_timestamp: Timestamp en nanosegundos

    Returns:
        datetime: Objeto datetime
    """
    return datetime.fromtimestamp(ns_timestamp / 1_000_000_000)


def datetime_to_ns(dt: datetime) -> int:
    """
    Convierte un datetime a timestamp en nanosegundos.

    Args:
        dt: Objeto datetime

    Returns:
        int: Timestamp en nanosegundos
    """
    return int(dt.timestamp() * 1_000_000_000)
