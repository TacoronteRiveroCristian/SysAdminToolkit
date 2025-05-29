from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from schemas.v2 import data_point as schemas_dp_v2 # v2 schemas
from schemas import common as schemas_common # Reusable common schemas
from crud import crud_data_v2 # v2 CRUD function
from core.config import settings

router = APIRouter()

@router.get(
    "/{schema_name}/{table_name}/query",
    response_model=schemas_common.PaginatedResponse[schemas_dp_v2.V2DataPoint]
)
def query_table_data_v2(
    schema_name: str,
    table_name: str,
    # Query parameters for V2DataQuery, FastAPI will populate these from URL
    columns: Optional[List[str]] = Query(None, description="Specific columns (variables) to retrieve. All if omitted."),
    time_column: Optional[str] = Query(None, description="Name of the column to be used as the 'time' field."),
    start_time: Optional[datetime] = Query(None, description="Start datetime for filtering (inclusive). ISO format."),
    end_time: Optional[datetime] = Query(None, description="End datetime for filtering (exclusive). ISO format."),
    tag_columns: Optional[List[str]] = Query(None, description="Columns to be treated as 'tags'."),

    pagination_params: schemas_common.CommonQueryParameters = Depends(),
    db: Session = Depends(get_db)
):
    """
    Query data from a specific table (v2 - GET).
    Data is returned as a list of dictionaries, each representing a variable at a time.

    :param schema_name: The name of the schema.
    :param table_name: The name of the table.
    :param columns: Specific columns (variables) to retrieve.
    :param time_column: Name of the timestamp column.
    :param start_time: Start filter for time_column.
    :param end_time: End filter for time_column.
    :param tag_columns: Columns to include as tags in each data point.
    :param pagination_params: Pagination (page, page_size).
    :param db: Database session.
    :return: Paginated list of V2DataPoint objects.
    :rtype: schemas_common.PaginatedResponse[schemas_dp_v2.V2DataPoint]
    """
    v2_query_params = schemas_dp_v2.V2DataQuery(
        columns=columns,
        time_column=time_column,
        start_time=start_time,
        end_time=end_time,
        tag_columns=tag_columns
    )

    total_rows, data_points = crud_data_v2.get_data_points_v2(
        db=db,
        schema_name=schema_name,
        table_name=table_name,
        query_params=v2_query_params,
        page=pagination_params.page,
        page_size=pagination_params.page_size
    )

    if total_rows == -1: # Sentinel for table not found or error
        raise HTTPException(status_code=404, detail=f"Table '{schema_name}.{table_name}' not found or query failed.")

    # As noted in crud_data_v2, total_rows refers to DB rows.
    # The actual number of V2DataPoint items might be different.
    # total_pages calculation here is based on total_rows.
    total_pages = (total_rows + pagination_params.page_size - 1) // pagination_params.page_size
    if total_rows == 0: # if total_rows is 0, total_pages should be 0 or 1 depending on preference for empty state.
        total_pages = 0

    return schemas_common.PaginatedResponse[schemas_dp_v2.V2DataPoint](
        data=data_points,
        pagination=schemas_common.Pagination(
            page=pagination_params.page,
            page_size=pagination_params.page_size, # This is page_size in terms of rows from DB
            total_items=total_rows, # This is total rows from DB
            total_pages=total_pages
        )
    )
