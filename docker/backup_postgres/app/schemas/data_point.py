from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DataPoint(BaseModel):
    """
    Schema for a single data point, similar to InfluxDB line protocol (v1).
    """
    measurement: str
    tags: Optional[Dict[str, Any]] = None
    fields: Dict[str, Any]
    time: Optional[datetime] = None

class DataQuery(BaseModel):
    """
    Query parameters for fetching data points from a table (v1).
    """
    columns: Optional[List[str]] = None
    time_column: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    tag_columns: Optional[List[str]] = None

class DataPointResponse(BaseModel):
    """
    Response schema for a list of data points (v1).
    """
    points: List[DataPoint]
