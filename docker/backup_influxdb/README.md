# InfluxDB Backup Service

A Docker Compose service that provides automated, configurable backups from one InfluxDB 1.8 server to another using Python.

## Overview

This service allows you to:

- Run backups on a schedule (via cron) or on-demand
- Select specific measurements, databases, or back up everything
- Configure data grouping and filters for efficient transfers
- Handle incremental backups (only copying new data since last backup)
- Run in development mode (with local InfluxDB) or production mode
- Smart handling of different data types (numeric, string, boolean)
- Granular control over measurements and fields using YAML configuration

## Architecture

The service consists of two main components:

1. **Python Container**: Executes the backup script with the configured settings
2. **InfluxDB Container**: (Development mode only) Provides a local InfluxDB instance for testing

## Source Code Organization

The project has the following key files:

- `docker-compose.yaml`: Defines the service architecture and dependencies
- `backup_influxdb.dockerfile`: Docker image definition for the backup service
- `src/backup_influxdb.py`: Main backup script that copies data from source to destination
- `src/backup_influxdb_cron.py`: Script that sets up cron jobs for scheduled backups
- `src/conf.py`: Configuration module that loads and validates YAML configuration
- `src/requirements.txt`: Python dependencies
- `backup_config.yaml.template`: Template for YAML-based configuration with all available options

## Deployment Options

### Development Mode

```yaml
# docker-compose.yml with profile=development
services:
  influxdb:
    image: influxdb:1.8
    # Configuration for local InfluxDB
    ...

  backup-service:
    build:
      context: .
      dockerfile: backup_influxdb.dockerfile
    volumes:
      - ./backup_config.yaml:/app/backup_config.yaml
    depends_on:
      - influxdb
    ...
```

### Production Mode

```yaml
# docker-compose.yml with profile=production
services:
  backup-service:
    build:
      context: .
      dockerfile: backup_influxdb.dockerfile
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
  network: influxdb_network

# Source database configuration
source:
  url: http://source-influxdb:8086
  databases:
    - name: metrics
      destination: metrics_backup
  # ...more settings

# Destination database configuration
destination:
  url: http://destination-influxdb:8086
  # ...more settings

# Measurements filtering configuration
measurements:
  include: [cpu, memory]
  exclude: [system]
  specific:
    cpu:
      fields:
        include: [usage_user, usage_system]
        # ...more settings

# Options like logging, scheduling, etc.
options:
  timeout_client: 20
  days_of_pagination: 7
  log_file: /var/log/backup_influxdb/backup.log
  log_level: INFO
  backup_schedule: "0 0 * * *"  # cron expression
```

### Example Configuration

Here's a complete example:

```yaml
global:
  network: influxdb_network

source:
  url: http://source-influxdb:8086
  databases:
    - name: metrics
      destination: metrics_backup
    - name: telegraf
      destination: telegraf_backup
  user: admin
  password: password
  group_by: 5m

destination:
  url: http://destination-influxdb:8086
  user: admin
  password: password

measurements:
  include: [cpu, memory, disk]
  exclude: [system]

  specific:
    cpu:
      fields:
        include: [usage_user, usage_system, usage_idle]
        types: [numeric, string, boolean]

    memory:
      fields:
        exclude: [buffer, cached]
        types: [numeric, string]

    disk:
      fields:
        types: [numeric]

options:
  timeout_client: 30
  days_of_pagination: 7
  log_file: /var/log/backup_influxdb/backup.log
  log_level: INFO
  backup_schedule: "0 */6 * * *"
```

### Advanced Field Selection

You can precisely control which fields are backed up for each measurement:

1. **Include/Exclude Fields**: Specify exact fields to include or exclude
   ```yaml
   cpu:
     fields:
       include: [usage_user, usage_system]  # Only these fields
   ```

2. **Filter by Data Type**: Specify which types of data to copy
   ```yaml
   disk:
     fields:
       types: [numeric]  # Only numeric fields, no strings or booleans
   ```

3. **Combine Filters**: Apply multiple filtering rules
   ```yaml
   memory:
     fields:
       include: [used_percent]
       types: [numeric]  # Only numeric fields from the include list
   ```

This granular control allows you to reduce the amount of data transferred and stored, focusing only on the fields that matter to your use case.

## Data Type Handling

The backup service has sophisticated handling for different data types:

### Numeric Values
- Numeric fields (int, float) are processed separately from non-numeric fields
- NaN (Not a Number) values are detected and excluded from the backup
- Infinite values (`float('inf')` and `float('-inf')`) are automatically filtered out
- Numeric fields are aggregated using the `mean()` function when grouping by time periods

### String Values
- String fields are preserved in their original format
- String fields are aggregated using the `last()` function when grouping by time periods
- String values are properly escaped when sent to the destination database

### Boolean Values
- Boolean fields are treated as non-numeric values
- Boolean values are preserved in their original state (true/false)
- Like strings, booleans are aggregated using the `last()` function

### Time Values
- Timestamps are normalized to a consistent format: `YYYY-MM-DDThh:mm:ssZ`
- Time-based pagination helps manage large datasets

### Smart Field Handling
- Fields with prefixes from query aggregation functions (e.g., `mean_`, `last_`) have these prefixes stripped
- The backup process will report when NaN or infinite values are skipped
- When combining records from different data types, fields with the same name are properly merged

## Backup Process

1. **Connect to Servers**
   - Establish connections to source and destination InfluxDB servers
   - Verify connections with ping tests

2. **Database Processing**
   - For each database pair (source → destination):
     - Create destination database if it doesn't exist
     - Get list of measurements (all or filtered by configuration)

3. **Measurement Processing**
   - For each measurement:
     - Apply inclusion/exclusion filters from configuration
     - Check last entry time in destination (for incremental backup)
     - If first backup, use pagination to handle large datasets

4. **Data Extraction and Transformation**
   - Query source data since last entry or in paginated chunks
   - Process numeric and non-numeric fields separately
     - Apply field inclusion/exclusion filters from configuration
     - Numeric fields: Filter out NaN and infinite values
     - Non-numeric fields: Handle strings and booleans
   - Combine records with the same timestamp

5. **Data Writing**
   - Write processed data to destination measurements
   - Report on successful record transfers

6. **Logging**
   - Log all operations, warnings, and errors
   - Track NaN/infinite value filtering
   - Report on field types and counts

## Incremental Backup Strategy

The service implements a smart incremental backup approach:

1. **First Backup Detection**
   - If destination measurement is empty, perform a full backup
   - For large datasets, automatically switch to paginated approach

2. **Time-Based Incremental Backup**
   - For subsequent backups, only transfer data newer than the last entry in destination
   - Uses the exact timestamp of the last record to ensure no data loss

3. **Pagination for Large Datasets**
   - Automatically splits large datasets into manageable chunks
   - Default is 7-day chunks, configurable via `days_of_pagination` in YAML
   - Helps prevent memory issues with large datasets

## Scheduling

Two modes of operation are supported:

### On-Demand Backup
- Set `backup_schedule: ""` in YAML
- The container will perform a one-time backup and exit

### Scheduled Backup
- Set `backup_schedule` with a cron expression in YAML
- Example: `backup_schedule: "0 */6 * * *"` for every 6 hours
- The scheduler will:
  1. Run an immediate backup on startup
  2. Set up the cron job with the specified schedule
  3. Keep the container running between scheduled tasks
  4. Log next run time and countdown

## Logging

Comprehensive logging is implemented:

- Logs are written to both a file and the console
- Log level is configurable via `log_level` in YAML
- For Docker deployments, logs are stored in a mounted volume
- The log format includes timestamps, log level, and detailed messages
- Logs include information about:
  - Connection status
  - Number of records processed
  - Field types detected
  - NaN/infinity values filtered
  - Backup progress and completion

## Getting Started

1. Clone this repository
2. Create your configuration file:
   ```bash
   cp backup_config.yaml.template backup_config.yaml
   nano backup_config.yaml
   ```
3. Run with Docker Compose:

```bash
# Development mode with local InfluxDB
docker-compose --profile development up

# Production mode connecting to external InfluxDB servers
docker-compose --profile production up -d
```

## Usage Examples

### Basic Backup

```yaml
# backup_config.yaml
source:
  url: http://source-influxdb:8086
  databases:
    - name: metrics
      destination: metrics_backup

destination:
  url: http://destination-influxdb:8086
```

### Advanced Field Filtering

```yaml
# backup_config.yaml
# ... other configuration ...
measurements:
  specific:
    cpu:
      fields:
        include: [usage_user, usage_system, usage_idle]
    memory:
      fields:
        include: [used_percent, available, free]
```

### Running scheduled backups

```yaml
# backup_config.yaml
# ... other configuration ...
options:
  backup_schedule: "0 */6 * * *"  # Every 6 hours
```

### Direct Python Script Usage

You can use the Python scripts directly outside of Docker if needed:

1. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

2. Create a configuration file and run:
   ```bash
   cp backup_config.yaml.template backup_config.yaml
   # Edit the configuration file
   BACKUP_CONFIG_PATH=./backup_config.yaml python src/backup_influxdb.py
   ```

## Troubleshooting

### Common Issues

- **Connection Failures**: Verify network connectivity and credentials in your YAML
- **Missing Data**: Check if fields contain NaN or infinite values being filtered
- **Memory Issues**: Lower the `days_of_pagination` value for very large datasets
- **Container Exits**: Make sure your `backup_schedule` setting is valid if you want continuous operation
- **Missing Fields**: Check your YAML configuration for field inclusions/exclusions

### Debugging

- Set `log_level: DEBUG` in your YAML for more detailed logs
- Examine the backup logs in the mounted volume
- Run in development mode to test with a local InfluxDB instance
