from typing import List, Optional, Dict, Any
from sqlalchemy import inspect, text, MetaData, Table
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from schemas import database_info as schemas_db

def get_schemas(db: Session) -> List[schemas_db.SchemaInfo]:
    """
    Retrieves a list of all schemas in the database.

    Uses SQLAlchemy inspector to get schema names, filtering out system schemas.

    :param db: SQLAlchemy session.
    :type db: Session
    :return: A list of SchemaInfo objects.
    :rtype: List[schemas_db.SchemaInfo]
    """
    inspector = inspect(db.bind)
    schema_names = inspector.get_schema_names()
    # Filter out system schemas, typically starting with 'pg_' or 'information_schema'
    # Adjust filter as necessary for other DBs or specific needs
    filtered_schemas = [
        schemas_db.SchemaInfo(name=s_name)
        for s_name in schema_names
        if not s_name.startswith("pg_") and s_name != "information_schema"
    ]
    return filtered_schemas

def get_tables(db: Session, schema_name: str) -> List[schemas_db.TableInfo]:
    """
    Retrieves a list of tables within a given schema.

    :param db: SQLAlchemy session.
    :type db: Session
    :param schema_name: The name of the schema.
    :type schema_name: str
    :return: A list of TableInfo objects.
    :rtype: List[schemas_db.TableInfo]
    """
    inspector = inspect(db.bind)
    try:
        table_names = inspector.get_table_names(schema=schema_name)
        return [schemas_db.TableInfo(name=t_name, schema_name=schema_name) for t_name in table_names]
    except SQLAlchemyError as e:
        # Log error: print(f"Error getting tables for schema {schema_name}: {e}")
        # This might happen if the schema doesn't exist, inspector might raise or return empty.
        # Depending on exact inspector behavior, might need to check if schema exists first.
        return []

def get_table_details(db: Session, schema_name: str, table_name: str) -> Optional[schemas_db.TableDetails]:
    """
    Retrieves detailed information for a specific table, including its columns.

    Uses SQLAlchemy inspector to get column details and primary key information.

    :param db: SQLAlchemy session.
    :type db: Session
    :param schema_name: The name of the schema.
    :type schema_name: str
    :param table_name: The name of the table.
    :type table_name: str
    :return: A TableDetails object if the table is found, otherwise None.
    :rtype: Optional[schemas_db.TableDetails]
    """
    inspector = inspect(db.bind)
    try:
        columns_data = inspector.get_columns(table_name, schema=schema_name)
        if not columns_data:
            return None

        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema_name)
        primary_key_columns = pk_constraint.get('constrained_columns', []) if pk_constraint else []

        columns = [
            schemas_db.ColumnInfo(
                name=col['name'],
                type=str(col['type']), # Convert SQLAlchemy type to string
                nullable=col['nullable'],
                default=col.get('default', None), # Default might not always be present
                primary_key=col['name'] in primary_key_columns
            )
            for col in columns_data
        ]
        return schemas_db.TableDetails(name=table_name, schema_name=schema_name, columns=columns)
    except NoSuchTableError:
        return None
    except SQLAlchemyError as e:
        # Log error: print(f"Error getting details for table {schema_name}.{table_name}: {e}")
        return None
