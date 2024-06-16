"""
Script para realizar copias de seguridad de una o varias bases de datos
de un servidor a otro.
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from influxdb import InfluxDBClient

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
)
DEST_CLIENT = InfluxDBClient(
    host=DEST_URL.split(":")[1].replace("//", ""),
    port=int(
        DEST_URL.split(":")[2],
    ),
    username=os.getenv("DEST_USER"),
    password=os.getenv("DEST_PASSWORD"),
)


def check_connection(client: InfluxDBClient, name: str) -> bool:
    """
    Verifica si la conexión al cliente dado es exitosa.

    :param client: El cliente para verificar la conexión.
    :type client: :class:`InfluxDBClient`
    :param name: El nombre del cliente para propósitos de registro.
    :type name: str
    :return: True si la conexión es exitosa, False en caso contrario.
    :rtype: bool
    """
    try:
        client.ping()
        logger.info(f"Conexión exitosa a {name}")
        return True
    except Exception as e:
        logger.error(f"Conexión fallida a {name}: {str(e)}")
        return False


def get_last_entry_time(client: InfluxDBClient, measurement: str) -> Optional[str]:
    """
    Obtiene la marca de tiempo del último registro en la medición dada.
    :param client: El cliente para consultar la base de datos.
    :type client: :class:`InfluxDBClient`
    :param measurement: El nombre de la medición.
    :type measurement: str
    :return: La marca de tiempo del último registro en la medición,
    o None si no se encuentra ningún registro.
    :rtype: Optional[str]
    """
    query = f"SELECT * FROM {measurement} ORDER BY time DESC LIMIT 1"
    try:
        result = client.query(query)
        if result:
            points = list(result.get_points())
            if points:
                return points[0]["time"]
        return None
    except Exception as e:
        logger.error(
            f"\tError al obtener el último registro del measurement {measurement}: {str(e)}"
        )
        return None


def copy_data_since_last_entry(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    last_entry_time: str,
    measurement: str,
    group_by: str,
) -> None:
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
        result = source_client.query(query)
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
        if points:
            dest_client.write_points(points, batch_size=5000)
            logger.info(f"\tSe han copiado los datos de {measurement} exitosamente.")
    except Exception as e:
        logger.error(
            f"\tError al copiar los datos del measurement {measurement}: {str(e)}"
        )


if __name__ == "__main__":
    # Verificar la conexión de cada cliente
    if check_connection(SOURCE_CLIENT, "Source URL") and check_connection(
        DEST_CLIENT, "Destination URL"
    ):
        # Recorrer cada base de datos
        for source_db, dest_db in zip(SOURCE_DBS, DEST_DBS):
            # Apuntar a la base de datos correspondiente
            SOURCE_CLIENT.switch_database(source_db)
            logger.info(f"Iniciando copia de datos de {source_db} a {dest_db}.")
            # Recorrer cada measurement
            for measurement in SOURCE_CLIENT.get_list_measurements():
                # Crear la base de datos si no existe y apuntar a la base de datos correspondiente
                DEST_CLIENT.create_database(dest_db)
                DEST_CLIENT.switch_database(dest_db)
                # Obtener el último registro del measurement de destino para saber desde donde se
                # debe copiar los datos
                last_entry_time = get_last_entry_time(DEST_CLIENT, measurement["name"])
                # Copiar datos desde el último registro
                copy_data_since_last_entry(
                    SOURCE_CLIENT,
                    DEST_CLIENT,
                    last_entry_time,
                    measurement["name"],
                    SOURCE_GROUP_BY,
                )
    else:
        logger.error(
            "Abortando proceso de copia de datos debido a problemas de conexión."
        )
