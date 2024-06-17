"""
Script para realizar copias de seguridad de una o varias bases de datos
de un servidor a otro.

En el caso de que se realice por primera vez la copia de seguridad, intentara
coger todos los datos en una misma query. Si hay demasiados, saldra un warning en los logs
y se intentará relaizar el proceso de paginacion semanal.

En el caso de que no se realice correctamente la copia de seguridad, es aconsejable borrar la base
de datos de destino (en el caso de que se haya creado y/o volcado datos) y repetir el procedimiento desde un principio.

Si ya hay datos en la base de datos de destino, se hará una copia de los datos teniendo en cuenta el datetime mas reciente
del measurement correspondiente.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional

from dateutil.parser import parse
from dotenv import load_dotenv
from influxdb import InfluxDBClient
from influxdb.resultset import ResultSet

# Cargar variables de entorno
load_dotenv()

# Configuración de logging
LOG_FILE = os.getenv("LOG_FILE", "backup_log.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Parámetros de InfluxDB
SOURCE_URL = os.getenv("SOURCE_URL")
SOURCE_DBS = os.getenv("SOURCE_DBS").split(",")
SOURCE_GROUP_BY = os.getenv("SOURCE_GROUP_BY", "5m")
DEST_URL = os.getenv("DEST_URL")
DEST_DBS = os.getenv("DEST_DBS").split(",")

# Verificar que las listas de bases de datos de origen y destino tengan la misma longitud
# ya que cada base de datos "source" sera la correspondiente para la base de datos "dest"
if len(SOURCE_DBS) != len(DEST_DBS):
    logger.error(
        "Las listas de bases de datos de origen y destino no coinciden en longitud."
    )
    raise ValueError(
        "Las listas de bases de datos de origen y destino deben tener la misma longitud."
    )

# Crear cliente de InfluxDB para origen y destino
SOURCE_CLIENT = InfluxDBClient(
    host=SOURCE_URL.split(":")[1].replace("//", ""),
    port=int(
        SOURCE_URL.split(":")[2],
    ),
    username=os.getenv("SOURCE_USER"),
    password=os.getenv("SOURCE_PASSWORD"),
    timeout=int(os.getenv("TIMEOUT_CLIENT")),
)
DEST_CLIENT = InfluxDBClient(
    host=DEST_URL.split(":")[1].replace("//", ""),
    port=int(
        DEST_URL.split(":")[2],
    ),
    username=os.getenv("DEST_USER"),
    password=os.getenv("DEST_PASSWORD"),
    timeout=int(os.getenv("TIMEOUT_CLIENT")),
)


def check_connection(client: InfluxDBClient) -> bool:
    """
    Verifica si la conexión al cliente dado es exitosa.

    :param client: El cliente para verificar la conexión.
    :type client: :class:`InfluxDBClient`
    :return: True si la conexión es exitosa, False en caso contrario.
    :rtype: bool
    """
    try:
        client.ping()
        logger.info(f"Conexión exitosa a con el host '{client._host}:{client._port}'.")
        return True
    except Exception as e:
        logger.error(f"Conexión fallida a '{client._host}:{client._port}': {str(e)}")
        return False


def get_entry_time(
    client: InfluxDBClient, measurement: str, order: Literal["ASC", "DESC"]
) -> Optional[str]:
    """
    Obtiene la marca de tiempo del primer o último registro en la medición dada.

    :param client: El cliente para consultar la base de datos.
    :type client: :class:`InfluxDBClient`
    :param measurement: El nombre de la medición.
    :type measurement: str
    :param order: El orden en el que se deben obtener los registros ("ASC" para el primer registro, "DESC" para el último registro).
    :type order: str
    :return: La marca de tiempo del primer o último registro en la medición,
    o None si no se encuentra ningún registro.
    :rtype: Optional[str]
    """
    query = f"SELECT * FROM {measurement} ORDER BY time {order} LIMIT 1"
    try:
        result = client.query(query)
        if result:
            points = list(result.get_points())
            if points:
                # Obtener la marca de tiempo del primer o último registro y normalizarlo
                datetime_str = parse(points[0]["time"]).strftime("%Y-%m-%dT%H:%M:%SZ")
                return datetime_str
        return None
    except Exception as e:
        logger.error(
            f"\tError al obtener el registro del measurement '{measurement}' en orden '{order}': {str(e)}"
        )
        return None


def build_list_points(result: ResultSet, measurement: str) -> List[Dict[str, Any]]:
    """
    Construye una lista de puntos desde el resultado de una consulta de InfluxDB.

    :param result: El resultado de la consulta de InfluxDB.
    :type result: ResultSet
    :param measurement: El nombre de la medición.
    :type measurement: str
    :return: Una lista de puntos con sus respectivos campos y valores.
    :rtype: List[Dict[str, Any]]
    """
    points = []
    for _, series in result.items():
        for _point in series:
            # Crear lista de puntos
            point = {
                "time": _point["time"],
                "measurement": measurement,
                "fields": {
                    key.replace("mean_", ""): value
                    for key, value in _point.items()
                    if value is not None and key != "time"
                },
            }
            # Comprobar que el diccionario de valores no este vacío
            if len(point["fields"]) > 0:
                points.append(point)

    return points


def copy_data_since_last_entry(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    last_entry_time: str,
    measurement: str,
    group_by: str,
) -> bool:
    """
    Copia los datos desde la última entrada hasta el presente.

    :param source_client: El cliente de InfluxDB de origen.
    :type source_client: :class:`InfluxDBClient`
    :param dest_client: El cliente de InfluxDB de destino.
    :type dest_client: :class:`InfluxDBClient`
    :param last_entry_time: La marca de tiempo de la última entrada.
    :type last_entry_time: str
    :param measurement: El nombre de la medición.
    :type measurement: str
    :param group_by: El valor de agrupación de tiempo.
    :type group_by: str
    :return: Ninguno.
    :rtype: None
    """
    # Crear query para obtener los datos desde el registro anterior
    if last_entry_time:
        section_last_entry_time = f"WHERE time >= '{last_entry_time}'"
    else:
        section_last_entry_time = ""
    query = f"SELECT MEAN(*) FROM {measurement} {section_last_entry_time} GROUP BY time({group_by})"
    try:
        logger.info(
            f"\tIniciando copia de seguridad para el measurement '{measurement}'."
        )
        # Ejecutar query
        result = source_client.query(query)
        # Obtener lista de puntos
        points = build_list_points(result, measurement)
        # Cpomprobar si la lista no es nula. Si es cierto, registrar los datos en el servidor de destino
        if points:
            dest_client.write_points(points, batch_size=5000)
            logger.info(
                f"\tDatos del measurement '{measurement}' copiados exitosamente desde la marca de tiempo '{last_entry_time}' (puntos registrados: {len(points)})."
            )
        # Devuelve True si no se ha generado ningun error
        return True
    except OverflowError as e:
        logger.warning(
            f"\tError del tipo 'OverflowError' al copiar los datos del measurement '{measurement}': {str(e)}"
        )
        return False
    except Exception as e:
        logger.warning(
            f"\tError al copiar los datos del measurement '{measurement}': {str(e)}"
        )
        return False


def copy_data_with_pagination(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    first_entry_time: str,
    measurement: str,
    group_by: str,
) -> bool:
    """ """
    str_format_datetime_query = "%Y-%m-%dT%H:%M:%SZ"
    str_format_datetime_log = "%Y-%m-%dT%H:%M:%SZ"
    days_timedelta = 7
    try:
        # Fecha de inicio (hacia atras)
        start_date = datetime.now(timezone.utc)
        # Fecha de fin (hacia atras)
        end_date = start_date - timedelta(days=days_timedelta)

        # Transformar fecha del primer registro y crear la expresion de paginacion
        if first_entry_time:
            first_entry_time = datetime.strptime(
                first_entry_time, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)

            cond_pagination = start_date >= first_entry_time
        else:
            cond_pagination = True

        cum_points = 0
        while cond_pagination:
            # Construir query dinámica
            query = (
                f"SELECT MEAN(*) FROM {measurement} "
                f"WHERE time >= '{end_date.strftime(str_format_datetime_query)}' AND time < '{start_date.strftime(str_format_datetime_query)}' "
                f"GROUP BY time({group_by})"
            )
            logger.info(
                f"\t\tCopia de seguridad para el measurement '{measurement}' para el periodo {end_date.strftime(str_format_datetime_log)} a {start_date.strftime(str_format_datetime_log)}."
            )

            # Ejecutar query
            result = source_client.query(query)
            # Obtener lista de puntos
            points = build_list_points(result, measurement)
            # Comprobar si la lista no es nula. Si es cierto, registrar los datos en el servidor de destino
            if points:
                cum_points += len(points)
                dest_client.write_points(points, batch_size=1000)
            else:
                # Si no hay datos, romper el bucle
                logger.info(
                    f"\t\tNo hay más datos para el measurement '{measurement}'. Paginación finalizada (puntos registrados: {cum_points})."
                )
                break

            # Mover el período un mes hacia atrás
            start_date = end_date
            end_date = start_date - timedelta(days=days_timedelta)

        # Devuelve True si no se ha generado ningún error
        return True
    except Exception as e:
        logger.error(
            f"\t\tError al copiar los datos del measurement '{measurement}': {str(e)}"
        )
        return False


if __name__ == "__main__":
    # Verificar la conexión de cada cliente
    if check_connection(SOURCE_CLIENT) and check_connection(DEST_CLIENT):
        try:
            # Recorrer cada base de datos
            for source_db, dest_db in zip(SOURCE_DBS, DEST_DBS):
                # Apuntar a la base de datos correspondiente
                SOURCE_CLIENT.switch_database(source_db)
                logger.info(
                    f"Iniciando copia de datos de '{SOURCE_CLIENT._host}:{source_db}' a '{DEST_CLIENT._host}:{dest_db}'."
                )
                # Recorrer cada measurement
                for measurement in SOURCE_CLIENT.get_list_measurements():
                    if measurement["name"] == "CONTENEDOR_NON_STANDARD":
                        pass
                    # Crear la base de datos si no existe y apuntar a la base de datos correspondiente
                    DEST_CLIENT.create_database(dest_db)
                    DEST_CLIENT.switch_database(dest_db)
                    # Obtener el último registro del measurement de destino para saber desde donde se
                    # debe copiar los datos
                    last_entry_time = get_entry_time(
                        DEST_CLIENT,
                        measurement["name"],
                        "DESC",
                    )
                    # Copiar datos desde el último registro
                    result_copy_data_since_last_entry = copy_data_since_last_entry(
                        SOURCE_CLIENT,
                        DEST_CLIENT,
                        last_entry_time,
                        measurement["name"],
                        SOURCE_GROUP_BY,
                    )
                    # result_copy_data_since_last_entry = False
                    # Verificar el resultado de la operación
                    if not result_copy_data_since_last_entry:
                        logger.info(
                            f"\tIntentando paginación para el measurement '{measurement['name']}'..."
                        )
                        # TODO que comience desde la fecha actual pero tiene que tener como target final el dato mas antiguo
                        # para que no se quede nada atras
                        first_entry_time = get_entry_time(
                            SOURCE_CLIENT,
                            measurement["name"],
                            "ASC",
                        )
                        result_copy_data_with_pagination = copy_data_with_pagination(
                            SOURCE_CLIENT,
                            DEST_CLIENT,
                            first_entry_time,
                            measurement["name"],
                            SOURCE_GROUP_BY,
                        )
        except Exception as e:
            logger.error(
                f"Error al realizar la copia de datos con el measurement '{measurement}': {e}"
            )
        finally:
            # Cerrar conexiones con los clientes InfluxDB
            SOURCE_CLIENT.close()
            DEST_CLIENT.close()
    else:
        logger.error(
            "Abortando proceso de copia de datos debido a problemas de conexión."
        )
