# PostgreSQL Backup Service

A Docker Compose service that provides automated, configurable backups from one PostgreSQL server to another using Python.

## Overview

This service allows you to:

- Run backups on a schedule (via cron) or on-demand
- Select specific databases or back up everything
- Configure backup strategies (e.g., full, incremental - to be implemented)
- Run in development mode (with local PostgreSQL) or production mode
- Granular control over backup options using YAML configuration

## Architecture

The service consists of two main components:

1. **Python Container**: Executes the backup script with the configured settings
2. **PostgreSQL Container**: (Development mode only) Provides a local PostgreSQL instance for testing

## Source Code Organization

The project has the following key files:

- `docker-compose.yaml`: Defines the service architecture and dependencies
- `backup_postgres.dockerfile`: Docker image definition for the backup service
- `src/backup_postgres.py`: Main backup script that copies data from source to destination
- `src/backup_postgres_cron.py`: Script that sets up cron jobs for scheduled backups
- `src/conf.py`: Configuration module that loads and validates YAML configuration
- `src/requirements.txt`: Python dependencies
- `backup_config.yaml.template`: Template for YAML-based configuration with all available options

## Deployment Options

### Development Mode

```yaml
# docker-compose.yml with profile=development
services:
  postgres:
    image: postgres:latest
    # Configuration for local PostgreSQL
    ...

  backup-service:
    build:
      context: .
      dockerfile: backup_postgres.dockerfile
    volumes:
      - ./backup_config.yaml:/app/backup_config.yaml
    depends_on:
      - postgres
    ...
```

### Production Mode

```yaml
# docker-compose.yml with profile=production
services:
  backup-service:
    build:
      context: .
      dockerfile: backup_postgres.dockerfile
    volumes:
      - ./backup_config.yaml:/app/backup_config.yaml
    ...
```

## Configuration

The service uses a **single YAML configuration file** for all settings. This approach centralizes all configuration in one well-structured file, providing maximum flexibility.

### Setting Up Configuration

1. Copy the template file:
   ```bash
   cp backup_config.yaml.template backup_config.yaml
   ```

2. Edit the configuration file:
   ```bash
   nano backup_config.yaml
   ```

3. Mount the configuration file when running the container:
   ```yaml
   volumes:
     - ./backup_config.yaml:/app/backup_config.yaml
   ```

### Configuration Structure

The YAML file is organized into sections:

```yaml
# Global settings
global:
  network: postgres_network

# Source database configuration
source:
  host: source-postgres
  port: 5432
  user: user
  password: password
  databases:
    - name: metrics
      destination_db_name: metrics_backup # Optional: specify a different name for the destination database
  # ...more settings

# Destination database configuration
destination:
  host: destination-postgres
  port: 5432
  user: user
  password: password
  # ...more settings

# Backup options
options:
  log_file: /var/log/backup_postgres/backup.log
  log_level: INFO
  backup_schedule: "0 0 * * *"  # cron expression
  # ...more backup strategy options to be added
```

### Example Configuration

Here's a complete example:

```yaml
global:
  network: postgres_network

source:
  host: source-postgres
  port: 5432
  user: admin
  password: password
  databases:
    - name: metrics
      destination_db_name: metrics_backup
    - name: telegraf
      destination_db_name: telegraf_backup

destination:
  host: destination-postgres
  port: 5432
  user: admin
  password: password

options:
  log_file: /var/log/backup_postgres/backup.log
  log_level: INFO
  backup_schedule: "0 */6 * * *"
```
