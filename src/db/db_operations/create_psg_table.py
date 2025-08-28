import os
import pandas as pd
import typing
import asyncpg
from src.db.db_operations.connections import get_db_connection_pool, close_db_connection_pool
# --- Database Configuration ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)


def map_pandas_dtype_to_postgres(dtype, col_name=None):
    """Maps Pandas data types to appropriate PostgreSQL data types."""
    # Use BIGINT for columns that are likely to have large values (e.g., IDs)
    if pd.api.types.is_integer_dtype(dtype):
        if col_name and any(x in col_name.lower() for x in ['id', 'league_id', 'user_id', 'team_id', 'player_id', 'last_author_id',
                                    'group_id', 'last_read_id', 'last_message_id', 'last_message_time', 'loser_bracket_id', 'winner_bracket_id',
                                    'company_id', 'draft_id', 'previous_league_id', 'last_transaction_id','bracket_id', 'loser_bracket_overrides_id', 'winner_bracket_id']):
            return "BIGINT"
        return "INTEGER"
    elif pd.api.types.is_float_dtype(dtype):
        return "NUMERIC" # Use NUMERIC for precision in stats
    elif pd.api.types.is_bool_dtype(dtype):
        return "BOOLEAN"
    elif pd.api.types.is_datetime64_any_dtype(dtype):
        return "TIMESTAMP WITH TIME ZONE"
    else: # Default to TEXT for objects (strings) and other unhandled types
        return "TEXT"

def generate_create_table_sql(df: pd.DataFrame, table_name: str, pk_needed: bool) -> str:
    """
    Generates a PostgreSQL CREATE TABLE statement from a Pandas DataFrame's schema.
    If pk_needed is False, omits the PRIMARY KEY clause.
    """
    if df.empty:
        return f"CREATE TABLE IF NOT EXISTS {table_name} (id SERIAL PRIMARY KEY);" # Basic fallback

    if 'owner_id' in df.columns:
        df = df.rename(columns={'owner_id': 'user_id'})

    columns_sql = []
    for col_name, dtype in df.dtypes.items():
        sql_col_name = ''.join(c if c.isalnum() else '_' for c in col_name).lower()
        pg_type = map_pandas_dtype_to_postgres(dtype, col_name)  # Pass col_name for BIGINT detection
        if sql_col_name in ['player_id', 'player_name', 'week', 'season', 'team_abbr']:
            columns_sql.append(f"    {sql_col_name} {pg_type} NOT NULL")
        else:
            columns_sql.append(f"    {sql_col_name} {pg_type}")


    pk_cols = []
    # if 'player_id' in df.columns: pk_cols.append('player_id')
    # if 'season' in df.columns: pk_cols.append('season')
    # if 'user_id' in df.columns: pk_cols.append('user_id')
    # if 'user_id' in df.columns: pk_cols.append('league_id')
    # if 'week' in df.columns: pk_cols.append('week')

    if pk_needed:
        if len(pk_cols) == 3:
            primary_key_clause = f",\n    PRIMARY KEY ({', '.join(pk_cols)})"
        else:
            primary_key_clause = ",\n    id SERIAL PRIMARY KEY"
        sql_statement = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
{', '.join(columns_sql)}{primary_key_clause}
)"""
    else:
        sql_statement = f"""
CREATE TABLE IF NOT EXISTS {table_name} (
{', '.join(columns_sql)}
)"""

    return sql_statement

async def execute_create_table_sql(sql_statement: str):
    """
    Executes a SQL CREATE TABLE statement against the PostgreSQL database.
    Optionally creates the schema if it does not exist.
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