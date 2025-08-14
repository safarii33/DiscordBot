import os
import pandas as pd
import typing
import asyncpg
from src.db.connections import get_db_connection_pool, close_db_connection_pool
# --- Database Configuration ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


def map_pandas_dtype_to_postgres(dtype):
    """Maps Pandas data types to appropriate PostgreSQL data types."""
    if pd.api.types.is_integer_dtype(dtype):
        return "INTEGER"
    elif pd.api.types.is_float_dtype(dtype):
        return "NUMERIC" # Use NUMERIC for precision in stats
    elif pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP WITH TIME ZONE"
    else: # Default to TEXT for objects (strings) and other unhandled types
        return "TEXT"

def generate_create_table_sql(df: pd.DataFrame, table_name: str):
    """
    Generates a PostgreSQL CREATE TABLE statement from a Pandas DataFrame's schema.
    
    Args:
        df (pd.DataFrame): The DataFrame to inspect.
        table_name (str): The desired name for the SQL table.
        
    Returns:
        str: The SQL CREATE TABLE statement.
    """
    if df.empty:
        return f"CREATE TABLE IF NOT EXISTS {table_name} (id SERIAL PRIMARY KEY);" # Basic fallback

    columns_sql = []
    for col_name, dtype in df.dtypes.items():
        # Sanitize column names for SQL (replace non-alphanumeric with underscore, lowercase)
        sql_col_name = ''.join(c if c.isalnum() else '_' for c in col_name).lower()
        pg_type = map_pandas_dtype_to_postgres(dtype)
        
        # Add a NOT NULL constraint for columns that are typically always present
        # This is a heuristic; you might need to adjust based on actual data
        if sql_col_name in ['player_id', 'player_name', 'week', 'season', 'team_abbr']:
            columns_sql.append(f"    {sql_col_name} {pg_type} NOT NULL")
        else:
            columns_sql.append(f"    {sql_col_name} {pg_type}")
            
    # Add a primary key if desired, e.g., a composite key for weekly stats
    # For raw import, a simple ID might be enough, or a composite of player_id, season, week
    # Let's suggest a composite key that makes sense for weekly data.
    pk_cols = []
    if 'player_id' in df.columns: pk_cols.append('player_id')
    if 'season' in df.columns: pk_cols.append('season')
    if 'week' in df.columns: pk_cols.append('week')

    if len(pk_cols) == 3: # If we have all three, make a composite PK
        primary_key_clause = f",\n    PRIMARY KEY ({', '.join(pk_cols)})"
    else: # Fallback to a simple serial ID if composite PK not clear
        primary_key_clause = ",\n    id SERIAL PRIMARY KEY" 

    sql_statement = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
{', '.join(columns_sql)}{primary_key_clause}
)"""
    return sql_statement

async def execute_create_table_sql(sql_statement: str):
    """
    Executes a SQL CREATE TABLE statement against the PostgreSQL database.
    """
    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print("❌ Could not get a database connection pool. Aborting SQL execution.")
        return False

    async with pool.acquire() as conn:
        try:
            print("\nAttempting to execute CREATE TABLE statement...")
            await conn.execute(sql_statement)
            print("✅ CREATE TABLE statement executed successfully!")
            return True
        except asyncpg.PostgresError as e:
            print(f"❌ Database error executing CREATE TABLE statement: {e}")
            return False
        except Exception as e:
            print(f"❌ An unexpected error occurred during SQL execution: {e}")
            return False