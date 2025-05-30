import os
import sys
import logging
from crontab import CronTab
from conf import load_config, setup_logging

# Configure logging early in case of issues
logger = logging.getLogger(__name__)

DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "/var/log/backup_postgres/cron_setup.log"

def main():
    # Initial basic logging setup for cron script itself
    # The main backup script will use its own logging config
    log_level_env = os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    setup_logging(log_level_env, DEFAULT_LOG_FILE)

    config_path = os.getenv("BACKUP_CONFIG_PATH", "/app/backup_config.yaml")
    logger.info(f"Loading configuration from: {config_path}")

    try:
        config = load_config(config_path)
    except FileNotFoundError:
        logger.error(f"Configuration file not found at {config_path}. Cron job cannot be set up.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error loading configuration: {e}. Cron job cannot be set up.")
        sys.exit(1)

    options_config = config.get("options", {})
    backup_schedule = options_config.get("backup_schedule")

    if not backup_schedule or not str(backup_schedule).strip():
        logger.info("No backup_schedule defined in configuration or it is empty. Cron job will not be set up. The main script will run once.")
        # If there is no schedule, this cron script's purpose is done.
        # The docker-compose command will fall back to running backup_postgres.py directly.
        sys.exit(0)

    logger.info(f"Backup schedule: '{backup_schedule}'")

    # Path to the main backup script within the container
    backup_script_path = "/app/backup_postgres.py"
    python_executable = sys.executable # Gets the path to the current python interpreter

    # Create a new cron tab for the root user (common in Docker)
    # Note: Ensure the cron daemon is running in your Docker container.
    # The Dockerfile for this project should handle starting the cron service.
    try:
        # Attempt to use the system cron. May require root or cron group permissions.
        cron = CronTab(user=True) # True for current user, or specify user='root' if needed and permissions allow
    except Exception as e:
        logger.warning(f"Could not access user cron tab ({e}). Attempting system cron. This might require root.")
        try:
            cron = CronTab(user='root')
        except Exception as e_root:
            logger.error(f"Failed to access system cron tab as root: {e_root}. Please ensure cron is installed and user has permissions.")
            sys.exit(1)

    # Remove any existing jobs managed by this script to prevent duplicates
    # Use a unique comment to identify jobs managed by this script
    job_comment = "PostgreSQL Backup Service Job"
    for job in cron:
        if job.comment == job_comment:
            logger.info(f"Removing existing cron job: {job}")
            cron.remove(job)

    # Create the new cron job
    job = cron.new(command=f"{python_executable} {backup_script_path}", comment=job_comment)

    if not CronTab.is_valid(backup_schedule):
        logger.error(f"Invalid cron expression: '{backup_schedule}'. Please check your configuration.")
        sys.exit(1)

    job.setall(backup_schedule)

    try:
        cron.write()
        logger.info(f"Cron job successfully created: {job.command} with schedule '{job.slices}'")
    except Exception as e:
        logger.error(f"Failed to write cron tab: {e}. Check permissions and cron service status.")
        sys.exit(1)

    logger.info("Cron setup complete. Starting cron daemon and keeping container alive...")

    # This part is crucial for Docker: start cron in the foreground
    # and keep the container running. The CMD of the Dockerfile usually handles this.
    # However, since this script is the entry point when scheduling, it needs to start cron.
    try:
        # Start cron daemon in the foreground
        os.execv("/usr/sbin/cron", ["cron", "-f"])
    except FileNotFoundError:
        logger.error("Could not find /usr/sbin/cron. Ensure cron is installed correctly in the Docker image.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to start cron daemon: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
