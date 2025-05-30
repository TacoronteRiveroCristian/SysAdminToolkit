from typing import List, Dict, Any
from pydantic import BaseModel

class SchemaInfo(BaseModel):
    """
    Schema for database schema information.

    :param name: Name of the schema.
    :type name: str
    """
    name: str

class ColumnInfo(BaseModel):
    """
    Schema for table column information.

    :param name: Name of the column.
    :type name: str
    :param type: Data type of the column.
    :type type: str
    :param nullable: Whether the column is nullable.
    :type nullable: bool
    :param default: Default value of the column, if any.
    :type default: str, optional
    :param primary_key: Whether the column is part of the primary key.
    :type primary_key: bool
    """
    name: str
    type: str # Using str representation for simplicity, could be more specific
    nullable: bool
    default: str | None = None
    primary_key: bool = False
    # constraints: List[str] = [] # Could add constraints later

class TableInfo(BaseModel):
    """
    Schema for basic table information.

    :param name: Name of the table.
    :type name: str
    :param schema: Schema the table belongs to.
    :type schema: str
    """
    name: str
    schema_name: str # Renamed from schema to avoid conflict with Pydantic schema method

class TableDetails(TableInfo):
    """
    Schema for detailed table information, including columns.

    :param columns: List of columns in the table.
    :type columns: List[ColumnInfo]
    """
    columns: List[ColumnInfo]
    # row_count: int | None = None # Could be added
