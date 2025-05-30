from typing import List, Tuple, Optional, Any, Dict
from sqlalchemy import select, func, MetaData, Table
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from datetime import datetime

from schemas.v2 import data_point as schemas_dp_v2 # Import v2 schemas

def get_data_points_v2(
    db: Session,
    schema_name: str,
    table_name: str,
    query_params: schemas_dp_v2.V2DataQuery,
    page: int,
    page_size: int
) -> Tuple[int, List[schemas_dp_v2.V2DataPoint]]:
    """
    Retrieves data from a table and formats it as a list of V2DataPoint objects (v2 format).
    Each V2DataPoint represents a single variable from a row.

    :param db: SQLAlchemy session.
    :param schema_name: The name of the schema.
    :param table_name: The name of the table.
    :param query_params: Query parameters for filtering and selection (V2DataQuery).
    :param page: Current page number for pagination.
    :param page_size: Number of items per page for pagination.
    :return: A tuple containing the total number of *rows* matching the query
             (before pagination) and the list of V2DataPoint objects for the current page.
             Returns (-1, []) if the table is not found or a query error occurs.
    :rtype: Tuple[int, List[schemas_dp_v2.V2DataPoint]]
    """
    try:
        metadata = MetaData()
        reflected_table = Table(table_name, metadata, autoload_with=db.get_bind(), schema=schema_name)

        # Determine columns to select for data fields (variables)
        data_columns_to_select = []
        if query_params.columns:
            for col_name in query_params.columns:
                if (col := reflected_table.c.get(col_name)) is not None:
                    data_columns_to_select.append(col)
            if not data_columns_to_select: # If specified columns don't exist, default to all non-tag, non-time columns
                pass # Handled below by iterating all columns

        # Always include time_column and tag_columns in the initial DB query if specified
        db_query_columns = set(data_columns_to_select) # Use set for efficient add/lookup
        if query_params.time_column and (tc := reflected_table.c.get(query_params.time_column)) is not None:
            db_query_columns.add(tc)
        if query_params.tag_columns:
            for tag_col_name in query_params.tag_columns:
                if (tag_c := reflected_table.c.get(tag_col_name)) is not None:
                    db_query_columns.add(tag_c)

        if not db_query_columns: # If still no columns (e.g. bad inputs), select all
             db_query_columns = list(reflected_table.c)
        else:
             db_query_columns = list(db_query_columns)

        # Base query
        stmt = select(*db_query_columns)

        # Time filtering
        time_col_obj = None
        if query_params.time_column and (time_col_obj := reflected_table.c.get(query_params.time_column)) is not None:
            if query_params.start_time:
                stmt = stmt.where(time_col_obj >= query_params.start_time)
            if query_params.end_time:
                stmt = stmt.where(time_col_obj < query_params.end_time)

        # Get total count of *rows* for pagination
        count_stmt = select(func.count()).select_from(stmt.alias())
        total_rows = db.execute(count_stmt).scalar_one_or_none() or 0

        if total_rows == 0:
            return 0, []

        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        # Optional: Order by time column or PK for consistent pagination
        # if time_col_obj is not None: stmt = stmt.order_by(time_col_obj)
        # elif reflected_table.primary_key: stmt = stmt.order_by(*reflected_table.primary_key.columns)

        db_results = db.execute(stmt).mappings().all()

        output_data_points = []
        measurement_name = f"{schema_name}.{table_name}"

        for row_data in db_results:
            row_time_value = None
            if query_params.time_column and (time_col_obj_name := getattr(time_col_obj, 'name', None)):
                row_time_value = row_data.get(time_col_obj_name)
                if not isinstance(row_time_value, datetime):
                    row_time_value = None # Ensure it's a datetime object or None

            current_row_tags = {}
            if query_params.tag_columns:
                for tag_col_name in query_params.tag_columns:
                    if tag_col_name in row_data and row_data[tag_col_name] is not None:
                         current_row_tags[tag_col_name] = row_data[tag_col_name]

            columns_for_variables = data_columns_to_select if data_columns_to_select else reflected_table.c
            for col_obj in columns_for_variables:
                col_name = col_obj.name
                # Skip if this column was designated as time or a tag column
                if query_params.time_column and col_name == query_params.time_column: continue
                if query_params.tag_columns and col_name in query_params.tag_columns: continue

                if col_name in row_data: # Ensure column was actually selected
                    output_data_points.append(
                        schemas_dp_v2.V2DataPoint(
                            measurement=measurement_name,
                            time=row_time_value,
                            tags=current_row_tags if current_row_tags else None,
                            variable=col_name,
                            value=row_data[col_name]
                        )
                    )

        # Note: total_items for pagination refers to the number of V2DataPoint objects, not rows.
        # This can be complex if page_size is small and rows have many variables.
        # For simplicity here, total_items for pagination is based on rows, but the returned list might be longer.
        # A more accurate total_items for V2DataPoints would require counting after transformation, or estimating.
        # Let's return total_rows for now and the client can see len(output_data_points) for the current page's item count.
        return total_rows, output_data_points

    except NoSuchTableError:
        return -1, []
    except SQLAlchemyError as e:
        return -1, []
    except Exception as e:
        return -1, []
