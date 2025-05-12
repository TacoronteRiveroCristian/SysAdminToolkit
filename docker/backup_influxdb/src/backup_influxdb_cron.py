#!/usr/bin/env python3
"""
Script to set up and run scheduled backups using cron.
This script is used as an entrypoint when running the container with scheduling enabled.
"""

import os
import sys
import time
from crontab import CronTab
from croniter import croniter
from datetime import datetime

from conf import BACKUP_SCHEDULE, logger

# Path to the main backup script
BACKUP_SCRIPT = "/app/backup_influxdb.py"


def setup_cron(schedule: str) -> None:
    """
    Set up cron job for backup script.

    Args:
        schedule: Cron schedule expression (e.g., "0 */6 * * *")
    """
    logger.info(f"Setting up cron with schedule: {schedule}")

    # Create a system cron
    cron = CronTab(user=True)

    # Remove any existing jobs for the backup script
    cron.remove_all(comment="influxdb_backup")

    # Create new job
    job = cron.new(
        command=f"python {BACKUP_SCRIPT} >> /var/log/backup_influxdb/cron.log 2>&1",
        comment="influxdb_backup"
    )

    # Set schedule
    job.setall(schedule)

    # Write to crontab
    cron.write()

    logger.info("Cron job set up successfully")


def get_next_run_time(schedule: str) -> datetime:
    """
    Get the next scheduled run time.

    Args:
        schedule: Cron schedule expression

    Returns:
        datetime: Next scheduled run time
    """
    iter = croniter(schedule, datetime.now())
    return iter.get_next(datetime)


def run_on_schedule(schedule: str) -> None:
    """
    Run the backup script on schedule and keep the container running.

    Args:
        schedule: Cron schedule expression
    """
    while True:
        next_run = get_next_run_time(schedule)
        now = datetime.now()

        # Calculate time until next run
        time_until_next_run = (next_run - now).total_seconds()

        logger.info(f"Next backup scheduled at: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Waiting {time_until_next_run:.0f} seconds until next run")

        # Sleep until next run time
        time.sleep(time_until_next_run)

        # Run backup script directly for immediate execution
        logger.info("Running backup script now")
        os.system(f"python {BACKUP_SCRIPT}")


def main():
    """Main function."""
    if not BACKUP_SCHEDULE:
        logger.error("No backup schedule configured. Set the BACKUP_SCHEDULE environment variable.")
        return False

    try:
        # Validate cron expression
        if not croniter.is_valid(BACKUP_SCHEDULE):
            logger.error(f"Invalid cron expression: {BACKUP_SCHEDULE}")
            return False

        # Set up cron job
        setup_cron(BACKUP_SCHEDULE)

        # Run backup immediately
        logger.info("Running initial backup...")
        os.system(f"python {BACKUP_SCRIPT}")

        # Start cron service
        os.system("service cron start")

        # Keep container running and monitor
        run_on_schedule(BACKUP_SCHEDULE)

        return True

    except Exception as e:
        logger.error(f"Error setting up scheduled backups: {str(e)}\n")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
