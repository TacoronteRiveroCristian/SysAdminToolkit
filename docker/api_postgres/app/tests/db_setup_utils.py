import sqlalchemy
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import ProgrammingError
from datetime import datetime, timezone
import json

# This would ideally come from a test-specific configuration or environment variables
# For simplicity here, we hardcode it but point to the same DB used by the app.
# Ensure your .env file has the correct DATABASE_URL for the main app.
# The test runner will typically be in an environment where these are set.
from core.config import settings # Assuming tests can access app's core.config

DATABASE_URL_FOR_TESTS = settings.sqlalchemy_database_url

engine = create_engine(DATABASE_URL_FOR_TESTS)
SessionLocalTest = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocalTest()
    try:
        yield db
    finally:
        db.close()

def clear_all_data():
    """Drops all public and test schemas to ensure a clean slate. Be careful!"""
    db = next(get_db_session())
    inspector = inspect(engine)
    schemas_to_drop = [s_name for s_name in inspector.get_schema_names() if s_name.startswith('test_') or s_name == 'public']

    try:
        for schema_name in schemas_to_drop:
            print(f"Attempting to drop schema: {schema_name}")
            db.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE;'))
            if schema_name == 'public': # Recreate public schema if dropped
                db.execute(text('CREATE SCHEMA "public";'))
        db.commit()
        print("Cleared existing test data and relevant schemas.")
    except ProgrammingError as e:
        db.rollback()
        print(f"Error during clearing data (might be normal if schemas didn't exist or due to dependencies): {e}")
    except Exception as e:
        db.rollback()
        print(f"Unexpected error during clearing data: {e}")
    finally:
        db.close()

def setup_test_database():
    """Creates test schemas, tables, and populates them with diverse data."""
    db = next(get_db_session())

    # JSON payloads prepared using json.dumps for safety and correctness
    inv_spec1_json = json.dumps({"cpu": "i7", "ram_gb": 16, "ssd_gb": 512})
    inv_spec2_json = json.dumps({"dpi": 1600, "buttons": 3})
    inv_spec3_json = json.dumps({"switches": "blue", "layout": "104-key"})

    sensor_meta1_json = json.dumps({"location": "room_a", "battery_level": 0.8})
    sensor_meta2_json = json.dumps({"location": "room_b"})
    sensor_meta4_json = json.dumps({"status": "calibrating"})

    user_pref1_json = json.dumps({"theme": "dark", "notifications": True})
    user_pref2_json = json.dumps({"theme": "light", "notifications": False, "language": "es"})

    schemas_and_tables = {
        "test_schema_alpha": {
            "inventory": [
                "CREATE TABLE test_schema_alpha.inventory ("
                "  item_id SERIAL PRIMARY KEY,"
                "  item_name TEXT NOT NULL UNIQUE,"
                "  quantity INTEGER DEFAULT 0 CHECK (quantity >= 0),"
                "  price NUMERIC(10, 2),"
                "  last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,"
                "  tags TEXT[],"
                "  specs JSONB,"
                "  is_active BOOLEAN DEFAULT TRUE"
                ");",
                f"INSERT INTO test_schema_alpha.inventory (item_name, quantity, price, last_updated, tags, specs, is_active) VALUES "
                f"('Laptop Pro', 10, 1200.50, '2023-01-15 10:00:00 UTC', ARRAY['electronics', 'computer'], '{inv_spec1_json}'::jsonb, TRUE),"
                f"('Wireless Mouse', 150, 25.99, '2023-01-20 14:30:00 UTC', ARRAY['electronics', 'accessory'], '{inv_spec2_json}'::jsonb, TRUE),"
                f"('Mechanical Keyboard', 50, 75.00, '2023-02-01 09:15:00 UTC', ARRAY['electronics', 'accessory', 'gaming'], '{inv_spec3_json}'::jsonb, FALSE),"
                f"('USB-C Hub', 75, 39.99, NOW() - INTERVAL '1 day', ARRAY['accessory', 'adapter'], NULL, TRUE);"
            ],
            "sensor_readings": [
                "CREATE TABLE test_schema_alpha.sensor_readings ("
                "  reading_id BIGSERIAL PRIMARY KEY,"
                "  device_id VARCHAR(50) NOT NULL,"
                "  ts TIMESTAMP WITH TIME ZONE NOT NULL,"
                "  temperature FLOAT,"
                "  humidity FLOAT,"
                "  pressure_hpa DOUBLE PRECISION,"
                "  metadata JSON"
                ");",
                "CREATE INDEX idx_sensor_ts ON test_schema_alpha.sensor_readings (ts DESC);",
                "CREATE INDEX idx_sensor_device_ts ON test_schema_alpha.sensor_readings (device_id, ts DESC);",
                f"INSERT INTO test_schema_alpha.sensor_readings (device_id, ts, temperature, humidity, pressure_hpa, metadata) VALUES "
                f"('device001', '{datetime(2023, 3, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()}', 22.5, 45.2, 1012.5, '{sensor_meta1_json}'::json),"
                f"('device002', '{datetime(2023, 3, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()}', 25.1, 50.0, 1010.1, '{sensor_meta2_json}'::json),"
                f"('device001', '{datetime(2023, 3, 1, 10, 5, 0, tzinfo=timezone.utc).isoformat()}', 22.7, 45.5, 1012.6, NULL),"
                f"('device001', '{datetime(2023, 3, 1, 10, 10, 0, tzinfo=timezone.utc).isoformat()}', 22.8, 45.8, 1012.4, '{sensor_meta4_json}'::json);"
            ]
        },
        "test_schema_beta": {
            "user_profiles": [
                "CREATE TABLE test_schema_beta.user_profiles ("
                "  user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                "  username VARCHAR(255) NOT NULL UNIQUE,"
                "  email VARCHAR(255) NOT NULL UNIQUE,"
                "  created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,"
                "  preferences JSONB"
                ");",
                f"INSERT INTO test_schema_beta.user_profiles (username, email, preferences) VALUES "
                f"('johndoe', 'john.doe@example.com', '{user_pref1_json}'::jsonb),"
                f"('janeyoe', 'jane.yoe@example.com', '{user_pref2_json}'::jsonb);"
            ],
            "empty_table": [
                 "CREATE TABLE test_schema_beta.empty_table (id INT PRIMARY KEY, description TEXT);"
            ]
        }
    }

    try:
        for schema_name, tables in schemas_and_tables.items():
            print(f"Creating schema: {schema_name}")
            db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}";'))
            for table_name, ddl_statements in tables.items():
                print(f"  Creating table: {schema_name}.{table_name}")
                for stmt in ddl_statements:
                    db.execute(text(stmt))
        db.commit()
        print("Test database setup complete.")
    except ProgrammingError as e:
        db.rollback()
        print(f"Error during database setup (table/schema might already exist or other DDL issue): {e}")
    except Exception as e:
        db.rollback()
        print(f"Unexpected error during database setup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Running test database setup directly...")
    # If you want to clear before setting up:
    # print("Clearing existing data first...")
    # clear_all_data()
    # print("Done clearing.")
    setup_test_database()
    print("Script finished.")
