#!/usr/bin/env python3
"""
InfluxDB Backup Script

This script performs backups from a source InfluxDB 1.8 server to a destination
InfluxDB 1.8 server. It supports backing up specific measurements, databases,
or entire servers and includes smart incremental backup features.

If this is the first backup, it will attempt to copy all data at once.
If there's too much data, it will use a weekly pagination approach.

For incremental backups, it will only copy data newer than the last entry
in the destination database.
"""

import os
import sys
import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Literal, Optional, Union, Any

from dateutil.parser import parse
from influxdb import InfluxDBClient
from influxdb.resultset import ResultSet

from conf import (
    SOURCE_DBS,
    DEST_DBS,
    SOURCE_GROUP_BY,
    MEASUREMENTS,
    DAYS_OF_PAGINATION,
    logger,
    get_source_client_params,
    get_dest_client_params
)


def check_connection(client: InfluxDBClient) -> bool:
    """
    Verify connection to an InfluxDB client.

    Args:
        client: InfluxDBClient instance

    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client.ping()
        logger.info(f"Connection successful to {client._host}:{client._port}")
        return True
    except Exception as e:
        logger.error(f"Connection failed to {client._host}:{client._port}: {str(e)}")
        return False


def get_entry_time(
    client: InfluxDBClient,
    measurement: str,
    order: Literal["ASC", "DESC"]
) -> Optional[str]:
    """
    Get timestamp of first or last record in a measurement.

    Args:
        client: InfluxDBClient instance
        measurement: Name of the measurement
        order: "ASC" for first entry, "DESC" for last entry

    Returns:
        str: Timestamp in format "YYYY-MM-DDThh:mm:ssZ" or None if no records
    """
    query = f'SELECT * FROM "{measurement}" ORDER BY time {order} LIMIT 1'
    try:
        result = client.query(query)
        if result:
            points = list(result.get_points())
            if points:
                # Normalize the timestamp
                datetime_str = parse(points[0]["time"]).strftime("%Y-%m-%dT%H:%M:%SZ")
                return datetime_str
        return None
    except Exception as e:
        logger.error(f"Error getting {order} record from '{measurement}': {str(e)}")
        return None


def filter_non_numeric_values(
    point: Dict[str, Any],
    float_selector: bool
) -> Dict[str, Union[int, float, str, bool]]:
    """
    Filter fields in a data point by type.

    Args:
        point: Data point to filter
        float_selector: If True, keep only numeric fields. If False, keep non-numeric fields.

    Returns:
        Dict: Filtered fields dictionary
    """
    filtered_fields = {}
    nan_count = 0
    nan_fields = []

    if float_selector:
        # Keep only numeric fields
        for key, value in point.items():
            if value is not None and key != "time" and isinstance(value, (int, float)):
                # Skip NaN values
                if isinstance(value, float) and (math.isnan(value) or value == float('inf') or value == float('-inf')):
                    nan_count += 1
                    nan_fields.append(key)
                    logger.warning(f"\tSkipping NaN or infinite value for field '{key}' at time '{point.get('time', 'unknown')}'")
                    continue
                # Strip prefixes from query aggregation functions (mean_, last_)
                clean_key = key
                for prefix in ["mean_", "last_"]:
                    if clean_key.startswith(prefix):
                        clean_key = clean_key[len(prefix):]
                filtered_fields[clean_key] = value
    else:
        # Keep only string and boolean fields
        for key, value in point.items():
            if value is not None and key != "time" and isinstance(value, (str, bool)):
                # Strip prefixes from query aggregation functions (mean_, last_)
                clean_key = key
                for prefix in ["mean_", "last_"]:
                    if clean_key.startswith(prefix):
                        clean_key = clean_key[len(prefix):]
                filtered_fields[clean_key] = value

    # Log the results of NaN filtering
    if nan_count > 0:
        logger.info(f"\tRemoved {nan_count} NaN/infinite values for fields: {', '.join(nan_fields)}")

    return filtered_fields


def combine_records_by_time(
    points_float: List[Dict[str, Any]],
    points_no_float: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Combine records from two lists based on timestamp.

    Args:
        points_float: List of points with numeric fields
        points_no_float: List of points with non-numeric fields

    Returns:
        List: Combined points with all fields
    """
    combined_points = []

    # Convert lists to dictionaries indexed by time
    float_dict = {record["time"]: record for record in points_float}
    no_float_dict = {record["time"]: record for record in points_no_float}

    # Combine records with the same timestamp
    for time, float_record in float_dict.items():
        if time in no_float_dict:
            combined_fields = {**float_record["fields"], **no_float_dict[time]["fields"]}
        else:
            combined_fields = float_record["fields"]

        combined_record = {
            "time": time,
            "measurement": float_record["measurement"],
            "fields": combined_fields,
        }
        combined_points.append(combined_record)

    return combined_points


def build_list_points(
    result: ResultSet,
    measurement: str,
    float_selector: bool
) -> List[Dict[str, Any]]:
    """
    Build list of points from InfluxDB query result.

    Args:
        result: InfluxDB query result
        measurement: Name of the measurement
        float_selector: If True, keep only numeric fields. If False, keep non-numeric fields.

    Returns:
        List: Points with selected fields
    """
    points = []
    total_nan_count = 0
    field_counts = {}

    for _, series in result.items():
        for point in series:
            # Create point with filtered fields
            point_data = {
                "time": point["time"],
                "measurement": measurement,
                "fields": filter_non_numeric_values(point, float_selector),
            }

            # Track field names for reporting
            for field_name in point_data["fields"]:
                field_counts[field_name] = field_counts.get(field_name, 0) + 1

            # Add point only if it has fields
            if point_data["fields"]:
                points.append(point_data)

    # Log information about fields
    if field_counts:
        logger.info(f"\tFound {len(field_counts)} unique fields: {', '.join(sorted(field_counts.keys()))}")

    return points


def copy_data_since_last_entry(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    last_entry_time: str,
    measurement: str,
    group_by: str,
) -> bool:
    """
    Copy data from source to destination since the last entry.

    Args:
        source_client: Source InfluxDB client
        dest_client: Destination InfluxDB client
        last_entry_time: Timestamp of last entry in destination
        measurement: Name of the measurement
        group_by: Time grouping for query (e.g., "5m")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Query numeric and non-numeric fields separately with proper aggregation functions
        query_float = f"""
            SELECT mean(*::field) FROM "{measurement}"
            WHERE time > '{last_entry_time}'
            GROUP BY time({group_by}) fill(none)
        """

        query_no_float = f"""
            SELECT last(*::field) FROM "{measurement}"
            WHERE time > '{last_entry_time}'
            GROUP BY time({group_by}) fill(none)
        """

        # Get numeric and non-numeric data
        result_float = source_client.query(query_float)
        logger.info(f"\tRetrieved numeric data from '{measurement}' since {last_entry_time}")

        result_no_float = source_client.query(query_no_float)
        logger.info(f"\tRetrieved non-numeric data from '{measurement}' since {last_entry_time}")

        # Build points lists
        points_float = build_list_points(result_float, measurement, True)
        points_no_float = build_list_points(result_no_float, measurement, False)

        # Combine points
        points = combine_records_by_time(points_float, points_no_float)

        # Write to destination if we have points
        if points:
            # Get time range
            time_points = [p["time"] for p in points]
            min_time = min(time_points) if time_points else "unknown"
            max_time = max(time_points) if time_points else "unknown"

            # Get field statistics
            all_fields = set()
            for point in points:
                all_fields.update(point["fields"].keys())

            logger.info(f"\tWriting {len(points)} points to '{measurement}' (time range: {min_time} to {max_time})")
            logger.info(f"\tFields being written: {', '.join(sorted(all_fields))}")
            dest_client.write_points(points)
            return True
        else:
            logger.info(f"\tNo new data found for '{measurement}' since {last_entry_time}")
            return True

    except Exception as e:
        logger.error(f"\tError copying data for '{measurement}': {str(e)}")
        return False


def copy_data_with_pagination(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    first_entry_time: str,
    measurement: str,
    group_by: str,
) -> bool:
    """
    Copy data with weekly pagination to handle large datasets.

    Args:
        source_client: Source InfluxDB client
        dest_client: Destination InfluxDB client
        first_entry_time: Timestamp of first entry in source
        measurement: Name of the measurement
        group_by: Time grouping for query (e.g., "5m")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse the first entry time
        start_time = parse(first_entry_time)
        current_time = datetime.now(timezone.utc)

        # Set initial start and end times
        period_start = start_time
        period_end = period_start + timedelta(days=DAYS_OF_PAGINATION)

        # Ensure end time doesn't exceed current time
        if period_end > current_time:
            period_end = current_time

        success = True

        # Paginate through data in chunks
        while period_start < current_time:
            period_start_str = period_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            period_end_str = period_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            logger.info(f"\tCopying data for '{measurement}' from {period_start_str} to {period_end_str}")

            # Query numeric and non-numeric data separately with proper aggregation functions
            query_float = f"""
                SELECT mean(*::field) FROM "{measurement}"
                WHERE time >= '{period_start_str}' AND time < '{period_end_str}'
                GROUP BY time({group_by}) fill(none)
            """

            query_no_float = f"""
                SELECT last(*::field) FROM "{measurement}"
                WHERE time >= '{period_start_str}' AND time < '{period_end_str}'
                GROUP BY time({group_by}) fill(none)
            """

            # Get data for this period
            result_float = source_client.query(query_float)
            result_no_float = source_client.query(query_no_float)

            # Build and combine points
            points_float = build_list_points(result_float, measurement, True)
            points_no_float = build_list_points(result_no_float, measurement, False)
            points = combine_records_by_time(points_float, points_no_float)

            # Write to destination if we have points
            if points:
                # Get field statistics
                all_fields = set()
                for point in points:
                    all_fields.update(point["fields"].keys())

                logger.info(f"\tWriting {len(points)} points to '{measurement}'")
                logger.info(f"\tFields being written: {', '.join(sorted(all_fields))}")
                dest_client.write_points(points)
            else:
                logger.info(f"\tNo data found for '{measurement}' from {period_start_str} to {period_end_str}")

            # Move to next period
            period_start = period_end
            period_end = period_start + timedelta(days=DAYS_OF_PAGINATION)

            # Ensure end time doesn't exceed current time
            if period_end > current_time:
                period_end = current_time

        return success

    except Exception as e:
        logger.error(f"\tError copying data for '{measurement}' with pagination: {str(e)}")
        return False


def backup_measurement(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    measurement: str,
    group_by: str,
) -> bool:
    """
    Back up a single measurement from source to destination.

    Args:
        source_client: Source InfluxDB client
        dest_client: Destination InfluxDB client
        measurement: Name of the measurement
        group_by: Time grouping for query (e.g., "5m")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Processing measurement: '{measurement}'")

        # Check if destination already has data for this measurement
        last_entry_time = get_entry_time(dest_client, measurement, "DESC")

        if last_entry_time:
            # Incremental backup from last entry
            logger.info(f"\tFound last entry at {last_entry_time} for '{measurement}'")
            return copy_data_since_last_entry(
                source_client, dest_client, last_entry_time, measurement, group_by
            )
        else:
            # Full backup (first time)
            logger.info(f"\tNo existing data found for '{measurement}', attempting full backup")

            # Get first entry time in source
            first_entry_time = get_entry_time(source_client, measurement, "ASC")

            if not first_entry_time:
                logger.warning(f"\tNo data found in source for '{measurement}'")
                return True

            # Try direct copy first
            try:
                logger.info(f"\tAttempting direct copy for '{measurement}' from {first_entry_time}")
                return copy_data_since_last_entry(
                    source_client, dest_client, first_entry_time, measurement, group_by
                )
            except Exception as e:
                # If direct copy fails (likely due to too much data), use pagination
                logger.warning(f"\tDirect copy failed for '{measurement}', switching to pagination: {str(e)}")
                return copy_data_with_pagination(
                    source_client, dest_client, first_entry_time, measurement, group_by
                )

    except Exception as e:
        logger.error(f"Error backing up measurement '{measurement}': {str(e)}")
        return False


def get_measurements(client: InfluxDBClient, database: str) -> List[str]:
    """
    Get list of measurements in a database.

    Args:
        client: InfluxDB client
        database: Database name

    Returns:
        List: Measurement names
    """
    client.switch_database(database)
    result = client.query("SHOW MEASUREMENTS")
    measurements = []

    for point in result.get_points():
        measurements.append(point["name"])

    return measurements


def backup_database(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    source_db: str,
    dest_db: str,
    group_by: str,
) -> bool:
    """
    Back up an entire database from source to destination.

    Args:
        source_client: Source InfluxDB client
        dest_client: Destination InfluxDB client
        source_db: Source database name
        dest_db: Destination database name
        group_by: Time grouping for query (e.g., "5m")

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Backing up database '{source_db}' to '{dest_db}'")

        # Switch to source database
        source_client.switch_database(source_db)

        # Create destination database if it doesn't exist
        dest_dbs = [db["name"] for db in dest_client.get_list_database()]
        if dest_db not in dest_dbs:
            logger.info(f"Creating destination database '{dest_db}'")
            dest_client.create_database(dest_db)

        # Switch to destination database
        dest_client.switch_database(dest_db)

        # Get measurements to back up
        if MEASUREMENTS:
            db_measurements = [m for m in MEASUREMENTS if m.strip()]
            logger.info(f"Using configured measurements: {', '.join(db_measurements)}")
        else:
            db_measurements = get_measurements(source_client, source_db)
            logger.info(f"Found {len(db_measurements)} measurements in '{source_db}'")

        # Back up each measurement
        success = True
        for measurement in db_measurements:
            measurement_success = backup_measurement(
                source_client, dest_client, measurement, group_by
            )
            if not measurement_success:
                success = False

        return success

    except Exception as e:
        logger.error(f"Error backing up database '{source_db}' to '{dest_db}': {str(e)}")
        return False


def main():
    """Main backup function."""
    logger.info("Starting InfluxDB backup process")

    # Create clients
    source_client = InfluxDBClient(**get_source_client_params())
    dest_client = InfluxDBClient(**get_dest_client_params())

    # Check connections
    if not check_connection(source_client):
        logger.error("Failed to connect to source InfluxDB server")
        return False

    if not check_connection(dest_client):
        logger.error("Failed to connect to destination InfluxDB server")
        return False

    # Back up each database
    success = True
    for i, (source_db, dest_db) in enumerate(zip(SOURCE_DBS, DEST_DBS)):
        db_success = backup_database(
            source_client, dest_client, source_db, dest_db, SOURCE_GROUP_BY
        )
        if not db_success:
            success = False

    # Close connections
    source_client.close()
    dest_client.close()

    if success:
        logger.info("Backup process completed successfully\n")
    else:
        logger.warning("Backup process completed with errors\n")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
