import logging

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError

logger = logging.getLogger(__name__)


class InfluxClient:
    """
    Cliente para interactuar con un servidor InfluxDB.
    """

    def __init__(
        self, url, user, password, timeout=20, ssl=False, verify_ssl=True
    ):
        self.url = url
        self.user = user
        self.password = password
        self.timeout = timeout

        # Parsear URL para obtener host y puerto
        try:
            # La división por '://' es robusta tanto para http como para https
            protocol, rest = url.split("://", 1)
            host_part = rest.split("/")[0]  # Ignorar cualquier path en la URL
            if ":" in host_part:
                host, port_str = host_part.split(":")
                port = int(port_str)
            else:
                host = host_part
                port = 443 if ssl else 80  # Puerto por defecto según SSL
        except ValueError as e:
            logger.error(
                f"URL de InfluxDB no válida: {url}. Formato esperado: http(s)://hostname:puerto"
            )
            raise ValueError(f"URL de InfluxDB no válida: {url}") from e

        self.client = InfluxDBClient(
            host=host,
            port=port,
            username=user,
            password=password,
            timeout=timeout,
            ssl=ssl,
            verify_ssl=verify_ssl,
        )
        self.test_connection()

    def test_connection(self):
        """Prueba la conexión con el servidor InfluxDB."""
        try:
            version = self.client.ping()
            logger.info(
                f"Conexión exitosa a {self.url}. Versión de InfluxDB: {version}"
            )
        except InfluxDBClientError as e:
            logger.error(f"No se pudo conectar a InfluxDB en {self.url}: {e}")
            raise ConnectionError(
                f"No se pudo conectar a InfluxDB en {self.url}"
            ) from e

    def query(self, query_string, database):
        """Ejecuta una consulta en una base de datos específica."""
        logger.debug(f"Ejecutando consulta en DB '{database}': {query_string}")
        try:
            self.client.switch_database(database)
            result = self.client.query(query_string)
            return result
        except InfluxDBClientError as e:
            logger.error(
                f"Error al ejecutar consulta en '{database}': {query_string} - Error: {e}"
            )
            return None

    def write_points(self, points, database):
        """Escribe puntos de datos en una base de datos específica."""
        if not points:
            return
        logger.debug(
            f"Escribiendo {len(points)} puntos en la base de datos '{database}'"
        )
        try:
            self.client.switch_database(database)
            self.client.write_points(points)
        except InfluxDBClientError as e:
            logger.error(f"Error al escribir puntos en '{database}': {e}")
            raise

    def get_measurements(self, database):
        """Obtiene la lista de mediciones de una base de datos."""
        logger.debug(f"Obteniendo mediciones de la base de datos '{database}'")
        result = self.query("SHOW MEASUREMENTS", database)
        if result:
            return [item["name"] for item in result.get_points()]
        return []

    def get_field_keys(self, database, measurement):
        """Obtiene los campos y sus tipos para una medición."""
        logger.debug(
            f"Obteniendo campos para la medición '{measurement}' en la DB '{database}'"
        )
        result = self.query(f'SHOW FIELD KEYS FROM "{measurement}"', database)
        if result:
            return {
                item["fieldKey"]: item["fieldType"]
                for item in result.get_points()
            }
        return {}

    def get_first_timestamp(self, database, measurement):
        """
        Obtiene el timestamp del primer punto (el más antiguo) de una medición.
        Devuelve un string en formato RFC3339 o None si no hay datos.
        """
        logger.debug(
            f"Buscando primer timestamp para '{measurement}' en DB '{database}'"
        )
        query_str = f'SELECT * FROM "{measurement}" ORDER BY time ASC LIMIT 1'
        result = self.query(query_str, database)
        if result:
            try:
                return next(result.get_points())["time"]
            except (StopIteration, KeyError):
                logger.debug(
                    f"No se encontraron datos en '{measurement}' en DB '{database}'."
                )
                return None
        return None

    def get_last_timestamp(self, database, measurement):
        """
        Obtiene el timestamp del último punto de una medición.
        Devuelve un string en formato RFC3339 o None si no hay datos.
        """
        logger.debug(
            f"Buscando último timestamp para '{measurement}' en DB '{database}'"
        )
        query_str = f'SELECT * FROM "{measurement}" ORDER BY time DESC LIMIT 1'
        result = self.query(query_str, database)
        if result:
            try:
                # El timestamp se devuelve en la clave 'time' del primer punto
                return next(result.get_points())["time"]
            except (StopIteration, KeyError):
                logger.debug(
                    f"No se encontraron datos en '{measurement}' en DB '{database}'."
                )
                return None
        return None

    def create_database(self, db_name):
        """Crea una nueva base de datos si no existe."""
        logger.info(f"Verificando/creando base de datos de destino: {db_name}")
        try:
            self.client.create_database(db_name)
            logger.info(f"Base de datos '{db_name}' asegurada.")
        except InfluxDBClientError as e:
            logger.error(f"Error al crear la base de datos '{db_name}': {e}")
            raise
