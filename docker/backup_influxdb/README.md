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
- `src/conf.py`: Configuration module that loads and validates environment variables
- `src/requirements.txt`: Python dependencies
- `.env-example`: Example environment variables file

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
    environment:
      - SOURCE_URL=http://source-influxdb:8086
      - DEST_URL=http://influxdb:8086
      # Other configuration variables
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
    environment:
      - SOURCE_URL=http://source-influxdb:8086
      - DEST_URL=http://destination-influxdb:8086
      # Other configuration variables
    ...
```

## Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| SOURCE_URL | URL of source InfluxDB server | - | Yes |
| SOURCE_DBS | Comma-separated list of source databases | - | Yes |
| SOURCE_USER | Source InfluxDB username | - | No |
| SOURCE_PASSWORD | Source InfluxDB password | - | No |
| SOURCE_GROUP_BY | Time period for grouping data in queries | 5m | No |
| DEST_URL | URL of destination InfluxDB server | - | Yes |
| DEST_DBS | Comma-separated list of destination databases | - | Yes |
| DEST_USER | Destination InfluxDB username | - | No |
| DEST_PASSWORD | Destination InfluxDB password | - | No |
| MEASUREMENTS | Comma-separated list of measurements to back up | All | No |
| TIMEOUT_CLIENT | Timeout for InfluxDB client operations in seconds | 20 | No |
| DAYS_OF_PAGINATION | Days to split backup into when dealing with large datasets | 7 | No |
| LOG_FILE | Path to log file | /var/log/backup_influxdb/backup.log | No |
| LOG_LEVEL | Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | INFO | No |
| BACKUP_SCHEDULE | Cron expression for scheduled backups | - | No |
| INFLUXDB_NETWORK | Name of the Docker network | influxdb_network | No |

## Environment File

You can use a `.env` file to configure the service. An example `.env-example` file is provided. Copy this file to the main directory as `.env` and modify as needed:

```bash
# Copy the example file
cp .env-example .env

# Edit with your configuration
nano .env
```

Example `.env` content:

```ini
# Source InfluxDB
SOURCE_URL=http://source-influxdb:8086
SOURCE_DBS=metrics,telegraf
SOURCE_USER=
SOURCE_PASSWORD=
SOURCE_GROUP_BY=5m

# Destination InfluxDB
DEST_URL=http://destination-influxdb:8086
DEST_DBS=metrics_backup,telegraf_backup
DEST_USER=
DEST_PASSWORD=

# Backup Options
MEASUREMENTS=
TIMEOUT_CLIENT=20
DAYS_OF_PAGINATION=7

# Scheduling
# BACKUP_SCHEDULE=0 0 * * *  # Daily at midnight
```

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
     - Check last entry time in destination (for incremental backup)
     - If first backup, use pagination to handle large datasets

4. **Data Extraction and Transformation**
   - Query source data since last entry or in paginated chunks
   - Process numeric and non-numeric fields separately
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
   - Default is 7-day chunks, configurable via `DAYS_OF_PAGINATION`
   - Helps prevent memory issues with large datasets

## Scheduling

Two modes of operation are supported:

### On-Demand Backup
- Run the container without a schedule to perform a one-time backup
- The container will exit after the backup completes

### Scheduled Backup
- Set `BACKUP_SCHEDULE` environment variable with a cron expression
- Uses standard cron syntax (e.g., `0 */6 * * *` for every 6 hours)
- The scheduler will:
  1. Run an immediate backup on startup
  2. Set up the cron job with the specified schedule
  3. Keep the container running between scheduled tasks
  4. Log next run time and countdown

## Logging

Comprehensive logging is implemented:

- Logs are written to both a file (`LOG_FILE`) and the console
- Log level is configurable via `LOG_LEVEL`
- For Docker deployments, logs are stored in `/var/log/backup_influxdb/`
- The log format includes timestamps, log level, and detailed messages
- Logs include information about:
  - Connection status
  - Number of records processed
  - Field types detected
  - NaN/infinity values filtered
  - Backup progress and completion

## Getting Started

1. Clone this repository
2. Create and configure a `.env` file (see above)
3. Run with Docker Compose:

```bash
# Development mode with local InfluxDB
docker-compose --profile development up

# Production mode connecting to external InfluxDB servers
docker-compose --profile production up -d
```

## Usage Examples

### Backing up specific measurements

```yaml
environment:
  - SOURCE_URL=http://source-influxdb:8086
  - SOURCE_DBS=metrics
  - DEST_URL=http://backup-influxdb:8086
  - DEST_DBS=metrics_backup
  - MEASUREMENTS=cpu,memory,disk
```

### Running scheduled backups

```yaml
environment:
  - SOURCE_URL=http://source-influxdb:8086
  - SOURCE_DBS=metrics
  - DEST_URL=http://backup-influxdb:8086
  - DEST_DBS=metrics_backup
  - BACKUP_SCHEDULE=0 */6 * * *  # Every 6 hours
```

### Direct Python Script Usage

You can use the Python scripts directly outside of Docker if needed:

1. Install dependencies:
   ```bash
   pip install -r src/requirements.txt
   ```

2. Set environment variables and run:
   ```bash
   export SOURCE_URL=http://source-influxdb:8086
   export SOURCE_DBS=metrics
   export DEST_URL=http://destination-influxdb:8086
   export DEST_DBS=metrics_backup
   python src/backup_influxdb.py
   ```

## Troubleshooting

### Common Issues

- **Connection Failures**: Verify network connectivity and credentials
- **Missing Data**: Check if fields contain NaN or infinite values being filtered
- **Memory Issues**: Lower the `DAYS_OF_PAGINATION` value for very large datasets
- **Container Exits**: Ensure `BACKUP_SCHEDULE` is set for continuous operation

### Debugging

- Set `LOG_LEVEL=DEBUG` for more detailed logs
- Examine the backup logs in the mounted volume
- Run in development mode to test with a local InfluxDB instance
