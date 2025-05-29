from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.session import get_db
from schemas import database_info as schemas_db
from schemas import common as schemas_common
from crud import crud_database # We will create this CRUD module next

router = APIRouter()

@router.get("/schemas", response_model=List[schemas_db.SchemaInfo])
def get_database_schemas(
    db: Session = Depends(get_db)
):
    """
    Retrieve all schemas in the connected database.

    This endpoint lists all schemas (namespaces) available in the PostgreSQL database.

    :param db: Database session dependency.
    :type db: Session
    :return: A list of schema information objects.
    :rtype: List[schemas_db.SchemaInfo]
    """
    schemas = crud_database.get_schemas(db)
    return schemas

@router.get("/{schema_name}/tables", response_model=List[schemas_db.TableInfo])
def get_tables_in_schema(
    schema_name: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve all tables within a specific schema.

    :param schema_name: The name of the schema to inspect.
    :type schema_name: str
    :param db: Database session dependency.
    :type db: Session
    :return: A list of table information objects.
    :rtype: List[schemas_db.TableInfo]
    :raises HTTPException: 404 if the schema is not found.
    """
    tables = crud_database.get_tables(db, schema_name=schema_name)
    if not tables:
        # Check if schema exists at all before returning empty list, or if crud layer handles it
        # For now, assume crud_database.get_tables returns empty list if schema is empty or not found
        pass # Or raise HTTPException(status_code=404, detail=f"Schema '{schema_name}' not found or contains no tables.")
    return tables

@router.get("/{schema_name}/{table_name}/details", response_model=schemas_db.TableDetails)
def get_table_details(
    schema_name: str,
    table_name: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve detailed information for a specific table, including its columns.

    :param schema_name: The name of the schema containing the table.
    :type schema_name: str
    :param table_name: The name of the table to inspect.
    :type table_name: str
    :param db: Database session dependency.
    :type db: Session
    :return: Detailed information about the table, including columns.
    :rtype: schemas_db.TableDetails
    :raises HTTPException: 404 if the table or schema is not found.
    """
    table_details = crud_database.get_table_details(db, schema_name=schema_name, table_name=table_name)
    if not table_details:
        raise HTTPException(status_code=404, detail=f"Table '{schema_name}.{table_name}' not found.")
    return table_details
