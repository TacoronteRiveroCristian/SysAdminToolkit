import logging
import time
from datetime import datetime, timedelta, timezone

from .config import Config
from .influx_client import InfluxClient

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Gestiona el proceso de backup entre dos instancias de InfluxDB.
    """

    def __init__(
        self,
        config: Config,
        source_client: InfluxClient,
        dest_client: InfluxClient,
    ):
        self.config = config
        self.source_client = source_client
        self.dest_client = dest_client
        self.retries = self.config.get("options.retries", 3)
        self.retry_delay = self.config.get("options.retry_delay", 5)

    def _execute_with_retry(self, func, *args, **kwargs):
        """Ejecuta una función con una política de reintentos."""
        for attempt in range(self.retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Reintentar solo para errores de conexión/red, no para errores de lógica de InfluxDB
                if isinstance(
                    e,
                    (
                        ConnectionError,
                        # InfluxDBClientError puede ser muy genérico, pero lo incluimos
                        # importando la excepción específica si fuera necesario
                        self.source_client.client.exceptions.InfluxDBClientError,
                    ),
                ):
                    if attempt < self.retries:
                        logger.warning(
                            f"La operación falló por un error de red: {e}. Reintentando en {self.retry_delay}s... (Intento {attempt + 1}/{self.retries})"
                        )
                        time.sleep(self.retry_delay)
                    else:
                        logger.error(
                            f"La operación falló después de {self.retries} reintentos."
                        )
                        raise e  # Lanza la excepción final si todos los reintentos fallan
                else:
                    # Si no es un error de red, no reintentar (ej. consulta mal formada)
                    logger.error(
                        f"La operación falló por un error no recuperable: {e}"
                    )
                    raise e
        return None  # No debería alcanzarse, pero es para que el linter esté contento

    def _get_fields_to_backup(self, source_db, measurement):
        """
        Calcula la lista final de campos a respaldar para una medición,
        basado en la configuración (include, exclude, types).
        """
        specific_config = self.config.get(
            f"measurements.specific.{measurement}", {}
        )
        all_fields = self.source_client.get_field_keys(source_db, measurement)

        fields_config = (
            specific_config.get("fields", {}) if specific_config else {}
        )
        types_to_include = fields_config.get(
            "types", ["numeric", "string", "boolean"]
        )
        valid_influx_types = {"float", "integer", "string", "boolean"}
        fields_by_type = []
        for f, t in all_fields.items():
            normalized_type = t.replace("integer", "numeric").replace(
                "float", "numeric"
            )
            if t in valid_influx_types and normalized_type in types_to_include:
                fields_by_type.append(f)

        fields_include = fields_config.get("include", [])
        fields_exclude = fields_config.get("exclude", [])

        if fields_include:
            final_fields = [f for f in fields_by_type if f in fields_include]
        else:
            final_fields = [
                f for f in fields_by_type if f not in fields_exclude
            ]

        return final_fields

    def run_backup(self):
        """Punto de entrada principal para ejecutar el backup según el modo configurado."""
        mode = self.config.get("options.backup_mode")
        logger.info(f"Iniciando backup en modo: {mode}")

        if mode == "range":
            self._run_range_backup()
        elif mode == "incremental":
            self._run_incremental_backup()
        else:
            logger.error(f"Modo de backup desconocido: {mode}")

    def _run_range_backup(self):
        """Ejecuta un backup para un rango de fechas específico."""
        start_date_str = self.config.get("options.range.start_date")
        end_date_str = self.config.get("options.range.end_date")

        if not start_date_str or not end_date_str:
            logger.error(
                "Para el modo 'range', se requieren 'start_date' y 'end_date'."
            )
            return

        logger.info(
            f"Backup de rango desde {start_date_str} hasta {end_date_str}"
        )
        self._process_databases(start_date_str, end_date_str)
        logger.info("Backup de rango completado.")

    def _run_incremental_backup(self):
        """Ejecuta un backup incremental."""
        logger.info("Iniciando backup incremental.")
        self._process_databases()
        logger.info("Backup incremental completado.")

    def _process_databases(self, start_time=None, end_time=None):
        """Itera sobre las BBDD configuradas y procesa sus mediciones."""
        databases = self.config.get("source.databases", [])
        for db_map in databases:
            source_db = db_map["name"]
            dest_db = db_map["destination"]
            logger.info(f"Procesando backup de '{source_db}' -> '{dest_db}'")

            # Asegurarse de que la base de datos de destino exista
            try:
                self.dest_client.create_database(dest_db)
            except Exception as e:
                logger.error(
                    f"No se pudo crear/verificar la DB de destino '{dest_db}'. Saltando... Error: {e}"
                )
                continue

            measurements = self._get_filtered_measurements(source_db)
            for measurement in measurements:
                self._process_measurement(
                    source_db, dest_db, measurement, start_time, end_time
                )

    def _get_filtered_measurements(self, source_db):
        """Obtiene la lista de mediciones a respaldar, aplicando filtros."""
        all_measurements = self.source_client.get_measurements(source_db)
        include_list = self.config.get("measurements.include", [])
        exclude_list = self.config.get("measurements.exclude", [])

        if include_list:
            filtered = [m for m in all_measurements if m in include_list]
            logger.debug(
                f"Mediciones a incluir (de {len(all_measurements)}): {filtered}"
            )
            return filtered

        if exclude_list:
            filtered = [m for m in all_measurements if m not in exclude_list]
            logger.debug(
                f"Mediciones a excluir (de {len(all_measurements)}): {filtered}"
            )
            return filtered

        logger.debug(
            f"Sin filtros globales, se procesarán todas las {len(all_measurements)} mediciones."
        )
        return all_measurements

    def _process_measurement(
        self, source_db, dest_db, measurement, start_time, end_time
    ):
        """Procesa una única medición, copiando los datos."""
        logger.info(f"Procesando medición: '{measurement}'")

        fields_to_backup = self._get_fields_to_backup(source_db, measurement)
        if not fields_to_backup:
            logger.warning(
                f"No hay campos que respaldar para '{measurement}' después de aplicar filtros de configuración. Saltando."
            )
            return

        logger.debug(
            f"Campos de interés para este backup de '{measurement}': {fields_to_backup}"
        )

        # Para modo incremental, determinar el rango de tiempo
        if self.config.get("options.backup_mode") == "incremental":
            logger.info(
                f"Modo incremental: Buscando el último timestamp en destino '{dest_db}' para los campos: {fields_to_backup}"
            )
            last_timestamp_str = self.dest_client.get_last_timestamp(
                dest_db, measurement, fields=fields_to_backup
            )

            if last_timestamp_str:
                logger.info(
                    f"Último timestamp encontrado en destino: {last_timestamp_str}. Se continuará desde este punto."
                )
                # Comprobar si la medición está obsoleta
                obsolete_threshold = self.config.get(
                    "incremental.obsolete_threshold"
                )
                if obsolete_threshold:
                    if self._is_obsolete(
                        last_timestamp_str, obsolete_threshold
                    ):
                        logger.info(
                            f"La medición '{measurement}' está obsoleta para los campos de interés. Saltando..."
                        )
                        return
                start_time = last_timestamp_str
            else:
                logger.info(
                    f"No se encontró ningún timestamp en destino para los campos de interés. Se buscará el primer dato en el origen '{source_db}'."
                )
                first_timestamp_str = self.source_client.get_first_timestamp(
                    source_db, measurement, fields=fields_to_backup
                )

                if not first_timestamp_str:
                    logger.info(
                        f"No se han encontrado datos para los campos de '{measurement}' en el origen. Saltando medición."
                    )
                    return

                logger.info(
                    f"El registro más antiguo en origen para los campos de interés es de {first_timestamp_str}. Se iniciará el backup desde ese punto."
                )
                # Restamos un microsegundo para asegurar que la consulta (que usa '>') incluya el primer punto.
                first_ts_dt = datetime.fromisoformat(
                    first_timestamp_str.replace("Z", "+00:00")
                )
                start_time = (
                    first_ts_dt - timedelta(microseconds=1)
                ).isoformat()

        # Paginación por días
        pagination_days = self.config.get("options.days_of_pagination", 7)
        logger.debug(f"Calculando rangos de paginación desde: {start_time}")
        date_ranges = self._calculate_date_ranges(
            start_time, end_time, pagination_days
        )

        if len(date_ranges) > 1:
            logger.info(
                f"Paginación activada para '{measurement}'. La consulta se dividirá en {len(date_ranges)} períodos de {pagination_days} días."
            )

        for i, (period_start, period_end) in enumerate(date_ranges):
            if len(date_ranges) > 1:
                logger.info(
                    f"Procesando período {i+1}/{len(date_ranges)} para '{measurement}': {period_start} a {period_end}"
                )
            self._transfer_data(
                source_db,
                dest_db,
                measurement,
                period_start,
                period_end,
                fields_to_backup,
            )

    def _is_obsolete(self, last_timestamp_str, threshold_str):
        """Verifica si la última marca de tiempo supera el umbral de obsolescencia."""
        last_time = datetime.fromisoformat(
            last_timestamp_str.replace("Z", "+00:00")
        )

        num = int(threshold_str[:-1])
        unit = threshold_str[-1].lower()

        if unit == "s":
            delta = timedelta(seconds=num)
        elif unit == "m":
            delta = timedelta(minutes=num)
        elif unit == "h":
            delta = timedelta(hours=num)
        elif unit == "d":
            delta = timedelta(days=num)
        elif unit == "w":
            delta = timedelta(weeks=num)
        elif unit == "M":
            delta = timedelta(days=num * 30)  # Aproximación
        elif unit == "y":
            delta = timedelta(days=num * 365)  # Aproximación
        else:
            logger.warning(
                f"Unidad de umbral desconocida: {unit}. Ignorando obsolescencia."
            )
            return False

        return datetime.now(timezone.utc) - last_time > delta

    def _calculate_date_ranges(self, start_str, end_str, days):
        """Divide un rango de fechas en bloques más pequeños para paginación."""
        if start_str:
            start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
        else:
            # Si no hay inicio, usamos una fecha muy antigua para capturar todo
            start = datetime(1970, 1, 1, tzinfo=timezone.utc)

        if end_str:
            end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
        else:
            end = datetime.now(timezone.utc)

        ranges = []
        current_start = start
        while current_start < end:
            current_end = current_start + timedelta(days=days)
            if current_end > end:
                current_end = end
            ranges.append((current_start.isoformat(), current_end.isoformat()))
            current_start = current_end

        return ranges

    def _transfer_data(
        self,
        source_db,
        dest_db,
        measurement,
        period_start,
        period_end,
        fields_to_backup,
    ):
        """Construye la consulta, la ejecuta y escribe los datos en el destino."""
        query = self._build_query(
            source_db, measurement, period_start, period_end, fields_to_backup
        )
        if not query:
            logger.warning(
                f"No se generó ninguna consulta para la medición '{measurement}'. Saltando."
            )
            return

        try:
            logger.info(
                f"[{source_db} -> {dest_db}] Consultando datos para '{measurement}' en el período actual."
            )
            results = self._execute_with_retry(
                self.source_client.query, query, source_db
            )
            if not results:
                logger.debug(
                    f"La consulta para '{measurement}' no devolvió resultados para el rango."
                )
                return

            points_to_write = []
            for point_group in results.items():
                # point_group es una tupla: (('measurement_name', {tags...}), [puntos...])
                series_tags = point_group[0][1]
                series_points = point_group[1]

                for p in series_points:
                    # Filtramos explícitamente los campos para escribir SOLO los que corresponden a este backup.
                    # Esta es la corrección clave para evitar la contaminación de datos.
                    filtered_fields = {
                        k: v
                        for k, v in p.items()
                        if k in fields_to_backup and v is not None
                    }

                    point = {
                        "measurement": measurement,
                        "tags": series_tags,
                        "time": p["time"],
                        "fields": filtered_fields,
                    }
                    # Solo añadir el punto si tiene al menos un campo válido tras el filtrado
                    if point["fields"]:
                        points_to_write.append(point)

            if points_to_write:
                logger.info(
                    f"[{source_db}] Se encontraron {len(points_to_write)} puntos válidos (no nulos) para los campos de interés en este período."
                )
                logger.info(
                    f"[{source_db} -> {dest_db}] Escribiendo {len(points_to_write)} puntos de '{measurement}'."
                )
                self._execute_with_retry(
                    self.dest_client.write_points, points_to_write, dest_db
                )
                logger.info(
                    f"[{dest_db}] Escritura completada para '{measurement}' en este período."
                )
            else:
                logger.info(
                    f"No se encontraron nuevos puntos válidos (no nulos) para los campos de interés en este período."
                )

        except Exception as e:
            logger.error(
                f"Fallo en la transferencia de datos para '{measurement}': {e}"
            )

    def _build_query(
        self, source_db, measurement, start_time, end_time, fields_to_backup
    ):
        """Construye la consulta SELECT * con filtros de tiempo y group by."""
        if not fields_to_backup:
            logger.warning(
                f"No hay campos que respaldar para '{measurement}' después de aplicar filtros."
            )
            return None

        select_clause = ", ".join([f'"{f}"' for f in fields_to_backup])
        query = f'SELECT {select_clause} FROM "{measurement}"'

        # Cláusula WHERE para el tiempo
        time_conditions = []
        if start_time:
            # Usamos > para no duplicar el último punto ya existente
            time_conditions.append(f"time > '{start_time}'")
        if end_time:
            time_conditions.append(f"time <= '{end_time}'")

        if time_conditions:
            query += " WHERE " + " AND ".join(time_conditions)

        # Cláusula GROUP BY
        group_by = self.config.get("source.group_by")
        if group_by:
            # Al agrupar, también debemos incluir todas las etiquetas (*)
            query += f" GROUP BY *, time({group_by})"
        else:
            # Agrupar por todas las etiquetas si no hay group by de tiempo
            query += f" GROUP BY *"

        return query
