from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class V2DataPoint(BaseModel):
    """
    Schema for a single variable data point (v2).
    Each point represents one variable (column) from a row at a specific time.

    :param measurement: The table name (e.g., 'schema_name.table_name').
    :type measurement: str
    :param time: Timestamp for the data point.
    :type time: datetime, optional
    :param tags: Dictionary of tag key-value pairs (e.g., indexed columns or other contextual data from the row).
    :type tags: Dict[str, Any], optional
    :param variable: The name of the variable (column name).
    :type variable: str
    :param value: The value of the variable.
    :type value: Any
    """
    measurement: str
    time: Optional[datetime] = None
    tags: Optional[Dict[str, Any]] = None
    variable: str
    value: Any

class V2DataQuery(BaseModel):
    """
    Query parameters for fetching data points from a table for v2 (GET request).
    These will be translated from query parameters in the GET request.

    :param columns: Specific columns (variables) to retrieve. If None or empty, all columns are retrieved.
    :type columns: Optional[List[str]] = None
    :param time_column: Name of the column to be used as the 'time' field.
    :type time_column: Optional[str] = None
    :param start_time: Start datetime for filtering (inclusive).
    :type start_time: Optional[datetime] = None
    :param end_time: End datetime for filtering (exclusive).
    :type end_time: Optional[datetime] = None
    :param tag_columns: Columns to be treated as 'tags'. These will be included in the tags dict for each data point if their values are not None.
    :type tag_columns: Optional[List[str]] = None
    # Additional simple filters can be added as query parameters if needed.
    # Example: filter_column_name: Optional[str] = None
    """
    columns: Optional[List[str]] = None
    time_column: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tag_columns: Optional[List[str]] = None
