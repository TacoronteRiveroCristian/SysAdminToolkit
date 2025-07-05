"""
Scheduler para el sistema de backup de InfluxDB
===============================================

Maneja la programación y ejecución de backups usando expresiones cron.
"""

import logging
import signal
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from croniter import croniter

from .utils import get_process_id


class SchedulerError(Exception):
    """Excepción para errores del scheduler"""

    pass


class BackupScheduler:
    """
    Scheduler para backups programados con cron.

    Maneja la ejecución programada de backups usando expresiones cron.
    """

    def __init__(self, config_name: str, logger: logging.Logger):
        """
        Inicializa el scheduler.

        Args:
            config_name: Nombre de la configuración
            logger: Logger para mensajes
        """
        self.config_name = config_name
        self.logger = logger
        self.process_id = get_process_id()

        # Estado del scheduler
        self.is_running = False
        self.should_stop = False
        self.current_thread = None
        self.next_run_time = None
        self.cron_expression = None

        # Configurar señales para parada graceful
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Configura los manejadores de señales."""

        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, stopping scheduler...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def validate_cron_expression(self, cron_expr: str) -> bool:
        """
        Valida una expresión cron.

        Args:
            cron_expr: Expresión cron a validar

        Returns:
            bool: True si es válida
        """
        try:
            croniter(cron_expr)
            return True
        except (ValueError, TypeError):
            return False

    def get_next_run_time(
        self, cron_expr: str, base_time: datetime = None
    ) -> datetime:
        """
        Calcula la próxima ejecución basada en una expresión cron.

        Args:
            cron_expr: Expresión cron
            base_time: Tiempo base (por defecto ahora)

        Returns:
            datetime: Próxima ejecución

        Raises:
            SchedulerError: Si la expresión cron no es válida
        """
        if not self.validate_cron_expression(cron_expr):
            raise SchedulerError(f"Invalid cron expression: {cron_expr}")

        if base_time is None:
            base_time = datetime.now()

        cron = croniter(cron_expr, base_time)
        return cron.get_next(datetime)

    def schedule_backup(
        self, cron_expr: str, backup_function: Callable, *args, **kwargs
    ) -> None:
        """
        Programa un backup usando una expresión cron.

        Args:
            cron_expr: Expresión cron
            backup_function: Función de backup a ejecutar
            *args: Argumentos para la función
            **kwargs: Argumentos nombrados para la función

        Raises:
            SchedulerError: Si ya hay un backup programado o expresión inválida
        """
        if self.is_running:
            raise SchedulerError("Scheduler is already running")

        if not self.validate_cron_expression(cron_expr):
            raise SchedulerError(f"Invalid cron expression: {cron_expr}")

        self.cron_expression = cron_expr
        self.next_run_time = self.get_next_run_time(cron_expr)

        self.logger.info(f"Backup scheduled with cron: {cron_expr}")
        self.logger.info(f"Next run: {self.next_run_time}")

        # Crear y iniciar el thread del scheduler
        self.current_thread = threading.Thread(
            target=self._scheduler_loop,
            args=(backup_function, args, kwargs),
            name=f"BackupScheduler-{self.config_name}",
            daemon=True,
        )

        self.is_running = True
        self.should_stop = False
        self.current_thread.start()

    def _scheduler_loop(
        self, backup_function: Callable, args: tuple, kwargs: dict
    ) -> None:
        """
        Bucle principal del scheduler.

        Args:
            backup_function: Función de backup
            args: Argumentos para la función
            kwargs: Argumentos nombrados
        """
        self.logger.info(
            f"Scheduler loop started for config: {self.config_name}"
        )

        while not self.should_stop:
            try:
                current_time = datetime.now()

                # Verificar si es hora de ejecutar el backup
                if current_time >= self.next_run_time:
                    self._execute_scheduled_backup(
                        backup_function, args, kwargs
                    )

                    # Calcular próxima ejecución
                    self.next_run_time = self.get_next_run_time(
                        self.cron_expression, current_time
                    )

                    self.logger.info(
                        f"Next backup scheduled for: {self.next_run_time}"
                    )

                # Dormir un poco para no consumir mucha CPU
                time.sleep(30)  # Verificar cada 30 segundos

            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Esperar más tiempo si hay error

        self.logger.info("Scheduler loop stopped")
        self.is_running = False

    def _execute_scheduled_backup(
        self, backup_function: Callable, args: tuple, kwargs: dict
    ) -> None:
        """
        Ejecuta un backup programado.

        Args:
            backup_function: Función de backup
            args: Argumentos para la función
            kwargs: Argumentos nombrados
        """
        start_time = datetime.now()

        self.logger.info(f"=== SCHEDULED BACKUP STARTED ===")
        self.logger.info(f"Config: {self.config_name}")
        self.logger.info(f"Start time: {start_time}")

        try:
            # Ejecutar el backup
            result = backup_function(*args, **kwargs)

            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.info(f"=== SCHEDULED BACKUP COMPLETED ===")
            self.logger.info(f"Duration: {duration}")
            self.logger.info(f"Result: {result}")

        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.error(f"=== SCHEDULED BACKUP FAILED ===")
            self.logger.error(f"Duration: {duration}")
            self.logger.error(f"Error: {e}")
            self.logger.exception("Full traceback:")

    def run_once(self, backup_function: Callable, *args, **kwargs) -> Any:
        """
        Ejecuta un backup una sola vez (modo incremental sin schedule).

        Args:
            backup_function: Función de backup
            *args: Argumentos para la función
            **kwargs: Argumentos nombrados

        Returns:
            Any: Resultado de la función de backup
        """
        start_time = datetime.now()

        self.logger.info(f"=== SINGLE BACKUP STARTED ===")
        self.logger.info(f"Config: {self.config_name}")
        self.logger.info(f"Start time: {start_time}")

        try:
            result = backup_function(*args, **kwargs)

            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.info(f"=== SINGLE BACKUP COMPLETED ===")
            self.logger.info(f"Duration: {duration}")

            return result

        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time

            self.logger.error(f"=== SINGLE BACKUP FAILED ===")
            self.logger.error(f"Duration: {duration}")
            self.logger.error(f"Error: {e}")
            self.logger.exception("Full traceback:")

            raise

    def stop(self) -> None:
        """Detiene el scheduler."""
        if not self.is_running:
            return

        self.logger.info("Stopping scheduler...")
        self.should_stop = True

        # Esperar a que termine el thread
        if self.current_thread and self.current_thread.is_alive():
            self.current_thread.join(timeout=30)

            if self.current_thread.is_alive():
                self.logger.warning("Scheduler thread did not stop gracefully")

        self.is_running = False
        self.logger.info("Scheduler stopped")

    def get_status(self) -> Dict[str, Any]:
        """
        Retorna el estado actual del scheduler.

        Returns:
            Dict: Estado del scheduler
        """
        return {
            "config_name": self.config_name,
            "is_running": self.is_running,
            "should_stop": self.should_stop,
            "next_run_time": self.next_run_time,
            "cron_expression": self.cron_expression,
            "process_id": self.process_id,
            "thread_alive": (
                self.current_thread.is_alive() if self.current_thread else False
            ),
        }

    def get_time_until_next_run(self) -> Optional[timedelta]:
        """
        Calcula el tiempo hasta la próxima ejecución.

        Returns:
            timedelta: Tiempo hasta la próxima ejecución o None si no está programado
        """
        if not self.next_run_time:
            return None

        current_time = datetime.now()

        if self.next_run_time > current_time:
            return self.next_run_time - current_time
        else:
            return timedelta(0)

    def is_due(self) -> bool:
        """
        Verifica si es hora de ejecutar el backup.

        Returns:
            bool: True si es hora de ejecutar
        """
        if not self.next_run_time:
            return False

        return datetime.now() >= self.next_run_time

    def wait_for_next_run(self, max_wait_seconds: int = None) -> bool:
        """
        Espera hasta la próxima ejecución programada.

        Args:
            max_wait_seconds: Máximo tiempo de espera en segundos

        Returns:
            bool: True si llegó el momento, False si se agotó el tiempo
        """
        if not self.next_run_time:
            return False

        time_until_next = self.get_time_until_next_run()
        if not time_until_next:
            return True

        wait_seconds = time_until_next.total_seconds()

        if max_wait_seconds and wait_seconds > max_wait_seconds:
            wait_seconds = max_wait_seconds

        self.logger.info(f"Waiting {wait_seconds:.0f} seconds for next run...")

        start_wait = datetime.now()
        while datetime.now() - start_wait < timedelta(seconds=wait_seconds):
            if self.should_stop:
                return False

            time.sleep(1)

        return self.is_due()

    def update_schedule(self, new_cron_expr: str) -> None:
        """
        Actualiza la expresión cron del scheduler.

        Args:
            new_cron_expr: Nueva expresión cron

        Raises:
            SchedulerError: Si la expresión no es válida
        """
        if not self.validate_cron_expression(new_cron_expr):
            raise SchedulerError(f"Invalid cron expression: {new_cron_expr}")

        self.cron_expression = new_cron_expr
        self.next_run_time = self.get_next_run_time(new_cron_expr)

        self.logger.info(f"Schedule updated: {new_cron_expr}")
        self.logger.info(f"Next run: {self.next_run_time}")

    def get_recent_runs(self, cron_expr: str, count: int = 5) -> list:
        """
        Obtiene las últimas ejecuciones basadas en una expresión cron.

        Args:
            cron_expr: Expresión cron
            count: Número de ejecuciones a retornar

        Returns:
            list: Lista de fechas de ejecución
        """
        if not self.validate_cron_expression(cron_expr):
            return []

        base_time = datetime.now()
        cron = croniter(cron_expr, base_time)

        runs = []
        for _ in range(count):
            prev_run = cron.get_prev(datetime)
            runs.append(prev_run)

        return list(reversed(runs))

    def get_upcoming_runs(self, cron_expr: str, count: int = 5) -> list:
        """
        Obtiene las próximas ejecuciones basadas en una expresión cron.

        Args:
            cron_expr: Expresión cron
            count: Número de ejecuciones a retornar

        Returns:
            list: Lista de fechas de ejecución
        """
        if not self.validate_cron_expression(cron_expr):
            return []

        base_time = datetime.now()
        cron = croniter(cron_expr, base_time)

        runs = []
        for _ in range(count):
            next_run = cron.get_next(datetime)
            runs.append(next_run)

        return runs

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def __repr__(self) -> str:
        """Representación en string del scheduler."""
        return (
            f"BackupScheduler(config='{self.config_name}', "
            f"running={self.is_running}, next_run={self.next_run_time})"
        )
