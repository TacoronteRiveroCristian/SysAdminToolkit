import logging
import re
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

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parsea un timestamp de InfluxDB (con o sin decimales) a un objeto datetime."""
        # InfluxDB a veces devuelve timestamps con precisión de nanosegundos.
        # datetime.fromisoformat no maneja más de 6 dígitos para microsegundos.
        if "." in timestamp_str:
            parts = timestamp_str.split(".")
            main_part = parts[0]
            frac_part = parts[1].replace("Z", "")
            # Truncar a microsegundos (6 dígitos)
            frac_part = frac_part[:6]
            timestamp_str = f"{main_part}.{frac_part}Z"

        # Asegurarse de que termine en 'Z' para que sea reconocido como UTC
        if not timestamp_str.endswith("Z"):
            timestamp_str += "Z"

        return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    def _parse_duration(self, duration_str: str) -> timedelta:
        """Parsea una cadena de duración (ej: '30d', '6M', '1y') a un timedelta."""
        match = re.match(r"(\d+)([smhdwyM])", duration_str)
        if not match:
            raise ValueError(f"Formato de duración inválido: '{duration_str}'")

        value, unit = int(match.group(1)), match.group(2)

        if unit == "s":
            return timedelta(seconds=value)
        if unit == "m":
            return timedelta(minutes=value)
        if unit == "h":
            return timedelta(hours=value)
        if unit == "d":
            return timedelta(days=value)
        if unit == "w":
            return timedelta(weeks=value)
        # Estimaciones para meses y años
        if unit == "M":
            return timedelta(days=value * 30)
        if unit == "y":
            return timedelta(days=value * 365)

        raise ValueError(f"Unidad de duración desconocida: '{unit}'")

    def _execute_with_retry(self, func, *args, **kwargs):
        """Ejecuta una función con una política de reintentos."""
        for attempt in range(self.retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Fallo la ejecución de '{func.__name__}' (intento {attempt + 1}/{self.retries + 1}): {e}"
                )
                if attempt < self.retries:
                    logger.info(
                        f"Reintentando en {self.retry_delay} segundos..."
                    )
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        f"Fallaron todos los reintentos para '{func.__name__}'."
                    )
                    raise  # Re-lanzar la excepción final

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

    def _filter_obsolete_fields(self, dest_db, measurement, fields):
        """
        Filtra una lista de campos, descartando aquellos que son obsoletos.
        """
        threshold_str = self.config.get("options.field_obsolete_threshold")
        if not threshold_str:
            return fields  # No hay umbral, no se filtra nada

        logger.debug(
            f"Verificando obsolescencia de campos para '{measurement}' con umbral '{threshold_str}'..."
        )

        active_fields = []
        try:
            obsolete_threshold_td = self._parse_duration(threshold_str)
        except ValueError as e:
            logger.error(
                f"Valor de 'field_obsolete_threshold' no válido: {e}. No se aplicará el filtro."
            )
            return fields

        for field in fields:
            # Consultar el último timestamp para este campo específico
            last_ts_str = self._execute_with_retry(
                self.dest_client.get_last_timestamp,
                dest_db,
                measurement,
                fields=[field],
            )

            if last_ts_str:
                last_ts = self._parse_timestamp(last_ts_str)
                # Si el último punto es más reciente que el umbral de obsolescencia, el campo está activo
                if (
                    datetime.now(timezone.utc) - last_ts
                ) <= obsolete_threshold_td:
                    active_fields.append(field)
                else:
                    logger.warning(
                        f"Campo '{field}' en '{measurement}' ignorado por obsoleto "
                        f"(último dato en destino es de {last_ts_str}, umbral: {threshold_str})."
                    )
            else:
                # Si no hay timestamp, el campo es nuevo en el destino, por lo tanto, está activo.
                active_fields.append(field)

        return active_fields

    def _process_measurement(
        self, source_db, dest_db, measurement, start_time, end_time
    ):
        """Procesa una única medición, copiando los datos."""
        logger.info(f"Procesando medición: '{measurement}'")

        candidate_fields = self._get_fields_to_backup(source_db, measurement)
        if not candidate_fields:
            logger.warning(
                f"No hay campos que respaldar para '{measurement}' después de aplicar filtros de configuración. Saltando."
            )
            return

        # Filtrar campos obsoletos antes de continuar
        fields_to_backup = self._filter_obsolete_fields(
            dest_db, measurement, candidate_fields
        )

        if not fields_to_backup:
            logger.info(
                f"No hay campos activos que respaldar para '{measurement}' después de filtrar por obsolescencia. Saltando."
            )
            return

        logger.debug(
            f"Campos activos para este backup de '{measurement}': {fields_to_backup}"
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
                obsolete_threshold_str = self.config.get(
                    "options.incremental.obsolete_threshold"
                )
                if obsolete_threshold_str:
                    try:
                        obsolete_threshold = self._parse_duration(
                            obsolete_threshold_str
                        )
                        if self._is_obsolete(
                            last_timestamp_str, obsolete_threshold
                        ):
                            logger.info(
                                f"La medición '{measurement}' está obsoleta para los campos de interés. Saltando..."
                            )
                            return
                    except ValueError as e:
                        logger.error(
                            f"Valor de 'incremental.obsolete_threshold' no válido: {e}. No se aplicará el filtro."
                        )
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
        """Consulta datos de origen y los escribe en el destino para un período."""
        try:
            # Construir y ejecutar la consulta en el origen
            query = self.source_client.build_query(
                source_db,
                measurement,
                period_start,
                period_end,
                fields_to_backup,
                self.config.get("source.group_by", ""),
            )
            logger.info(
                f"[{source_db} -> {dest_db}] Consultando datos para '{measurement}' en el período actual."
            )
            results = self._execute_with_retry(
                self.source_client.query_data, source_db, query
            )

            # Extraer y transformar puntos
            points_to_write = self.source_client.extract_points_from_result(
                results
            )

            if not points_to_write:
                logger.info(
                    f"[{source_db}] No se encontraron nuevos puntos para '{measurement}' en este período."
                )
                return

            logger.info(
                f"[{source_db}] Se encontraron {len(points_to_write)} puntos válidos (no nulos) para los campos de interés en este período."
            )

            # Escribir en el destino
            logger.info(
                f"[{source_db} -> {dest_db}] Escribiendo {len(points_to_write)} puntos de '{measurement}'."
            )
            self._execute_with_retry(
                self.dest_client.write_points, points_to_write, dest_db
            )
            logger.info(
                f"[{dest_db}] Escritura completada para '{measurement}' en este período."
            )

        except Exception as e:
            logger.error(
                f"Fallo en la transferencia de datos para '{measurement}': {e}"
            )
            # Re-lanzar para que el scheduler lo marque como fallido y lo reintente
            raise

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
