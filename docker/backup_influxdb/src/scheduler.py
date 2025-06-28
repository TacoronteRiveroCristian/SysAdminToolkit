import logging
import time

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


class Scheduler:
    """
    Gestiona la ejecución programada de tareas usando un cron.
    """

    def __init__(self, job_function, cron_expression):
        """
        Inicializa el planificador.

        :param job_function: La función que se ejecutará en cada disparo del cron.
        :param cron_expression: La expresión cron que define la programación.
        """
        self.job_function = job_function
        self.cron_expression = cron_expression
        self.scheduler = BlockingScheduler(timezone="UTC")

    def start(self):
        """
        Inicia el planificador. Esta es una operación de bloqueo.
        """
        if not self.cron_expression:
            logger.error(
                "No se ha proporcionado una expresión cron para el planificador."
            )
            return

        logger.info(
            f"Programando la tarea de backup con la expresión cron: '{self.cron_expression}'"
        )

        try:
            self.scheduler.add_job(
                self.job_function,
                CronTrigger.from_crontab(self.cron_expression),
            )
        except ValueError as e:
            logger.error(
                f"La expresión cron '{self.cron_expression}' no es válida: {e}"
            )
            return

        logger.info(
            "El planificador está en marcha. Presiona Ctrl+C para detener."
        )
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Planificador detenido por el usuario.")
            self.scheduler.shutdown()
        except Exception as e:
            logger.critical(
                f"El planificador se ha detenido debido a un error inesperado: {e}"
            )
            self.scheduler.shutdown()


def run_job_once(job_function):
    """
    Ejecuta una tarea una sola vez y maneja los errores.
    """
    logger.info("Ejecutando la tarea de backup una sola vez.")
    try:
        job_function()
    except Exception as e:
        logger.critical(
            f"La tarea de backup ha fallado con un error crítico: {e}",
            exc_info=True,
        )
