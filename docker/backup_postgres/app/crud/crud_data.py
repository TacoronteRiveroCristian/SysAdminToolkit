from typing import List, Tuple, Optional, Any, Dict
from sqlalchemy import text, select, func, MetaData, Table, column, inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError
from datetime import datetime

from schemas import data_point as schemas_dp_v1 # v1 schema

def get_data_points(
    db: Session,
    schema_name: str,
    table_name: str,
    query_params: schemas_dp_v1.DataQuery,
    page: int,
    page_size: int
) -> Tuple[int, List[schemas_dp_v1.DataPoint]]:
    """
    Retrieves data from a table and formats it as a list of DataPoint objects (v1).
    """
    try:
        metadata = MetaData()
        reflected_table = Table(table_name, metadata, autoload_with=db.get_bind(), schema=schema_name)
        select_columns_obj = list(reflected_table.c)
        if query_params.columns:
            select_columns_obj = [col for col_name in query_params.columns if (col := reflected_table.c.get(col_name)) is not None]
            if not select_columns_obj:
                select_columns_obj = list(reflected_table.c)

        stmt = select(*select_columns_obj)
        time_col_obj = None
        if query_params.time_column and (time_col_obj := reflected_table.c.get(query_params.time_column)) is not None:
            if query_params.start_time:
                stmt = stmt.where(time_col_obj >= query_params.start_time)
            if query_params.end_time:
                stmt = stmt.where(time_col_obj < query_params.end_time)

        count_stmt = select(func.count()).select_from(stmt.alias())
        total_items = db.execute(count_stmt).scalar_one_or_none() or 0

        if total_items == 0:
            return 0, []

        stmt = stmt.limit(page_size).offset((page - 1) * page_size)
        results = db.execute(stmt).mappings().all()
        data_points_list = []
        for row_data in results:
            fields, tags, row_time = {}, {}, None
            for col in select_columns_obj:
                col_name, value = col.name, row_data.get(col.name)
                if query_params.tag_columns and col_name in query_params.tag_columns:
                    tags[col_name] = value
                else:
                    fields[col_name] = value
                if query_params.time_column and col_name == query_params.time_column and isinstance(value, datetime):
                    row_time = value
            data_points_list.append(
                schemas_dp_v1.DataPoint(
                    measurement=f"{schema_name}.{table_name}",
                    tags=tags if tags else None,
                    fields=fields,
                    time=row_time
                )
            )
        return total_items, data_points_list
    except (NoSuchTableError, SQLAlchemyError):
        return -1, []
    except Exception:
        return -1, []
