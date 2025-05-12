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
from typing import Dict, List, Literal, Optional, Union, Any, Tuple

from dateutil.parser import parse
from influxdb import InfluxDBClient
from influxdb.resultset import ResultSet

from conf import (
    SOURCE_DBS,
    DEST_DBS,
    SOURCE_GROUP_BY,
    MEASUREMENTS,
    MEASUREMENTS_CONFIG,
    DAYS_OF_PAGINATION,
    logger,
    get_source_client_params,
    get_dest_client_params,
    should_include_measurement,
    should_include_field
)


def check_connection(client: InfluxDBClient) -> bool:
    """
    Verify connection to an InfluxDB client.

    :param client: InfluxDBClient instance
    :return: True if connection successful, False otherwise
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

    :param client: InfluxDBClient instance
    :param measurement: Name of the measurement
    :param order: "ASC" for first entry, "DESC" for last entry
    :return: Timestamp in format "YYYY-MM-DDThh:mm:ssZ" or None if no records
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
    measurement: str,
    float_selector: bool
) -> Dict[str, Union[int, float, str, bool]]:
    """
    Filter fields in a data point by type and configuration.

    :param point: Data point to filter
    :param measurement: Name of the measurement
    :param float_selector: If True, keep only numeric fields. If False, keep non-numeric fields
    :return: Filtered fields dictionary
    """
    filtered_fields = {}
    nan_count = 0
    nan_fields = []

    # Determine field type for configuration filtering
    field_type = "numeric" if float_selector else "string" if not float_selector else "boolean"

    for key, value in point.items():
        if value is not None and key != "time":
            # Skip fields that don't match the requested type
            if float_selector and not isinstance(value, (int, float)):
                continue
            elif not float_selector and not isinstance(value, (str, bool)):
                continue

            # For numeric types, check for NaN and infinity
            if isinstance(value, float) and (math.isnan(value) or value == float('inf') or value == float('-inf')):
                nan_count += 1
                nan_fields.append(key)
                logger.warning(f"\tSkipping NaN or infinite value for field '{key}' at time '{point.get('time', 'unknown')}'")
                continue

            # Check if field should be included based on configuration
            # For booleans, we need to figure out if it came from a boolean or string
            actual_field_type = "numeric" if isinstance(value, (int, float)) else "boolean" if isinstance(value, bool) else "string"

            # Strip prefixes from query aggregation functions (mean_, last_)
            clean_key = key
            for prefix in ["mean_", "last_"]:
                if clean_key.startswith(prefix):
                    clean_key = clean_key[len(prefix):]

            # Check if this field should be included based on configuration
            if should_include_field(measurement, clean_key, actual_field_type):
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

    :param points_float: List of points with numeric fields
    :param points_no_float: List of points with non-numeric fields
    :return: Combined points with all fields
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

    :param result: InfluxDB query result
    :param measurement: Name of the measurement
    :param float_selector: If True, keep only numeric fields. If False, keep non-numeric fields
    :return: List of prepared data points
    """
    # Initialize empty list
    points = []

    # Loop through all series in result
    try:
        for series in result.raw["series"]:
            # Extract column names
            columns = series["columns"]

            # Process each point
            for values in series["values"]:
                # Create point with all fields
                point = dict(zip(columns, values))

                # Extract time value
                time_str = point.pop("time")

                # Filter and prepare fields
                filtered_fields = filter_non_numeric_values(point, measurement, float_selector)

                # Only add points with fields
                if filtered_fields:
                    cleaned_point = {
                        "measurement": measurement,
                        "time": time_str,
                        "fields": filtered_fields,
                    }
                    points.append(cleaned_point)

    except (KeyError, AttributeError, TypeError) as e:
        logger.warning(f"\tNo valid data in query result: {str(e)}")

    logger.info(f"\tExtracted {len(points)} points from query result")
    return points


def copy_data_since_last_entry(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    last_entry_time: str,
    measurement: str,
    group_by: Optional[str] = None,
) -> bool:
    """
    Copy data since last entry time from source to destination.

    :param source_client: Source InfluxDB client
    :param dest_client: Destination InfluxDB client
    :param last_entry_time: Timestamp of last entry in destination
    :param measurement: Name of the measurement
    :param group_by: Time grouping for query (e.g., "5m"), optional
    :return: True if successful, False otherwise
    """
    try:
        # Determine if we should use GROUP BY time
        use_group_by = group_by is not None and group_by.strip() != ""

        # Build the query parts
        where_clause = f"WHERE time > '{last_entry_time}'"
        group_by_clause = f"GROUP BY time({group_by}) fill(none)" if use_group_by else ""

        # Query numeric and non-numeric fields separately
        if use_group_by:
            query_float = f"""
                SELECT mean(*::field) FROM "{measurement}"
                {where_clause}
                {group_by_clause}
            """

            query_no_float = f"""
                SELECT last(*::field) FROM "{measurement}"
                {where_clause}
                {group_by_clause}
            """
        else:
            # Without GROUP BY, just select all fields directly
            query_float = f'SELECT *::field FROM "{measurement}" {where_clause}'
            query_no_float = query_float  # Same query for both since no aggregation needed

        # Execute queries
        float_result = source_client.query(query_float)

        # For non-grouped queries, we don't need to query twice
        if use_group_by:
            no_float_result = source_client.query(query_no_float)
        else:
            no_float_result = float_result

        # Build points lists with type filtering
        logger.info("\tProcessing numeric fields...")
        points_float = build_list_points(float_result, measurement, True)

        # Only process non-numeric fields separately if using GROUP BY
        if use_group_by:
            logger.info("\tProcessing non-numeric fields...")
            points_no_float = build_list_points(no_float_result, measurement, False)
        else:
            # For non-grouped queries, we need to filter the same result differently
            logger.info("\tProcessing non-numeric fields from same result...")
            points_no_float = build_list_points(float_result, measurement, False)

        # Combine lists if we have both numeric and non-numeric data
        if points_float and points_no_float:
            logger.info("\tCombining numeric and non-numeric fields...")
            final_points = combine_records_by_time(points_float, points_no_float)
        elif points_float:
            final_points = points_float
        elif points_no_float:
            final_points = points_no_float
        else:
            logger.info("\tNo new data found since last entry")
            return True

        # Write to destination
        if final_points:
            logger.info(f"\tWriting {len(final_points)} points to destination")
            dest_client.write_points(final_points)
            logger.info(f"\tSuccessfully copied {len(final_points)} points")
            return True
        else:
            logger.info("\tNo points to write after processing")
            return True

    except Exception as e:
        logger.error(f"\tError copying data for measurement '{measurement}': {str(e)}")
        return False


def copy_data_with_pagination(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    first_entry_time: str,
    measurement: str,
    group_by: str,
) -> bool:
    """
    Copy data with pagination for large datasets.

    :param source_client: Source InfluxDB client
    :param dest_client: Destination InfluxDB client
    :param first_entry_time: Timestamp of first entry in source
    :param measurement: Name of the measurement
    :param group_by: Time grouping for query (e.g., "5m"), required for pagination
    :return: True if successful, False otherwise
    """
    try:
        # Ensure group_by is valid for pagination
        if group_by is None or (isinstance(group_by, str) and not group_by.strip()):
            logger.error(f"\tGroup by value is required for pagination but was empty or invalid: '{group_by}'")
            return False

        # Parse the first entry time
        start_time = parse(first_entry_time)

        # Get current time as end time
        end_time = datetime.now(timezone.utc)

        # Calculate time intervals for pagination
        pagination_days = DAYS_OF_PAGINATION
        current_start = start_time
        success = True

        # Process each time interval
        while current_start < end_time and success:
            # Calculate end of current interval
            current_end = current_start + timedelta(days=pagination_days)

            # Ensure we don't go beyond the end time
            if current_end > end_time:
                current_end = end_time

            # Format times for queries
            start_str = current_start.strftime("%Y-%m-%dT%H:%M:%SZ")
            end_str = current_end.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Query numeric and non-numeric fields separately with proper aggregation functions
            logger.info(f"\tQuerying data from {start_str} to {end_str}")
            query_float = f"""
                SELECT mean(*::field) FROM "{measurement}"
                WHERE time >= '{start_str}' AND time < '{end_str}'
                GROUP BY time({group_by}) fill(none)
            """

            query_no_float = f"""
                SELECT last(*::field) FROM "{measurement}"
                WHERE time >= '{start_str}' AND time < '{end_str}'
                GROUP BY time({group_by}) fill(none)
            """

            # Execute queries
            float_result = source_client.query(query_float)
            no_float_result = source_client.query(query_no_float)

            # Build points lists with type filtering
            logger.info("\tProcessing numeric fields...")
            points_float = build_list_points(float_result, measurement, True)
            logger.info("\tProcessing non-numeric fields...")
            points_no_float = build_list_points(no_float_result, measurement, False)

            # Combine lists if we have both numeric and non-numeric data
            if points_float and points_no_float:
                logger.info("\tCombining numeric and non-numeric fields...")
                final_points = combine_records_by_time(points_float, points_no_float)
            elif points_float:
                final_points = points_float
            elif points_no_float:
                final_points = points_no_float
            else:
                logger.info(f"\tNo valid points found for interval {start_str} to {end_str}")
                final_points = []

            # Write to destination
            if final_points:
                logger.info(f"\tWriting {len(final_points)} points to destination")
                dest_client.write_points(final_points)
                logger.info(f"\tSuccessfully copied {len(final_points)} points")
            else:
                logger.info("\tNo points to write after processing")

            # Update current_start for next iteration
            current_start = current_end
            logger.info(f"\tMoving to next time interval")

        return success

    except Exception as e:
        logger.error(f"\tError copying data with pagination for '{measurement}': {str(e)}")
        return False


def backup_measurement(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    measurement: str,
    group_by: Optional[str] = None,
) -> bool:
    """
    Backup a single measurement from source to destination.

    :param source_client: Source InfluxDB client
    :param dest_client: Destination InfluxDB client
    :param measurement: Name of the measurement
    :param group_by: Time grouping for query (e.g., "5m"), optional for direct copy, required for pagination
    :return: True if successful, False otherwise
    """
    logger.info(f"Processing measurement: {measurement}")

    # Check if the measurement should be included based on configuration
    if not should_include_measurement(measurement):
        logger.info(f"Skipping measurement '{measurement}' based on configuration")
        return True

    # Check for measurement-specific configuration
    if measurement in MEASUREMENTS_CONFIG:
        logger.info(f"Found specific configuration for measurement '{measurement}'")

    try:
        # Check if destination has any data for this measurement
        last_entry_time = get_entry_time(dest_client, measurement, "DESC")

        if last_entry_time:
            # Incremental backup - copy only data newer than last entry
            logger.info(f"\tFound last entry at {last_entry_time}, performing incremental backup")
            return copy_data_since_last_entry(
                source_client, dest_client, last_entry_time, measurement, group_by
            )
        else:
            # Full backup - check data volume first
            first_entry_time = get_entry_time(source_client, measurement, "ASC")
            last_entry_time = get_entry_time(source_client, measurement, "DESC")

            if not first_entry_time or not last_entry_time:
                logger.info(f"\tNo data found in source for measurement '{measurement}'")
                return True

            # Check time span
            first_datetime = parse(first_entry_time)
            last_datetime = parse(last_entry_time)
            span_days = (last_datetime - first_datetime).days

            logger.info(f"\tData spans {span_days} days from {first_entry_time} to {last_entry_time}")

            # If span is large, use pagination (which requires a group_by value)
            if span_days > DAYS_OF_PAGINATION:
                logger.info(f"\tData span > {DAYS_OF_PAGINATION} days, using pagination")

                # Pagination requires a valid group_by value
                if group_by is None or (isinstance(group_by, str) and not group_by.strip()):
                    logger.error(f"\tPagination requires a group_by value, but none was provided or it was empty")
                    return False

                return copy_data_with_pagination(
                    source_client, dest_client, first_entry_time, measurement, group_by
                )
            else:
                # Small dataset, can copy all at once without requiring group_by
                logger.info(f"\tCopying all data at once")
                return copy_data_since_last_entry(
                    source_client, dest_client, "1970-01-01T00:00:00Z", measurement, group_by
                )

    except Exception as e:
        logger.error(f"Error backing up measurement '{measurement}': {str(e)}")
        return False


def get_measurements(client: InfluxDBClient, database: str) -> List[str]:
    """
    Get list of measurements in a database.

    :param client: InfluxDBClient instance
    :param database: Name of the database
    :return: List of measurement names
    """
    client.switch_database(database)
    result = client.query("SHOW MEASUREMENTS")

    if result:
        measurements = [m["name"] for m in result.get_points()]
        logger.info(f"Found {len(measurements)} measurements in database '{database}'")

        # Filter measurements based on configuration
        filtered = []
        for measurement in measurements:
            if should_include_measurement(measurement):
                filtered.append(measurement)
            else:
                logger.info(f"Excluding measurement '{measurement}' based on configuration")

        logger.info(f"After filtering: {len(filtered)} measurements will be backed up")
        return filtered
    else:
        logger.warning(f"No measurements found in database '{database}'")
        return []


def backup_database(
    source_client: InfluxDBClient,
    dest_client: InfluxDBClient,
    source_db: str,
    dest_db: str,
    group_by: Optional[str] = None,
) -> bool:
    """
    Backup an entire database from source to destination.

    :param source_client: Source InfluxDB client
    :param dest_client: Destination InfluxDB client
    :param source_db: Source database name
    :param dest_db: Destination database name
    :param group_by: Time grouping for query (e.g., "5m"), optional for direct copy, required for pagination
    :return: True if successful, False otherwise
    """
    # Connect to source and destination
    source_client.switch_database(source_db)

    # Create destination database if it doesn't exist
    if dest_db not in dest_client.get_list_database():
        logger.info(f"Creating database '{dest_db}' in destination")
        dest_client.create_database(dest_db)

    dest_client.switch_database(dest_db)

    # Get list of measurements
    measurements = get_measurements(source_client, source_db)

    # Backup each measurement
    success = True
    errors = []

    for measurement in measurements:
        logger.info(f"Backing up '{source_db}.{measurement}' to '{dest_db}.{measurement}'")
        if not backup_measurement(source_client, dest_client, measurement, group_by):
            logger.error(f"Failed to backup measurement '{measurement}'")
            success = False
            errors.append(measurement)

    # Report results
    if success:
        logger.info(f"Successfully backed up database '{source_db}' to '{dest_db}'")
    else:
        logger.warning(f"Backup completed with errors for {len(errors)} measurements")
        logger.warning(f"Problematic measurements: {', '.join(errors)}")

    return success


def main():
    """
    Main entry point for the backup script.

    Connects to source and destination InfluxDB servers and performs the backup.
    """
    logger.info("Starting InfluxDB backup")

    # Create source client
    source_params = get_source_client_params()
    source_url = f"{source_params['host']}:{source_params['port']}"
    logger.info(f"Connecting to source InfluxDB at {source_url}")
    source_client = InfluxDBClient(**source_params)

    # Create destination client
    dest_params = get_dest_client_params()
    dest_url = f"{dest_params['host']}:{dest_params['port']}"
    logger.info(f"Connecting to destination InfluxDB at {dest_url}")
    dest_client = InfluxDBClient(**dest_params)

    # Check connections
    if not check_connection(source_client) or not check_connection(dest_client):
        logger.error("Connection check failed, aborting")
        sys.exit(1)

    # Process each database
    success = True
    for i, source_db in enumerate(SOURCE_DBS):
        dest_db = DEST_DBS[i]
        logger.info(f"Processing database: {source_db} -> {dest_db}")

        if not backup_database(source_client, dest_client, source_db, dest_db, SOURCE_GROUP_BY):
            logger.error(f"Failed to backup database '{source_db}'")
            success = False

    # Close connections
    source_client.close()
    dest_client.close()

    # Report final status
    if success:
        logger.info("Backup completed successfully\n")
        sys.exit(0)
    else:
        logger.warning("Backup completed with errors\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
