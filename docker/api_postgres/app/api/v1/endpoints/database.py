from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from schemas import database_info as schemas_db
from schemas import common as schemas_common
from crud import crud_database

router = APIRouter()

@router.get("/schemas", response_model=List[schemas_db.SchemaInfo])
def get_database_schemas(
    db: Session = Depends(get_db)
):
    """
    Retrieve all schemas in the connected database (v1).
    """
    schemas = crud_database.get_schemas(db)
    return schemas

@router.get("/{schema_name}/tables", response_model=List[schemas_db.TableInfo])
def get_tables_in_schema(
    schema_name: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve all tables within a specific schema (v1).
    """
    tables = crud_database.get_tables(db, schema_name=schema_name)
    return tables

@router.get("/{schema_name}/{table_name}/details", response_model=schemas_db.TableDetails)
def get_table_details(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed information for a specific table (v1).
    """
    table_details = crud_database.get_table_details(db, schema_name=schema_name, table_name=table_name)
    if not table_details:
        raise HTTPException(status_code=404, detail=f"Table '{schema_name}.{table_name}' not found.")
    return table_details
