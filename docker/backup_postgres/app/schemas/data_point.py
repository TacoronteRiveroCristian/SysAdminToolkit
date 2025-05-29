from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DataPoint(BaseModel):
    """
    Schema for a single data point, similar to InfluxDB line protocol.

    Represents a single row from a table, where columns are fields and tags.
    The `measurement` will be the table name.

    :param measurement: The table name (InfluxDB measurement).
    :type measurement: str
    :param tags: Dictionary of tag key-value pairs (indexed columns).
    :type tags: Dict[str, Any], optional
    :param fields: Dictionary of field key-value pairs (non-indexed data columns).
    :type fields: Dict[str, Any]
    :param time: Timestamp for the data point (e.g., a specific datetime column from the row).
    :type time: datetime, optional
    """
    measurement: str
    tags: Optional[Dict[str, Any]] = None
    fields: Dict[str, Any]
    time: Optional[datetime] = None

class DataQuery(BaseModel):
    """
    Query parameters for fetching data points from a table.

    :param columns: Specific columns to retrieve. If None or empty, all columns are retrieved.
    :type columns: List[str], optional
    :param time_column: Name of the column to be used as the 'time' field in DataPoint.
    :type time_column: str, optional
    :param start_time: Start datetime for filtering (inclusive).
    :type start_time: datetime, optional
    :param end_time: End datetime for filtering (exclusive).
    :type end_time: datetime, optional
    :param tag_columns: Columns to be treated as 'tags' in DataPoint.
    :type tag_columns: List[str], optional
    # Add other filters as needed, e.g., specific WHERE clauses
    """
    columns: Optional[List[str]] = None
    time_column: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tag_columns: Optional[List[str]] = None
    # Add filters: Optional[Dict[str, Any]] = None for general WHERE clauses

class DataPointResponse(BaseModel):
    """
    Response schema for a list of data points.

    :param results: List of query results, each containing a list of data points.
    :type results: List[Dict[str, List[DataPoint]]]
    """
    # This structure mimics InfluxDB's response for multiple series or statements
    # For simplicity, we might just return List[DataPoint] directly or PaginatedResponse[DataPoint]
    # Option 1: Simple list of points
    # points: List[DataPoint]

    # Option 2: More InfluxDB-like (can be complex for simple cases)
    # results: List[Dict[str, Any]] # [{'statement_id': 0, 'series': [{'name': 'table_name', 'columns': ['time', 'field1'], 'values': [...]}]}]

    # For now, let's go with a simpler direct list, or paginated list. User asked for "lista de puntos"
    points: List[DataPoint]
