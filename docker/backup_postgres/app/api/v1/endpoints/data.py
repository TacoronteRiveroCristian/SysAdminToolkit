from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session

from db.session import get_db
from schemas import data_point as schemas_dp_v1 # v1 schema
from schemas import common as schemas_common
from crud import crud_data # v1 crud logic

router = APIRouter()

@router.post(
    "/{schema_name}/{table_name}/query",
    response_model=schemas_common.PaginatedResponse[schemas_dp_v1.DataPoint],
)
def query_table_data_v1(
    schema_name: str,
    table_name: str,
    query_params: schemas_dp_v1.DataQuery = Body(None),
    pagination_params: schemas_common.CommonQueryParameters = Depends(),
    db: Session = Depends(get_db)
):
    """
    Query data from a specific table (v1 - POST).
    """
    if query_params is None:
        query_params = schemas_dp_v1.DataQuery()

    total_items, data_points = crud_data.get_data_points(
        db=db,
        schema_name=schema_name,
        table_name=table_name,
        query_params=query_params,
        page=pagination_params.page,
        page_size=pagination_params.page_size
    )

    if total_items == -1:
        raise HTTPException(status_code=404, detail=f"Table '{schema_name}.{table_name}' not found or query failed.")

    total_pages = (total_items + pagination_params.page_size - 1) // pagination_params.page_size

    return schemas_common.PaginatedResponse[schemas_dp_v1.DataPoint](
        data=data_points,
        pagination=schemas_common.Pagination(
            page=pagination_params.page,
            page_size=pagination_params.page_size,
            total_items=total_items,
            total_pages=total_pages
        )
    )
