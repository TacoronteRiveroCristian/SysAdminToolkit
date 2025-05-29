from typing import List, Tuple, Optional, Any, Dict
from sqlalchemy import text, select, func, MetaData, Table, column, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from datetime import datetime

from schemas import data_point as schemas_dp

def get_data_points(
    db: Session,
    schema_name: str,
    table_name: str,
    query_params: schemas_dp.DataQuery,
    page: int,
    page_size: int
) -> Tuple[int, List[schemas_dp.DataPoint]]:
    """
    Retrieves data from a table and formats it as a list of DataPoint objects.

    Handles column selection, time filtering, and pagination.

    :param db: SQLAlchemy session.
    :type db: Session
    :param schema_name: The name of the schema.
    :type schema_name: str
    :param table_name: The name of the table.
    :type table_name: str
    :param query_params: Query parameters for filtering and selection.
    :type query_params: schemas_dp.DataQuery
    :param page: Current page number for pagination.
    :type page: int
    :param page_size: Number of items per page for pagination.
    :type page_size: int
    :return: A tuple containing the total number of items matching the query
             (before pagination) and the list of DataPoint objects for the current page.
             Returns (-1, []) if the table is not found or a query error occurs.
    :rtype: Tuple[int, List[schemas_dp.DataPoint]]
    """
    try:
        metadata = MetaData()
        # Reflect the table to get its columns and structure
        # Using db.get_bind() for the engine connection
        reflected_table = Table(table_name, metadata, autoload_with=db.get_bind(), schema=schema_name)

        # Determine columns to select
        if query_params.columns:
            select_columns = [col for col_name in query_params.columns if (col := reflected_table.c.get(col_name)) is not None]
            if not select_columns: # If specified columns don't exist, maybe select all or error
                # For now, let's default to all if no valid columns specified, or handle error
                # raise ValueError("None of the specified columns exist in the table.")
                select_columns = list(reflected_table.c)
        else:
            select_columns = list(reflected_table.c) # Select all columns

        # Base query
        stmt = select(*select_columns)

        # Time filtering
        time_col_obj = None
        if query_params.time_column and (time_col_obj := reflected_table.c.get(query_params.time_column)) is not None:
            if query_params.start_time:
                stmt = stmt.where(time_col_obj >= query_params.start_time)
            if query_params.end_time:
                stmt = stmt.where(time_col_obj < query_params.end_time) # typically exclusive end

        # Add other filters here if query_params.filters is implemented

        # Get total count for pagination *before* applying limit/offset
        count_stmt = select(func.count()).select_from(stmt.alias())
        total_items_result = db.execute(count_stmt).scalar_one_or_none()
        total_items = total_items_result if total_items_result is not None else 0

        if total_items == 0:
            return 0, []

        # Add pagination
        stmt = stmt.limit(page_size).offset((page - 1) * page_size)

        # Order by (optional, good for consistent pagination, e.g., by primary key or time column)
        # if time_col_obj is not None:
        #     stmt = stmt.order_by(time_col_obj)
        # elif reflected_table.primary_key:
        #     stmt = stmt.order_by(*reflected_table.primary_key.columns)

        results = db.execute(stmt).mappings().all() # .mappings() gives us dict-like rows

        data_points = []
        for row_data in results:
            fields = {}
            tags = {}
            row_time = None

            for col in select_columns:
                col_name = col.name
                value = row_data.get(col_name)

                if query_params.tag_columns and col_name in query_params.tag_columns:
                    tags[col_name] = value
                else:
                    fields[col_name] = value

                if query_params.time_column and col_name == query_params.time_column and isinstance(value, datetime):
                    row_time = value

            data_points.append(
                schemas_dp.DataPoint(
                    measurement=f"{schema_name}.{table_name}", # Or just table_name
                    tags=tags if tags else None,
                    fields=fields,
                    time=row_time
                )
            )

        return total_items, data_points

    except NoSuchTableError:
        # Log: print(f"Table not found: {schema_name}.{table_name}")
        return -1, [] # Sentinel for table not found
    except SQLAlchemyError as e:
        # Log: print(f"Database error querying {schema_name}.{table_name}: {e}")
        return -1, [] # Sentinel for other DB errors
    except Exception as e:
        # Log: print(f"Unexpected error querying {schema_name}.{table_name}: {e}")
        return -1, []
