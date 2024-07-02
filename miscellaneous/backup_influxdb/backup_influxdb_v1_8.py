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
from typing import Any, Dict, List, Literal, Optional, Union

from dateutil.parser import parse
from dotenv import load_dotenv
from influxdb import InfluxDBClient
from influxdb.resultset import ResultSet

# Cargar variables de entorno
load_dotenv()

# Constantes
SOURCE_URL = os.getenv("SOURCE_URL")
SOURCE_DBS = os.getenv("SOURCE_DBS").split(",") if os.getenv("SOURCE_DBS") else []
SOURCE_GROUP_BY = os.getenv("SOURCE_GROUP_BY", "5m")
DEST_URL = os.getenv("DEST_URL")
DEST_DBS = os.getenv("DEST_DBS").split(",") if os.getenv("DEST_DBS") else []
DAYS_OF_PAGINATION = (
    int(os.getenv("DAYS_OF_PAGINATION")) if os.getenv("DAYS_OF_PAGINATION") else 7
)

PATH_LOG_FILE = os.getenv("LOG_FILE")

TIMEOUT_CLIENT = int(os.getenv("TIMEOUT_CLIENT")) if os.getenv("TIMEOUT_CLIENT") else 20

logging.basicConfig(
    filename=PATH_LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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
    timeout=TIMEOUT_CLIENT,
)
DEST_CLIENT = InfluxDBClient(
    host=DEST_URL.split(":")[1].replace("//", ""),
    port=int(
        DEST_URL.split(":")[2],
    ),
    username=os.getenv("DEST_USER"),
    password=os.getenv("DEST_PASSWORD"),
    timeout=TIMEOUT_CLIENT,
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


def filter_non_numeric_values(
    _point: Dict[str, Any], float_selector: bool
) -> Dict[str, Union[int, float]]:
    """
    Filtra los campos de un punto de datos dejando solo aquellos que son números (int o float)
    y que no son de tipo "time". Si float_selector es True, se filtran solo los campos de tipo float.
    Si float_selector es False, se filtran solo los campos de tipo str o bool.

    :param _point: El punto de datos a filtrar.
    :type _point: Dict[str, Any]
    :param float_selector: Si es True, se filtrarán solo los campos de tipo float.
                           Si es False, se filtrarán solo los campos de tipo str o bool.
    :type float_selector: bool
    :return: Un nuevo diccionario con los campos filtrados.
    :rtype: Dict[str, Union[int, float]]
    """
    filtered_fields = {}
    if float_selector:
        for key, value in _point.items():
            if value is not None and key != "time" and isinstance(value, (int, float)):
                filtered_fields[key.replace("last_", "").replace("mean_", "")] = value
    else:
        for key, value in _point.items():
            if value is not None and key != "time" and isinstance(value, (str, bool)):
                filtered_fields[key.replace("last_", "").replace("mean_", "")] = value
    return filtered_fields


def combine_records_by_time(
    points_float: List[Dict[str, Any]], points_no_float: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Combina registros de dos listas de puntos en una lista de puntos,
    combinando los campos de las dos listas en función de la marca de tiempo.

    :param points_float: La lista de puntos con campos de tipo float.
    :type points_float: List[Dict[str, Any]]
    :param points_no_float: La lista de puntos con campos de tipo no float.
    :type points_no_float: List[Dict[str, Any]]
    :return: La lista combinada de puntos.
    :rtype: List[Dict[str, Any]]
    """
    combined_points = []

    # Convertir las listas a diccionarios indexados por 'time'
    float_dict = {record["time"]: record for record in points_float}
    no_float_dict = {record["time"]: record for record in points_no_float}

    for time, float_record in float_dict.items():
        if time in no_float_dict:
            combined_fields = {
                **float_record["fields"],
                **no_float_dict[time]["fields"],
            }
        else:
            combined_fields = float_record["fields"]

        combined_record = {
            "time": time,
            "measurement": float_record["measurement"],
            "fields": combined_fields,
        }
        combined_points.append(combined_record)

    return combined_points


def build_list_points(
    result: ResultSet, measurement: str, float_selector: bool
) -> List[Dict[str, Any]]:
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
            # Crear lista de puntos, donde se seleccionar o valores numericos o valores bool/str
            point = {
                "time": _point["time"],
                "measurement": measurement,
                "fields": filter_non_numeric_values(_point, float_selector),
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
    query_float = f"SELECT MEAN(*) FROM {measurement} {section_last_entry_time} GROUP BY time({group_by})"
    query_no_float = f"SELECT LAST(*) FROM {measurement} {section_last_entry_time} GROUP BY time({group_by})"
    try:
        logger.info(
            f"\tIniciando copia de seguridad para el measurement '{measurement}'."
        )
        # Ejecutar query
        result_float = source_client.query(query_float)
        result_no_float = source_client.query(query_no_float)
        # Obtener lista de puntos
        points_float = build_list_points(result_float, measurement, True)
        points_no_float = build_list_points(result_no_float, measurement, False)

        # Combinar puntos tantos numericos como no numericos
        points = combine_records_by_time(points_float, points_no_float)

        # Comprobar si la lista no es nula. Si es cierto, registrar los datos en el servidor de destino
        if points:
            dest_client.write_points(points, batch_size=5000)
            if last_entry_time:
                txt_interval_time = f"la marca de tiempo {last_entry_time}"
            else:
                txt_interval_time = "el inicio de la base de datos"
            logger.info(
                f"\tDatos del measurement '{measurement}' copiados exitosamente desde {txt_interval_time} (puntos registrados: {len(points)})."
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
    """
    Copia los datos de un measurement de una base de datos de InfluxDB a otra, utilizando una paginación
    de un mes hacia atrás.

    :param source_client: El cliente de InfluxDB de la base de datos de origen.
    :type source_client: InfluxDBClient
    :param dest_client: El cliente de InfluxDB de la base de datos de destino.
    :type dest_client: InfluxDBClient
    :param first_entry_time: La marca de tiempo del primer registro a copiar (opcional).
    :type first_entry_time: str
    :param measurement: El nombre del measurement a copiar.
    :type measurement: str
    :param group_by: El valor de agrupación de tiempo.
    :type group_by: str
    :return: Ninguno.
    :rtype: None
    """
    str_format_datetime_query = "%Y-%m-%dT%H:%M:%SZ"
    str_format_datetime_log = "%Y-%m-%dT%H:%M:%SZ"
    days_timedelta = DAYS_OF_PAGINATION
    try:
        # Fecha de inicio (hacia atras)
        start_date = datetime.now(timezone.utc)
        # Fecha de fin (hacia atras)
        end_date = start_date - timedelta(days=days_timedelta)

        # Transformar fecha del primer registro y crear la expresión de paginacion
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
            query_float = (
                f"SELECT MEAN(*) FROM {measurement} "
                f"WHERE time >= '{end_date.strftime(str_format_datetime_query)}' AND time < '{start_date.strftime(str_format_datetime_query)}' "
                f"GROUP BY time({group_by})"
            )
            query_no_float = (
                f"SELECT LAST(*) FROM {measurement} "
                f"WHERE time >= '{end_date.strftime(str_format_datetime_query)}' AND time < '{start_date.strftime(str_format_datetime_query)}' "
                f"GROUP BY time({group_by})"
            )
            logger.info(
                f"\t\tCopia de seguridad para el measurement '{measurement}' para el periodo {end_date.strftime(str_format_datetime_log)} a {start_date.strftime(str_format_datetime_log)}."
            )

            # Ejecutar query
            result_float = source_client.query(query_float)
            result_no_float = source_client.query(query_no_float)
            # Obtener lista de puntos
            points_float = build_list_points(result_float, measurement, True)
            points_no_float = build_list_points(result_no_float, measurement, False)

            # Combinar puntos tantos numericos como no numericos
            points = combine_records_by_time(points_float, points_no_float)
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
        logger.info(
            f"Parametros del proceso: group by = {SOURCE_GROUP_BY} | days of pagination = {DAYS_OF_PAGINATION} | timeout = {int(os.getenv('TIMEOUT_CLIENT'))}"
        )
        try:
            # Si la longitud de SOURCE_DBS esta vacia, es que se desea copiar todas las bases de datos
            if len(SOURCE_DBS) == 0:
                SOURCE_DBS = [k.get("name") for k in SOURCE_CLIENT.get_list_database()]
                # Eliminar la base de dato _internal
                if "_internal" in SOURCE_DBS:
                    SOURCE_DBS.remove("_internal")
                # Replicar bases de datos destino
                DEST_DBS = SOURCE_DBS
            # Recorrer cada base de datow
            for source_db, dest_db in zip(SOURCE_DBS, DEST_DBS):
                # Apuntar a la base de datos correspondiente
                SOURCE_CLIENT.switch_database(source_db)
                # Recorrer cada measurement
                for measurement in SOURCE_CLIENT.get_list_measurements():
                    if measurement["name"] == "StorageSystem":
                        pass
                    logger.info(
                        f"Iniciando copia de datos de '{SOURCE_CLIENT._host}:{SOURCE_CLIENT._port}/{source_db}' a '{DEST_CLIENT._host}:{DEST_CLIENT._port}/{dest_db}'."
                    )
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
                        # Obtener la marca de tiempo del primer registro
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
            logger.info("Conexiones clientes InfluxDB cerradas.\n")
    else:
        logger.error(
            "Abortando proceso de copia de datos debido a problemas de conexión.\n"
        )
