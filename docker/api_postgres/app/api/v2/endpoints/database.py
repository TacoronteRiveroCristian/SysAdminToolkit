from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
# Reusing v1 schemas as they are suitable
from schemas import database_info as schemas_db
from crud import crud_database

router = APIRouter()

@router.get("/schemas", response_model=List[schemas_db.SchemaInfo])
def get_database_schemas_v2(db: Session = Depends(get_db)):
    """
    Retrieve all schemas in the connected database (v2).

    :param db: Database session dependency.
    :type db: Session
    :return: A list of schema information objects.
    :rtype: List[schemas_db.SchemaInfo]
    """
    schemas = crud_database.get_schemas(db)
    return schemas

@router.get("/{schema_name}/tables", response_model=List[schemas_db.TableInfo])
def get_tables_in_schema_v2(schema_name: str, db: Session = Depends(get_db)):
    """
    Retrieve all tables within a specific schema (v2).

    :param schema_name: The name of the schema to inspect.
    :type schema_name: str
    :param db: Database session dependency.
    :type db: Session
    :return: A list of table information objects.
    :rtype: List[schemas_db.TableInfo]
    """
    tables = crud_database.get_tables(db, schema_name=schema_name)
    if not tables and not crud_database.get_schemas(db): # Basic check if schema might not exist
        # A more robust check would be to see if the schema_name is in get_schemas(db)
        # For now, if tables list is empty, it could be schema not found or schema is empty.
        # Client might need to handle empty list appropriately.
        pass
    return tables

@router.get("/{schema_name}/{table_name}/details", response_model=schemas_db.TableDetails)
def get_table_details_v2(schema_name: str, table_name: str, db: Session = Depends(get_db)):
    """
    Retrieve detailed information for a specific table, including columns (v2).

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
