import subprocess
import logging
import sys
import os
from datetime import datetime
from conf import load_config, setup_logging

# Configure logging
logger = logging.getLogger(__name__)

def get_pg_env_vars(db_config):
    """Helper to create environment variables for pg_dump/pg_restore."""
    env = os.environ.copy()
    env["PGHOST"] = db_config["host"]
    env["PGPORT"] = str(db_config["port"])
    env["PGUSER"] = db_config["user"]
    env["PGPASSWORD"] = db_config["password"]
    return env

def run_pg_command(command, env_vars, db_name=None):
    """Runs a PostgreSQL command (pg_dump, pg_restore, psql) and handles errors."""
    full_command = list(command) # Make a copy to modify
    if db_name:
        full_command.extend(["-d", db_name])

    logger.debug(f"Running command: {' '.join(full_command)}")
    try:
        process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env_vars)
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            error_message = f"Error executing {' '.join(full_command)}.\nReturn code: {process.returncode}\nStdout: {stdout.decode('utf-8', 'ignore')}\nStderr: {stderr.decode('utf-8', 'ignore')}"
            logger.error(error_message)
            raise Exception(error_message)
        else:
            logger.info(f"Successfully executed {' '.join(full_command)}.")
            logger.debug(f"Stdout: {stdout.decode('utf-8', 'ignore')}")
            if stderr:
                 logger.debug(f"Stderr: {stderr.decode('utf-8', 'ignore')}") # Some commands like pg_restore output to stderr on success
        return stdout, stderr
    except FileNotFoundError:
        logger.error(f"Error: The command {' '.join(full_command)} was not found. Ensure PostgreSQL client tools are installed and in PATH.")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred with {' '.join(full_command)}: {e}")
        raise

def backup_database(source_config, db_name, backup_file_path, pg_dump_options):
    """Backs up a single PostgreSQL database using pg_dump."""
    logger.info(f"Starting backup for database '{db_name}' to '{backup_file_path}'")
    env_vars = get_pg_env_vars(source_config)

    command = [
        "pg_dump",
        "-F", "c",  # Custom format, good for pg_restore
        "-f", backup_file_path,
    ]
    if pg_dump_options:
        command.extend(pg_dump_options.split())

    run_pg_command(command, env_vars, db_name=db_name)
    logger.info(f"Backup for database '{db_name}' completed successfully to '{backup_file_path}'.")

def restore_database(destination_config, db_name_source, db_name_dest, backup_file_path, pg_restore_options):
    """Restores a single PostgreSQL database using pg_restore."""
    logger.info(f"Starting restore of '{backup_file_path}' to database '{db_name_dest}' on host '{destination_config['host']}'")
    env_vars = get_pg_env_vars(destination_config)

    # Check if destination database exists, create if not
    try:
        # Try to connect to the specific database. If it fails, the DB might not exist.
        run_pg_command(["psql", "-lqt"], env_vars, db_name=db_name_dest)
        logger.info(f"Database '{db_name_dest}' already exists on destination.")
    except Exception:
        logger.info(f"Database '{db_name_dest}' does not exist on destination. Attempting to create it.")
        try:
            # Connect to a default db like 'postgres' to create the new one
            run_pg_command(["createdb"], env_vars, db_name=db_name_dest)
            logger.info(f"Database '{db_name_dest}' created successfully on destination.")
        except Exception as e_create:
            logger.error(f"Failed to create database '{db_name_dest}' on destination: {e_create}")
            raise

    command = [
        "pg_restore",
        "--no-owner",      # Don't try to restore ownership, often causes permission issues
        "--no-acl",        # Don't try to restore ACLs
    ]
    if pg_restore_options:
        command.extend(pg_restore_options.split())
    command.append(backup_file_path)

    run_pg_command(command, env_vars, db_name=db_name_dest)
    logger.info(f"Restore of '{backup_file_path}' to database '{db_name_dest}' completed successfully.")

def main():
    config_path = os.getenv("BACKUP_CONFIG_PATH", "/app/backup_config.yaml")
    config = load_config(config_path)

    setup_logging(config.get("options", {}).get("log_level", "INFO"),
                  config.get("options", {}).get("log_file"))

    logger.info("PostgreSQL Backup Service started.")

    source_config = config["source"]
    destination_config = config["destination"]
    options_config = config.get("options", {})

    pg_dump_options = options_config.get("pg_dump_options", "")
    pg_restore_options = options_config.get("pg_restore_options", "--clean --if-exists")
    temp_dir = options_config.get("temp_dir", "/tmp")
    os.makedirs(temp_dir, exist_ok=True)

    if not source_config.get("databases"):
        logger.warning("No databases configured for backup. Exiting.")
        sys.exit(0)

    for db_info in source_config["databases"]:
        source_db_name = db_info["name"]
        dest_db_name = db_info.get("destination_db_name", source_db_name) # Use source name if destination not specified

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file_name = f"{source_db_name}_{timestamp}.dump"
        backup_file_path = os.path.join(temp_dir, backup_file_name)

        try:
            logger.info(f"Processing database: {source_db_name}")
            backup_database(source_config, source_db_name, backup_file_path, pg_dump_options)
            restore_database(destination_config, source_db_name, dest_db_name, backup_file_path, pg_restore_options)
            logger.info(f"Successfully backed up and restored database '{source_db_name}' to '{dest_db_name}'.")
        except Exception as e:
            logger.error(f"Failed to backup/restore database '{source_db_name}': {e}")
            # Optionally, decide if you want to continue with other databases or exit
            # For now, we log the error and continue
        finally:
            # Clean up the local backup file
            if os.path.exists(backup_file_path):
                try:
                    os.remove(backup_file_path)
                    logger.info(f"Cleaned up temporary backup file: {backup_file_path}")
                except OSError as e_remove:
                    logger.warning(f"Could not remove temporary backup file {backup_file_path}: {e_remove}")

    logger.info("PostgreSQL Backup Service finished.")

if __name__ == "__main__":
    main()
