import configparser
import csv
import os
import shutil
import time
import zipfile
from datetime import date, datetime, timedelta

import psycopg2

# --- Configuración del Periodo de Extracción ---
# Define aquí el rango de fechas para la extracción.
# Si START_DATE_STR y END_DATE_STR son None, se extraerán todos los datos de las tablas con columna de fecha.
# Para tablas sin columna de fecha, siempre se extraerá todo y se paginará si es necesario.
START_DATE_STR = "2025-06-05"  # Formato YYYY-MM-DD, ej: "2023-01-01"
END_DATE_STR = "2025-06-07"  # Formato YYYY-MM-DD, ej: "2023-01-31"

# --- Constantes Adicionales ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE_DIR = os.path.join(
    SCRIPT_DIR, "backup_data"
)  # Directorio base temporal para los CSVs
FINAL_ZIP_DIR = os.path.join(
    SCRIPT_DIR, "final_backups"
)  # Directorio donde se guardarán los ZIPs finales
DATE_COLUMN_NAME = "date_hour"
MAX_ROWS_PER_CSV = 100000  # Para tablas sin columna de fecha identificable o para paginación general
MAX_ROWS_PER_DAY_QUERY = (
    10000  # Máximo de filas por consulta diaria (para paginación)
)
PAUSE_BETWEEN_QUERIES = (
    2  # Segundos de pausa entre consultas para evitar saturar el servidor
)
PAUSE_BETWEEN_DAYS = 5  # Segundos de pausa entre días
DB_SCHEMA = "public"  # Esquema de la base de datos a respaldar


def get_db_connection(config):
    """Establece y devuelve una conexión a la base de datos PostgreSQL."""
    connection_params = {
        "host": config["postgresql"]["db_host"],
        "port": config["postgresql"]["db_port"],
        "dbname": config["postgresql"]["db_name"],
        "user": config["postgresql"]["db_user"],
        "password": config["postgresql"]["db_password"],
    }

    print(f"Intentando conectar con:")
    print(f"  Host: {connection_params['host']}")
    print(f"  Puerto: {connection_params['port']}")
    print(f"  Base de datos: {connection_params['dbname']}")
    print(f"  Usuario: {connection_params['user']}")

    # Intentar primero sin especificar SSL
    try:
        print("Intento 1: Conexión sin especificar SSL...")
        conn = psycopg2.connect(**connection_params)
        print("✓ Conexión exitosa!")
        return conn
    except psycopg2.Error as e:
        print(f"✗ Falló intento 1:")
        print(f"  Código de error PG: {e.pgcode}")
        print(f"  Mensaje de error PG: {e.pgerror}")
        print(f"  Error detallado: {e}")

    # Intentar con SSL deshabilitado
    try:
        print("Intento 2: Conexión con SSL deshabilitado...")
        connection_params["sslmode"] = "disable"
        conn = psycopg2.connect(**connection_params)
        print("✓ Conexión exitosa con SSL deshabilitado!")
        return conn
    except psycopg2.Error as e:
        print(f"✗ Falló intento 2:")
        print(f"  Código de error PG: {e.pgcode}")
        print(f"  Mensaje de error PG: {e.pgerror}")
        print(f"  Error detallado: {e}")

    # Intentar con SSL requerido
    try:
        print("Intento 3: Conexión con SSL requerido...")
        connection_params["sslmode"] = "require"
        conn = psycopg2.connect(**connection_params)
        print("✓ Conexión exitosa con SSL requerido!")
        return conn
    except psycopg2.Error as e:
        print(f"✗ Falló intento 3:")
        print(f"  Código de error PG: {e.pgcode}")
        print(f"  Mensaje de error PG: {e.pgerror}")
        print(f"  Error detallado: {e}")

    print("✗ Todos los intentos de conexión fallaron.")
    return None


def get_tables(conn, schema):
    """Obtiene la lista de tablas de un esquema específico."""
    tables = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tablename
                FROM pg_catalog.pg_tables
                WHERE schemaname = %s;
            """,
                (schema,),
            )
            tables = [row[0] for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Error al obtener la lista de tablas: {e}")
    return tables


def parse_dates():
    """Parsea las fechas de inicio y fin desde las constantes."""
    start_date = None
    end_date = None
    if START_DATE_STR:
        try:
            start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d").date()
        except ValueError:
            print(
                f"Formato de START_DATE_STR ('{START_DATE_STR}') inválido. Debe ser YYYY-MM-DD."
            )
            return None, None
    if END_DATE_STR:
        try:
            end_date = datetime.strptime(END_DATE_STR, "%Y-%m-%d").date()
        except ValueError:
            print(
                f"Formato de END_DATE_STR ('{END_DATE_STR}') inválido. Debe ser YYYY-MM-DD."
            )
            return None, None

    if start_date and end_date and start_date > end_date:
        print("START_DATE no puede ser posterior a END_DATE.")
        return None, None

    return start_date, end_date


def get_table_columns(conn, table_name, schema):
    """Obtiene los nombres de las columnas de una tabla."""
    columns = []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position;
            """,
                (schema, table_name),
            )
            columns = [row[0] for row in cur.fetchall()]
    except psycopg2.Error as e:
        print(f"Error al obtener columnas para la tabla {table_name}: {e}")
    return columns


def extract_day_data_paginated(
    conn, table_name, columns, schema, target_date, csv_file_path
):
    """
    Extrae datos de un día específico usando paginación para evitar sobrecargar el servidor.
    Retorna el número total de filas extraídas.
    """
    total_rows = 0
    offset = 0

    # Verificar si ya existe el archivo y abrirlo en modo append o crear nuevo
    file_mode = "a" if os.path.exists(csv_file_path) else "w"
    write_headers = file_mode == "w"

    try:
        with open(
            csv_file_path, file_mode, newline="", encoding="utf-8"
        ) as csvfile:
            writer = csv.writer(csvfile)

            if write_headers:
                writer.writerow(
                    columns
                )  # Escribir cabeceras solo si es un archivo nuevo

            while True:
                try:
                    # Intentar reconectar si la conexión está cerrada
                    if conn.closed:
                        print(f"    Conexión cerrada, intentando reconectar...")
                        # Esta función debería manejar la reconexión, pero por simplicidad
                        # retornamos el total hasta ahora
                        break

                    with conn.cursor() as cur:
                        # Query paginada para el día específico
                        query = f"""
                            SELECT * FROM "{schema}"."{table_name}"
                            WHERE DATE("{DATE_COLUMN_NAME}") = %s
                            ORDER BY "{DATE_COLUMN_NAME}"
                            LIMIT %s OFFSET %s;
                        """

                        print(
                            f"    Consultando offset {offset}, límite {MAX_ROWS_PER_DAY_QUERY}..."
                        )
                        cur.execute(
                            query, (target_date, MAX_ROWS_PER_DAY_QUERY, offset)
                        )

                        rows_in_batch = 0
                        for row in cur:
                            writer.writerow(row)
                            rows_in_batch += 1
                            total_rows += 1

                        print(
                            f"    Batch completado: {rows_in_batch} filas (total acumulado: {total_rows})"
                        )

                        # Si obtuvimos menos filas que el límite, hemos terminado
                        if rows_in_batch < MAX_ROWS_PER_DAY_QUERY:
                            print(f"    Extracción completa para {target_date}")
                            break

                        offset += MAX_ROWS_PER_DAY_QUERY

                        # Pausa entre consultas para no saturar el servidor
                        if PAUSE_BETWEEN_QUERIES > 0:
                            print(
                                f"    Pausando {PAUSE_BETWEEN_QUERIES} segundos..."
                            )
                            time.sleep(PAUSE_BETWEEN_QUERIES)

                except psycopg2.Error as e_query:
                    print(
                        f"    Error en consulta paginada (offset {offset}): {e_query}"
                    )
                    if "connection" in str(e_query).lower():
                        print(
                            f"    Error de conexión detectado, terminando extracción para este día"
                        )
                        break
                    else:
                        # Para otros errores, intentar continuar con el siguiente batch
                        offset += MAX_ROWS_PER_DAY_QUERY
                        continue

    except IOError as e_io:
        print(f"    Error al escribir CSV: {e_io}")

    return total_rows


def reconnect_db(config, max_retries=3):
    """Intenta reconectar a la base de datos con reintentos."""
    for retry in range(max_retries):
        print(f"  Intento de reconexión {retry + 1}/{max_retries}...")
        conn = get_db_connection(config)
        if conn:
            print("  ✓ Reconexión exitosa!")
            return conn
        if retry < max_retries - 1:
            print(f"  Esperando 5 segundos antes del siguiente intento...")
            time.sleep(5)
    print("  ✗ No se pudo reconectar después de todos los intentos")
    return None


def main():
    print("Iniciando proceso de backup...")

    # Crear directorios de salida si no existen
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    os.makedirs(FINAL_ZIP_DIR, exist_ok=True)

    config = configparser.ConfigParser()
    config_path = "config.ini"
    if not os.path.exists(config_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(script_dir, "config.ini")
        if not os.path.exists(config_path):
            print(
                f"Error: No se encuentra el archivo de configuración config.ini."
            )
            return

    config.read(config_path)

    db_name = config["postgresql"]["db_name"]

    start_date, end_date = parse_dates()
    if START_DATE_STR and start_date is None:
        return
    if END_DATE_STR and end_date is None:
        return

    conn = get_db_connection(config)
    if not conn:
        return

    tables = get_tables(conn, DB_SCHEMA)
    if not tables:
        print(f"No se encontraron tablas en el esquema '{DB_SCHEMA}'.")
        conn.close()
        return

    print(f"Tablas encontradas en el esquema '{DB_SCHEMA}': {tables}")

    processed_zip_filename = (
        None  # Para almacenar el nombre del archivo ZIP final
    )

    # Determinar el rango de fechas para el nombre del archivo ZIP
    zip_date_str = "all_data"
    if start_date and end_date:
        zip_date_str = (
            f"{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}"
        )
    elif start_date:
        zip_date_str = f"from_{start_date.strftime('%Y%m%d')}"
    elif end_date:
        zip_date_str = f"up_to_{end_date.strftime('%Y%m%d')}"

    # Limpiar el directorio base de salida antes de empezar (si existe de una ejecución anterior)
    if os.path.exists(OUTPUT_BASE_DIR):
        shutil.rmtree(OUTPUT_BASE_DIR)
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)

    for table_name in tables:
        print(f"Procesando tabla: {table_name}...")
        columns = get_table_columns(conn, table_name, DB_SCHEMA)
        if not columns:
            print(
                f"No se pudieron obtener columnas para la tabla {table_name}, saltando."
            )
            continue

        if DATE_COLUMN_NAME in columns:
            # Procesar tabla con columna de fecha
            print(
                f"La tabla {table_name} tiene la columna de fecha '{DATE_COLUMN_NAME}'. Extrayendo por día."
            )

            current_s_date = start_date
            current_e_date = end_date

            # Si no hay fechas definidas, necesitamos encontrar el min y max de la tabla
            if current_s_date is None or current_e_date is None:
                try:
                    with conn.cursor() as cur_min_max:
                        # Asegurarse de que la columna de fecha sea de un tipo adecuado para MIN/MAX
                        # Esto es una simplificación, la conversión de tipo puede ser necesaria si DATE_COLUMN_NAME no es directamente comparable.
                        cur_min_max.execute(
                            f'SELECT MIN("{DATE_COLUMN_NAME}"), MAX("{DATE_COLUMN_NAME}") FROM "{DB_SCHEMA}"."{table_name}";'
                        )
                        res = cur_min_max.fetchone()
                        if res and res[0] is not None and res[1] is not None:
                            table_min_date = res[0]
                            table_max_date = res[1]
                            # Convertir a objeto date si son datetime
                            if isinstance(table_min_date, datetime):
                                table_min_date = table_min_date.date()
                            if isinstance(table_max_date, datetime):
                                table_max_date = table_max_date.date()

                            if current_s_date is None:
                                current_s_date = table_min_date
                            if current_e_date is None:
                                current_e_date = table_max_date
                            print(
                                f"Rango de fechas para la tabla {table_name} (o global): {current_s_date} a {current_e_date}"
                            )
                        else:
                            print(
                                f"No se pudo determinar el rango de fechas para la tabla {table_name} a partir de la columna '{DATE_COLUMN_NAME}'. Se exportará completa sin división por fecha."
                            )
                            # Tratar como tabla sin columna de fecha (o manejar error)
                            export_table_paginated(
                                conn, table_name, columns, DB_SCHEMA
                            )
                            continue
                except psycopg2.Error as e_min_max:
                    print(
                        f"Error al obtener min/max fecha para {table_name}: {e_min_max}. Se exportará completa sin división por fecha."
                    )
                    export_table_paginated(conn, table_name, columns, DB_SCHEMA)
                    continue

            if (
                not current_s_date or not current_e_date
            ):  # Si aún no tenemos fechas (tabla vacía o error anterior)
                print(
                    f"No hay rango de fechas válido para {table_name}. Se exportará completa sin división por fecha."
                )
                export_table_paginated(conn, table_name, columns, DB_SCHEMA)
                continue

            loop_date = current_s_date
            while loop_date <= current_e_date:
                year_str = loop_date.strftime("%Y")
                month_str = loop_date.strftime("%m")
                day_str = loop_date.strftime("%d")

                output_dir_for_day = os.path.join(
                    OUTPUT_BASE_DIR, year_str, month_str, day_str
                )
                os.makedirs(output_dir_for_day, exist_ok=True)

                csv_file_path = os.path.join(
                    output_dir_for_day, f"{table_name}.csv"
                )

                print(f"  Procesando {loop_date.strftime('%Y-%m-%d')}...")

                # Verificar si la conexión sigue activa
                if conn.closed:
                    print(f"  Conexión perdida, intentando reconectar...")
                    conn = reconnect_db(config)
                    if not conn:
                        print(
                            f"  ✗ No se pudo reconectar, saltando día {loop_date.strftime('%Y-%m-%d')}"
                        )
                        loop_date += timedelta(days=1)
                        continue

                # Usar la nueva función paginada para extraer datos del día
                rows_written_for_day = extract_day_data_paginated(
                    conn,
                    table_name,
                    columns,
                    DB_SCHEMA,
                    loop_date,
                    csv_file_path,
                )

                if rows_written_for_day > 0:
                    print(
                        f"  ✓ Datos de {table_name} para {loop_date.strftime('%Y-%m-%d')} guardados en {csv_file_path} ({rows_written_for_day} filas)"
                    )
                else:
                    print(
                        f"  - No se encontraron datos para {table_name} el {loop_date.strftime('%Y-%m-%d')}"
                    )
                    # Opcionalmente eliminar el archivo CSV vacío
                    if (
                        os.path.exists(csv_file_path)
                        and os.path.getsize(csv_file_path)
                        <= len(",".join(columns)) + 2
                    ):
                        os.remove(csv_file_path)

                # Pausa entre días para no saturar el servidor
                if PAUSE_BETWEEN_DAYS > 0 and loop_date < current_e_date:
                    print(
                        f"  Pausando {PAUSE_BETWEEN_DAYS} segundos antes del siguiente día..."
                    )
                    time.sleep(PAUSE_BETWEEN_DAYS)

                loop_date += timedelta(days=1)
        else:
            # Procesar tabla sin columna de fecha (o si no se pudo usar)
            print(
                f"La tabla {table_name} no tiene la columna de fecha '{DATE_COLUMN_NAME}' o no se pudo usar. Exportando completa y paginando si es necesario."
            )
            export_table_paginated(conn, table_name, columns, DB_SCHEMA)

    # Comprimir los datos
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Asegurarse de que FINAL_ZIP_DIR existe
    os.makedirs(FINAL_ZIP_DIR, exist_ok=True)

    zip_filename_base = (
        f"postgres_backup_{db_name}_{zip_date_str}_{timestamp_str}.zip"
    )
    zip_filepath = os.path.join(FINAL_ZIP_DIR, zip_filename_base)

    try:
        if not os.listdir(OUTPUT_BASE_DIR):
            print("No se generaron archivos CSV, no se creará el archivo ZIP.")
        else:
            with zipfile.ZipFile(zip_filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(OUTPUT_BASE_DIR):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # El arco en el zip será relativo a OUTPUT_BASE_DIR
                        arcname = os.path.relpath(file_path, OUTPUT_BASE_DIR)
                        zf.write(file_path, arcname)
            print(f"Directorio {OUTPUT_BASE_DIR} comprimido en {zip_filepath}")
            processed_zip_filename = zip_filepath
            # Limpieza del directorio temporal de trabajo después de comprimir
            shutil.rmtree(OUTPUT_BASE_DIR)
            print(f"Directorio temporal {OUTPUT_BASE_DIR} eliminado.")

    except Exception as e_zip:
        print(f"Error al crear el archivo ZIP: {e_zip}")

    if conn:
        conn.close()

    if processed_zip_filename:
        print(
            f"Proceso de backup completado. Archivo ZIP generado: {processed_zip_filename}"
        )
    else:
        print(
            "Proceso de backup completado, pero no se generó ningún archivo ZIP (ver logs)."
        )


def export_table_paginated(conn, table_name, columns, schema):
    """Exporta una tabla completa, paginando los resultados si exceden MAX_ROWS_PER_CSV."""
    output_dir_for_table = os.path.join(OUTPUT_BASE_DIR, table_name)
    os.makedirs(output_dir_for_table, exist_ok=True)

    try:
        with conn.cursor(
            name="large_table_cursor"
        ) as cur:  # Usar cursor nombrado para grandes resultados
            cur.itersize = MAX_ROWS_PER_CSV  # Ajustar según memoria / necesidad

            query = f'SELECT * FROM "{schema}"."{table_name}";'
            cur.execute(query)

            file_part = 0
            rows_in_current_file = 0
            csv_file_path = None
            writer = None
            csvfile_handle = None

            for row_idx, row in enumerate(cur):
                if (
                    rows_in_current_file == 0
                ):  # Inicio de un nuevo archivo (o el primero)
                    file_part += 1
                    csv_file_path = os.path.join(
                        output_dir_for_table,
                        f"{table_name}_part_{file_part}.csv",
                    )
                    print(f"  Escribiendo en {csv_file_path}...")
                    csvfile_handle = open(
                        csv_file_path, "w", newline="", encoding="utf-8"
                    )
                    writer = csv.writer(csvfile_handle)
                    writer.writerow(columns)  # Escribir cabeceras

                writer.writerow(row)
                rows_in_current_file += 1

                if rows_in_current_file >= MAX_ROWS_PER_CSV:
                    csvfile_handle.close()
                    print(
                        f"  Archivo {csv_file_path} completado con {rows_in_current_file} filas."
                    )
                    rows_in_current_file = 0  # Reset para el próximo archivo

            if csvfile_handle and not csvfile_handle.closed:
                csvfile_handle.close()
                if (
                    rows_in_current_file > 0
                ):  # Si hubo filas en el último archivo
                    print(
                        f"  Archivo {csv_file_path} completado con {rows_in_current_file} filas."
                    )
                else:  # Si el último archivo se creó pero no tuvo filas (ej. tabla vacía procesada aquí)
                    os.remove(csv_file_path)
                    print(f"  Archivo {csv_file_path} vacío eliminado.")

    except psycopg2.Error as e_query:
        print(f"Error al extraer datos paginados para {table_name}: {e_query}")
    except IOError as e_io:
        print(f"Error al escribir CSV paginado para {table_name}: {e_io}")


if __name__ == "__main__":
    main()
