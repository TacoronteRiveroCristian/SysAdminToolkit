from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from db.session import get_db
from schemas import data_point as schemas_dp
from schemas import common as schemas_common
from crud import crud_data # We will create this CRUD module next
from core.config import settings

router = APIRouter()

@router.post(
    "/{schema_name}/{table_name}/query",
    response_model=schemas_common.PaginatedResponse[schemas_dp.DataPoint],
    # response_model_exclude_none=True # if DataPointResponse used a more complex structure
)
def query_table_data(
    schema_name: str,
    table_name: str,
    query_params: schemas_dp.DataQuery = Body(None), # Use POST with Body for complex queries
    pagination_params: schemas_common.CommonQueryParameters = Depends(),
    db: Session = Depends(get_db)
):
    """
    Query data from a specific table, formatted as InfluxDB-like data points.

    Allows specifying columns, time range, and pagination.

    :param schema_name: The name of the schema containing the table.
    :type schema_name: str
    :param table_name: The name of the table to query.
    :type table_name: str
    :param query_params: Query parameters for filtering, selecting columns, and time ranges.
    :type query_params: schemas_dp.DataQuery, optional
    :param pagination_params: Common pagination parameters (page, page_size).
    :type pagination_params: schemas_common.CommonQueryParameters
    :param db: Database session dependency.
    :type db: Session
    :return: A paginated list of data points.
    :rtype: schemas_common.PaginatedResponse[schemas_dp.DataPoint]
    :raises HTTPException: 404 if the table or schema is not found.
    """

    # Ensure query_params is not None for cleaner access
    if query_params is None:
        query_params = schemas_dp.DataQuery()

    total_items, data_points = crud_data.get_data_points(
        db=db,
        schema_name=schema_name,
        table_name=table_name,
        query_params=query_params,
        page=pagination_params.page,
        page_size=pagination_params.page_size
    )

    if total_items == -1: # Sentinel value if table not found by crud layer
        raise HTTPException(status_code=404, detail=f"Table '{schema_name}.{table_name}' not found or query failed.")

    total_pages = (total_items + pagination_params.page_size - 1) // pagination_params.page_size

    return schemas_common.PaginatedResponse[
        schemas_dp.DataPoint
    ](
        data=data_points,
        pagination=schemas_common.Pagination(
            page=pagination_params.page,
            page_size=pagination_params.page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )

# Example of how to use GET if query params are simple enough (FastAPI converts)
# @router.get(
#     "/{schema_name}/{table_name}",
#     response_model=schemas_common.PaginatedResponse[schemas_dp.DataPoint]
# )
# async def get_table_data_get(
#     schema_name: str,
#     table_name: str,
#     start_time: Optional[datetime] = Query(None, description="Start datetime for filtering (inclusive)"),
#     end_time: Optional[datetime] = Query(None, description="End datetime for filtering (exclusive)"),
#     columns: Optional[List[str]] = Query(None, description="Specific columns to retrieve"),
#     time_column: Optional[str] = Query(None, description="Name of the column to be used as the 'time' field"),
#     tag_columns: Optional[List[str]] = Query(None, description="Columns to be treated as 'tags'"),
#     pagination_params: schemas_common.CommonQueryParameters = Depends(),
#     db: Session = Depends(get_db)
# ):
#     query_args = schemas_dp.DataQuery(
#         columns=columns,
#         time_column=time_column,
#         start_time=start_time,
#         end_time=end_time,
#         tag_columns=tag_columns
#     )
#     # ... same logic as post endpoint ...
#     # This is just to show an alternative for simpler GET requests.
#     # For complex nested query params, POST with a request body is generally better.
#     pass
