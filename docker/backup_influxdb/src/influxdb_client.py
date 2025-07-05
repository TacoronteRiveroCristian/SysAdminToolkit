"""
Cliente especializado para InfluxDB 1.8
=======================================

Cliente que maneja todas las operaciones con InfluxDB 1.8 incluyendo:
- Creación y gestión de bases de datos
- Consultas con paginación
- Escritura usando Line Protocol
- Manejo de tipos de datos
- Filtrado de campos y mediciones
- Manejo de errores y reintentos
"""

import requests
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from urllib.parse import urlencode
import logging

from .utils import (
    retry_with_backoff, escape_influxdb_identifier,
    build_influxdb_line_protocol, classify_influxdb_type,
    generate_time_ranges, format_influxdb_time, parse_influxdb_time,
    parse_duration, chunks
)


class InfluxDBError(Exception):
    """Excepción base para errores de InfluxDB"""
    pass


class InfluxDBConnectionError(InfluxDBError):
    """Error de conexión a InfluxDB"""
    pass


class InfluxDBQueryError(InfluxDBError):
    """Error en consultas de InfluxDB"""
    pass


class InfluxDBWriteError(InfluxDBError):
    """Error en escritura a InfluxDB"""
    pass


class InfluxDBClient:
    """
    Cliente especializado para InfluxDB 1.8.

    Maneja todas las operaciones con InfluxDB incluyendo consultas,
    escritura, gestión de bases de datos y metadatos.
    """

    def __init__(self, url: str, username: str = None, password: str = None,
                 ssl_verify: bool = True, timeout: int = 30,
                 max_retries: int = 3, retry_delay: float = 1.0,
                 logger: logging.Logger = None):
        """
        Inicializa el cliente de InfluxDB.

        Args:
            url: URL del servidor InfluxDB
            username: Usuario (opcional)
            password: Contraseña (opcional)
            ssl_verify: Verificar SSL
            timeout: Timeout de conexión
            max_retries: Reintentos máximos
            retry_delay: Delay entre reintentos
            logger: Logger para mensajes
        """
        self.url = url.rstrip('/')
        self.username = username
        self.password = password
        self.ssl_verify = ssl_verify
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logger or logging.getLogger(__name__)

        # Configurar sesión HTTP
        self.session = requests.Session()
        self.session.verify = ssl_verify

        # Configurar autenticación
        if username and password:
            self.session.auth = (username, password)

    def _build_query_url(self, params: Dict[str, Any]) -> str:
        """
        Construye la URL de consulta con parámetros.

        Args:
            params: Parámetros de consulta

        Returns:
            str: URL completa
        """
        query_string = urlencode(params)
        return f"{self.url}/query?{query_string}"

    def _build_write_url(self, database: str, precision: str = 'ns') -> str:
        """
        Construye la URL de escritura.

        Args:
            database: Nombre de la base de datos
            precision: Precisión temporal

        Returns:
            str: URL de escritura
        """
        params = {'db': database, 'precision': precision}
        query_string = urlencode(params)
        return f"{self.url}/write?{query_string}"

    @retry_with_backoff(max_retries=3, retry_delay=1.0)
    def _execute_query(self, query: str, database: str = None,
                      epoch: str = None) -> Dict[str, Any]:
        """
        Ejecuta una consulta contra InfluxDB.

        Args:
            query: Consulta SQL
            database: Base de datos (opcional)
            epoch: Formato de timestamp (opcional)

        Returns:
            Dict: Respuesta de InfluxDB

        Raises:
            InfluxDBQueryError: Si la consulta falla
        """
        params = {'q': query}

        if database:
            params['db'] = database

        if epoch:
            params['epoch'] = epoch

        try:
            url = self._build_query_url(params)
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code != 200:
                raise InfluxDBQueryError(f"Query failed with status {response.status_code}: {response.text}")

            result = response.json()

            # Verificar si hay errores en la respuesta
            if 'error' in result:
                raise InfluxDBQueryError(f"Query error: {result['error']}")

            return result

        except requests.exceptions.RequestException as e:
            raise InfluxDBConnectionError(f"Connection failed: {e}")
        except json.JSONDecodeError as e:
            raise InfluxDBQueryError(f"Invalid JSON response: {e}")

    @retry_with_backoff(max_retries=3, retry_delay=1.0)
    def _execute_write(self, database: str, data: str, precision: str = 'ns') -> bool:
        """
        Ejecuta una escritura contra InfluxDB.

        Args:
            database: Base de datos destino
            data: Datos en Line Protocol
            precision: Precisión temporal

        Returns:
            bool: True si fue exitoso

        Raises:
            InfluxDBWriteError: Si la escritura falla
        """
        try:
            url = self._build_write_url(database, precision)

            headers = {'Content-Type': 'application/octet-stream'}

            response = self.session.post(
                url,
                data=data.encode('utf-8'),
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 204:
                return True
            else:
                raise InfluxDBWriteError(f"Write failed with status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            raise InfluxDBConnectionError(f"Connection failed: {e}")

    def test_connection(self) -> bool:
        """
        Prueba la conexión a InfluxDB.

        Returns:
            bool: True si la conexión es exitosa
        """
        try:
            result = self._execute_query("SHOW DATABASES")
            return 'results' in result
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def create_database(self, database: str) -> bool:
        """
        Crea una base de datos si no existe.

        Args:
            database: Nombre de la base de datos

        Returns:
            bool: True si fue creada o ya existía
        """
        try:
            escaped_db = escape_influxdb_identifier(database)
            query = f"CREATE DATABASE {escaped_db}"

            result = self._execute_query(query)
            self.logger.info(f"Database {database} created or already exists")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create database {database}: {e}")
            return False

    def database_exists(self, database: str) -> bool:
        """
        Verifica si una base de datos existe.

        Args:
            database: Nombre de la base de datos

        Returns:
            bool: True si existe
        """
        try:
            result = self._execute_query("SHOW DATABASES")

            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series:
                    databases = [row[0] for row in series[0].get('values', [])]
                    return database in databases

            return False

        except Exception as e:
            self.logger.error(f"Failed to check database existence: {e}")
            return False

    def get_databases(self) -> List[str]:
        """
        Obtiene la lista de bases de datos.

        Returns:
            List[str]: Lista de nombres de bases de datos
        """
        try:
            result = self._execute_query("SHOW DATABASES")

            databases = []
            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series:
                    databases = [row[0] for row in series[0].get('values', [])]

            # Filtrar bases de datos del sistema
            return [db for db in databases if not db.startswith('_')]

        except Exception as e:
            self.logger.error(f"Failed to get databases: {e}")
            return []

    def get_measurements(self, database: str) -> List[str]:
        """
        Obtiene la lista de mediciones de una base de datos.

        Args:
            database: Nombre de la base de datos

        Returns:
            List[str]: Lista de nombres de mediciones
        """
        try:
            result = self._execute_query("SHOW MEASUREMENTS", database)

            measurements = []
            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series:
                    measurements = [row[0] for row in series[0].get('values', [])]

            return measurements

        except Exception as e:
            self.logger.error(f"Failed to get measurements from {database}: {e}")
            return []

    def get_field_keys(self, database: str, measurement: str) -> Dict[str, str]:
        """
        Obtiene los campos y sus tipos de una medición.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición

        Returns:
            Dict[str, str]: Diccionario campo -> tipo
        """
        try:
            escaped_measurement = escape_influxdb_identifier(measurement)
            query = f"SHOW FIELD KEYS FROM {escaped_measurement}"

            result = self._execute_query(query, database)

            fields = {}
            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series:
                    values = series[0].get('values', [])
                    for row in values:
                        field_name, field_type = row[0], row[1]

                        # Mapear tipos de InfluxDB a nuestros tipos
                        if field_type in ['float', 'integer']:
                            fields[field_name] = 'numeric'
                        elif field_type == 'string':
                            fields[field_name] = 'string'
                        elif field_type == 'boolean':
                            fields[field_name] = 'boolean'
                        else:
                            fields[field_name] = 'string'

            return fields

        except Exception as e:
            self.logger.error(f"Failed to get field keys from {database}.{measurement}: {e}")
            return {}

    def get_tag_keys(self, database: str, measurement: str) -> List[str]:
        """
        Obtiene las claves de tags de una medición.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición

        Returns:
            List[str]: Lista de claves de tags
        """
        try:
            escaped_measurement = escape_influxdb_identifier(measurement)
            query = f"SHOW TAG KEYS FROM {escaped_measurement}"

            result = self._execute_query(query, database)

            tags = []
            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series:
                    values = series[0].get('values', [])
                    tags = [row[0] for row in values]

            return tags

        except Exception as e:
            self.logger.error(f"Failed to get tag keys from {database}.{measurement}: {e}")
            return []

    def get_last_timestamp(self, database: str, measurement: str) -> Optional[datetime]:
        """
        Obtiene el último timestamp de una medición.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición

        Returns:
            datetime: Último timestamp o None si no hay datos
        """
        try:
            escaped_measurement = escape_influxdb_identifier(measurement)
            query = f"SELECT * FROM {escaped_measurement} ORDER BY time DESC LIMIT 1"

            result = self._execute_query(query, database, epoch='ns')

            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series and series[0].get('values'):
                    # El primer valor es el timestamp
                    timestamp_ns = series[0]['values'][0][0]
                    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000)

            return None

        except Exception as e:
            self.logger.error(f"Failed to get last timestamp from {database}.{measurement}: {e}")
            return None

    def get_field_last_timestamp(self, database: str, measurement: str, field: str) -> Optional[datetime]:
        """
        Obtiene el último timestamp de un campo específico.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición
            field: Nombre del campo

        Returns:
            datetime: Último timestamp del campo o None
        """
        try:
            escaped_measurement = escape_influxdb_identifier(measurement)
            escaped_field = escape_influxdb_identifier(field)

            query = f"SELECT {escaped_field} FROM {escaped_measurement} WHERE {escaped_field} IS NOT NULL ORDER BY time DESC LIMIT 1"

            result = self._execute_query(query, database, epoch='ns')

            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series and series[0].get('values'):
                    timestamp_ns = series[0]['values'][0][0]
                    return datetime.fromtimestamp(timestamp_ns / 1_000_000_000)

            return None

        except Exception as e:
            self.logger.debug(f"Failed to get last timestamp for field {field}: {e}")
            return None

    def query_data(self, database: str, measurement: str,
                  start_time: datetime, end_time: datetime,
                  fields: List[str] = None, tags: List[str] = None,
                  group_by: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        Consulta datos de una medición en un rango de tiempo.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición
            start_time: Tiempo de inicio
            end_time: Tiempo de fin
            fields: Lista de campos a obtener
            tags: Lista de tags a obtener
            group_by: Cláusula GROUP BY
            limit: Límite de registros

        Returns:
            List[Dict]: Lista de registros
        """
        try:
            # Construir consulta
            escaped_measurement = escape_influxdb_identifier(measurement)

            # Campos a seleccionar
            if fields or tags:
                select_fields = []
                if fields:
                    select_fields.extend([escape_influxdb_identifier(f) for f in fields])
                if tags:
                    select_fields.extend([escape_influxdb_identifier(t) for t in tags])
                select_clause = ', '.join(select_fields)
            else:
                select_clause = '*'

            # Construir consulta base
            query = f"SELECT {select_clause} FROM {escaped_measurement}"

            # Añadir filtro temporal
            start_str = format_influxdb_time(start_time)
            end_str = format_influxdb_time(end_time)
            query += f" WHERE time >= '{start_str}' AND time < '{end_str}'"

            # Añadir GROUP BY si se especifica
            if group_by:
                query += f" GROUP BY {group_by}"

            # Añadir límite
            if limit:
                query += f" LIMIT {limit}"

            # Ejecutar consulta
            result = self._execute_query(query, database, epoch='ns')

            # Procesar resultados
            records = []
            if 'results' in result and result['results']:
                series_list = result['results'][0].get('series', [])

                for series in series_list:
                    columns = series.get('columns', [])
                    values = series.get('values', [])
                    tags_data = series.get('tags', {})

                    for row in values:
                        record = {}

                        # Procesar columnas
                        for i, column in enumerate(columns):
                            if column == 'time':
                                # Convertir timestamp
                                timestamp_ns = row[i]
                                if timestamp_ns:
                                    record['time'] = datetime.fromtimestamp(timestamp_ns / 1_000_000_000)
                            else:
                                record[column] = row[i]

                        # Añadir tags si existen
                        if tags_data:
                            record.update(tags_data)

                        records.append(record)

            return records

        except Exception as e:
            self.logger.error(f"Failed to query data from {database}.{measurement}: {e}")
            return []

    def write_data(self, database: str, measurement: str,
                  records: List[Dict[str, Any]], batch_size: int = 1000) -> bool:
        """
        Escribe datos usando Line Protocol.

        Args:
            database: Base de datos destino
            measurement: Nombre de la medición
            records: Lista de registros a escribir
            batch_size: Tamaño de lote para escritura

        Returns:
            bool: True si fue exitoso
        """
        try:
            if not records:
                return True

            # Dividir en lotes
            record_batches = chunks(records, batch_size)

            for batch in record_batches:
                lines = []

                for record in batch:
                    # Separar timestamp, fields y tags
                    timestamp = record.get('time')
                    timestamp_ns = None

                    if timestamp:
                        if isinstance(timestamp, datetime):
                            timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
                        else:
                            timestamp_ns = int(timestamp)

                    # Separar fields y tags
                    fields = {}
                    tags = {}

                    for key, value in record.items():
                        if key == 'time':
                            continue

                        if value is None:
                            continue

                        # Determinar si es tag o field
                        # Tags son strings, fields pueden ser cualquier tipo
                        if isinstance(value, str) and not key.startswith('_'):
                            tags[key] = value
                        else:
                            fields[key] = value

                    # Construir línea de Line Protocol
                    if fields:  # Solo escribir si hay fields
                        line = build_influxdb_line_protocol(
                            measurement, tags, fields, timestamp_ns
                        )
                        lines.append(line)

                # Escribir lote
                if lines:
                    line_protocol = '\n'.join(lines)
                    success = self._execute_write(database, line_protocol)

                    if not success:
                        return False

                    self.logger.debug(f"Wrote {len(lines)} lines to {database}.{measurement}")

            return True

        except Exception as e:
            self.logger.error(f"Failed to write data to {database}.{measurement}: {e}")
            return False

    def count_records(self, database: str, measurement: str,
                     start_time: datetime = None, end_time: datetime = None) -> int:
        """
        Cuenta el número de registros en una medición.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición
            start_time: Tiempo de inicio (opcional)
            end_time: Tiempo de fin (opcional)

        Returns:
            int: Número de registros
        """
        try:
            escaped_measurement = escape_influxdb_identifier(measurement)
            query = f"SELECT COUNT(*) FROM {escaped_measurement}"

            # Añadir filtro temporal si se especifica
            if start_time or end_time:
                conditions = []
                if start_time:
                    start_str = format_influxdb_time(start_time)
                    conditions.append(f"time >= '{start_str}'")
                if end_time:
                    end_str = format_influxdb_time(end_time)
                    conditions.append(f"time < '{end_str}'")

                if conditions:
                    query += f" WHERE {' AND '.join(conditions)}"

            result = self._execute_query(query, database)

            if 'results' in result and result['results']:
                series = result['results'][0].get('series', [])
                if series and series[0].get('values'):
                    return series[0]['values'][0][1]  # COUNT(*) es el segundo valor

            return 0

        except Exception as e:
            self.logger.error(f"Failed to count records in {database}.{measurement}: {e}")
            return 0

    def get_time_range(self, database: str, measurement: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Obtiene el rango de tiempo de una medición.

        Args:
            database: Nombre de la base de datos
            measurement: Nombre de la medición

        Returns:
            Tuple[datetime, datetime]: (primera_fecha, última_fecha)
        """
        try:
            escaped_measurement = escape_influxdb_identifier(measurement)

            # Obtener primera fecha
            query_first = f"SELECT * FROM {escaped_measurement} ORDER BY time ASC LIMIT 1"
            result_first = self._execute_query(query_first, database, epoch='ns')

            first_time = None
            if 'results' in result_first and result_first['results']:
                series = result_first['results'][0].get('series', [])
                if series and series[0].get('values'):
                    timestamp_ns = series[0]['values'][0][0]
                    first_time = datetime.fromtimestamp(timestamp_ns / 1_000_000_000)

            # Obtener última fecha
            query_last = f"SELECT * FROM {escaped_measurement} ORDER BY time DESC LIMIT 1"
            result_last = self._execute_query(query_last, database, epoch='ns')

            last_time = None
            if 'results' in result_last and result_last['results']:
                series = result_last['results'][0].get('series', [])
                if series and series[0].get('values'):
                    timestamp_ns = series[0]['values'][0][0]
                    last_time = datetime.fromtimestamp(timestamp_ns / 1_000_000_000)

            return first_time, last_time

        except Exception as e:
            self.logger.error(f"Failed to get time range from {database}.{measurement}: {e}")
            return None, None

    def close(self) -> None:
        """Cierra la conexión."""
        if self.session:
            self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def __repr__(self) -> str:
        """Representación en string del cliente."""
        return f"InfluxDBClient(url='{self.url}', timeout={self.timeout})"
