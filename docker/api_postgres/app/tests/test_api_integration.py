import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

# Adjust the import path according to your project structure
# This assumes main.py is in app/ and tests/ is a sibling to core/, api/, etc.
from main import app  # Your FastAPI application instance
from tests.db_setup_utils import setup_test_database, clear_all_data, get_db_session, engine
from core.config import settings # To check active API version

# Initialize TestClient
client = TestClient(app)

# Database session for direct checks if needed, though API testing is primary
TestingSessionLocal = Session(bind=engine)

@pytest.fixture(scope="session", autouse=True)
def manage_test_database():
    """
    Fixture to set up the test database before any tests run,
    and clean it up afterwards.
    """
    print("Setting up test database for the session...")
    # Clear any old data first to ensure a clean state, especially if previous runs failed
    clear_all_data() # This will also recreate public schema
    setup_test_database()
    print("Test database setup complete.")

    yield # This is where the testing happens

    print("Clearing test database after session...")
    clear_all_data()
    print("Test database cleared.")

# Helper to check if V2 is active, tests will be skipped otherwise
def is_v2_active():
    return "v2" in settings.ACTIVE_API_VERSIONS

# --- Test V2 Database Introspection Endpoints ---

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_list_schemas():
    response = client.get(f"{settings.API_V2_STR}/db-info/schemas")
    assert response.status_code == 200
    data = response.json()
    assert "schemas" in data
    schema_names = [s["schema_name"] for s in data["schemas"]]
    assert "test_schema_alpha" in schema_names
    assert "test_schema_beta" in schema_names
    assert "public" in schema_names # public should also be listed

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_list_tables_in_schema():
    schema_name = "test_schema_alpha"
    response = client.get(f"{settings.API_V2_STR}/db-info/schemas/{schema_name}/tables")
    assert response.status_code == 200
    data = response.json()
    assert "tables" in data
    table_names = [t["table_name"] for t in data["tables"]]
    assert "inventory" in table_names
    assert "sensor_readings" in table_names

    schema_name_beta = "test_schema_beta"
    response_beta = client.get(f"{settings.API_V2_STR}/db-info/schemas/{schema_name_beta}/tables")
    assert response_beta.status_code == 200
    data_beta = response_beta.json()
    table_names_beta = [t["table_name"] for t in data_beta["tables"]]
    assert "user_profiles" in table_names_beta
    assert "empty_table" in table_names_beta


@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_get_table_columns():
    schema_name = "test_schema_alpha"
    table_name = "inventory"
    response = client.get(f"{settings.API_V2_STR}/db-info/schemas/{schema_name}/tables/{table_name}/columns")
    assert response.status_code == 200
    data = response.json()
    assert "columns" in data
    column_details = {c["column_name"]: c["data_type"] for c in data["columns"]}

    assert "item_id" in column_details
    assert column_details["item_id"] == "integer" # Example, adjust based on your actual type mapping

    assert "item_name" in column_details
    assert column_details["item_name"] == "text"

    assert "price" in column_details
    assert column_details["price"] == "numeric"

    assert "last_updated" in column_details
    # The exact string for timestamp with time zone might vary based on SQLAlchemy/DB driver
    assert "timestamp with time zone" in column_details["last_updated"].lower()

    assert "tags" in column_details
    assert column_details["tags"] == "_text" # For TEXT[]

    assert "specs" in column_details
    assert column_details["specs"] == "jsonb"

    assert "is_active" in column_details
    assert column_details["is_active"] == "boolean"


@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_get_columns_for_nonexistent_table():
    response = client.get(f"{settings.API_V2_STR}/db-info/schemas/test_schema_alpha/tables/nonexistent_table/columns")
    assert response.status_code == 404 # Assuming 404 for not found


# --- Test V2 Data Extraction Endpoint ---

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_basic():
    schema_name = "test_schema_alpha"
    table_name = "sensor_readings"
    # Query for device_id and temperature from sensor_readings
    # Ensure your timestamp column for this table is named 'ts'
    response = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={"columns": ["device_id", "temperature", "ts"], "time_column": "ts"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0  # We inserted 4 records

    # Check structure of the first data point
    point = data["data"][0]
    assert "timestamp" in point
    assert "measurement" in point
    assert point["measurement"] == table_name # Default measurement name
    assert "tags" in point # Should be empty if no tag_columns specified
    assert isinstance(point["tags"], dict)
    assert "fields" in point
    assert "device_id" in point["fields"]
    assert "temperature" in point["fields"]
    assert "ts" not in point["fields"] # time_column should be in timestamp, not fields

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_with_tags():
    schema_name = "test_schema_alpha"
    table_name = "sensor_readings"
    response = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={
            "columns": ["temperature", "humidity"],
            "time_column": "ts",
            "tag_columns": ["device_id"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert len(data["data"]) > 0

    for point in data["data"]:
        assert "device_id" in point["tags"]
        assert point["tags"]["device_id"] in ["device001", "device002"]
        assert "temperature" in point["fields"]
        assert "humidity" in point["fields"]

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_pagination():
    schema_name = "test_schema_alpha"
    table_name = "sensor_readings"

    # Get first page, 2 items
    response1 = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={"columns": ["temperature"], "time_column": "ts", "page": 1, "page_size": 2}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    assert "data" in data1
    assert len(data1["data"]) == 2
    assert "pagination" in data1
    assert data1["pagination"]["page"] == 1
    assert data1["pagination"]["page_size"] == 2
    assert data1["pagination"]["total_items"] == 4 # Total sensor readings inserted
    assert data1["pagination"]["total_pages"] == 2

    # Get second page, 2 items
    response2 = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={"columns": ["temperature"], "time_column": "ts", "page": 2, "page_size": 2}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert len(data2["data"]) == 2
    assert data2["pagination"]["page"] == 2

    # Ensure data is different (assuming an order, e.g., by time or primary key)
    assert data1["data"][0]["fields"]["temperature"] != data2["data"][0]["fields"]["temperature"] # Basic check


@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_time_filter():
    schema_name = "test_schema_alpha"
    table_name = "sensor_readings"

    # Data was inserted around 2023-03-01 10:00:00 to 10:10:00 UTC
    start_time_str = datetime(2023, 3, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    end_time_str = datetime(2023, 3, 1, 10, 6, 0, tzinfo=timezone.utc).isoformat() # Up to 10:05 included

    response = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={
            "columns": ["temperature"],
            "time_column": "ts",
            "start_time": start_time_str,
            "end_time": end_time_str
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    # Should be 3 records: device001 at 10:00, device002 at 10:00, device001 at 10:05
    assert len(data["data"]) == 3
    for point in data["data"]:
        point_ts = datetime.fromisoformat(point["timestamp"])
        assert datetime.fromisoformat(start_time_str) <= point_ts <= datetime.fromisoformat(end_time_str)

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_custom_measurement_name():
    schema_name = "test_schema_alpha"
    table_name = "inventory"
    custom_name = "my_custom_inventory"
    response = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={
            "columns": ["item_name", "quantity"],
            "time_column": "last_updated", # Assuming 'last_updated' is the time column for inventory
            "measurement_name": custom_name
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) > 0
    assert data["data"][0]["measurement"] == custom_name

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_from_empty_table():
    schema_name = "test_schema_beta"
    table_name = "empty_table" # This table was created but has no data
     # It needs a time column to be queryable by the data endpoint, let's assume it might not have one.
    # The endpoint might return 400 if time_column is mandatory and not found, or 0 items.
    # For this test, let's assume we try to query without a time_column (if allowed by schema)
    # or with a dummy one if required.
    # Let's first get its columns to see if there's a time-like column
    cols_response = client.get(f"{settings.API_V2_STR}/db-info/schemas/{schema_name}/tables/{table_name}/columns")
    assert cols_response.status_code == 200
    # Based on db_setup_utils, empty_table has (id INT, description TEXT), no time column.
    # The V2 data query endpoint *requires* a time_column. So this should fail or be handled.

    # Attempting to query data without a valid time_column should ideally result in a specific error
    # or an empty list if the table is simply empty but schema matches.
    # Given the current design, time_column is mandatory in the V2 query.
    response = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={"columns": ["id", "description"], "time_column": "id"} # Using 'id' as a dummy time_column
    )
    # What to expect? If 'id' is not a time type, crud logic might fail.
    # If the table is empty, data list will be empty.
    # The crud_data_v2.py tries to cast time_column to DateTime.
    # If 'id' (an INT) cannot be cast, it might raise an internal server error, or a validation error.
    # Let's assume it returns empty data if the query executes but finds nothing,
    # or a 400/422 if query params are invalid for the table.

    # Given the types, using 'id' (INT) as time_column will likely lead to a DB error during query by crud_data_v2.
    # This could be a 500, or if there's validation, a 4xx.
    # For now, let's assert it doesn't crash with 200 and empty data, and refine later if needed.
    if response.status_code == 200: # If query succeeds despite type mismatch (unlikely with strict DBs)
        data = response.json()
        assert "data" in data
        assert len(data["data"]) == 0
    else:
        # More likely to be a 400 Bad Request or 422 Unprocessable Entity if the time_column type is validated,
        # or 500 if the DB query fails due to type mismatch.
        assert response.status_code in [400, 422, 404, 500] # 404 if table/schema not found by endpoint logic
        # If it's a 404 because the data query logic itself can't find it (e.g. no time column).
        # If it's a 400/422 because 'id' is not a valid time_column type.
        # If it's a 500 because the SQL query fails.
        # For test_schema_beta.empty_table, it has (id INT, description TEXT).
        # crud_data_v2.py will try to filter by time_column. Using 'id' (INT) for this will cause
        # a database error when trying to compare an INT column with a timestamp range.
        # FastAPI/Starlette usually catches DB errors from SQLAlchemy and returns 500.
        print(f"Response for empty_table with int as time_column: {response.status_code}, {response.text}")
        assert response.status_code == 500 # Expecting internal server error due to type mismatch in query

@pytest.mark.skipif(not is_v2_active(), reason="V2 API not active in current configuration")
def test_v2_query_data_invalid_column_name():
    schema_name = "test_schema_alpha"
    table_name = "sensor_readings"
    response = client.get(
        f"{settings.API_V2_STR}/data/{schema_name}/{table_name}/query",
        params={"columns": ["temperature", "non_existent_column"], "time_column": "ts"}
    )
    # Depending on implementation, this might be a 400 (bad request, column not found by API)
    # or 500 (if DB query fails). FastAPI typically converts DB errors to 500.
    # crud_data_v2.py currently doesn't validate column existence before querying.
    assert response.status_code == 500 # Expecting DB error due to non-existent column

# TODO: Add tests for V1 if it's made active for testing purposes
# def is_v1_active():
#     return "v1" in settings.ACTIVE_API_VERSIONS

# @pytest.mark.skipif(not is_v1_active(), reason="V1 API not active")
# def test_v1_list_schemas():
#     pass # etc.
