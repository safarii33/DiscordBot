import nfl_data_py as nfl
import pandas as pd
import os
import typing
import asyncio
import asyncpg
from src.db.connections import get_db_connection_pool, close_db_connection_pool
from src.db.db_operations.create_psg_table import generate_create_table_sql, execute_create_table_sql

# --- Database Configuration ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

def get_seasonal_data():
    # Fetching the NFL data for the 2023 season
    try:
        data = nfl.import_seasonal_data(years=[2024, 2022, 2021, 2020, 2019], s_type='REG')
        return data
    except Exception as e:
        print(f"An error occurred while fetching the data: {e}")
        return None
    
def get_weekly_data(years: typing.List):
    # Fetching the NFL data for week 1 of the 2024 season
    try:
        data = nfl.import_weekly_data(years)
        return data
    except Exception as e:
        print(f"An error occurred while fetching the weekly data: {e}")
        return None

# --- New/Updated Function to Insert Data ---

async def insert_data_to_db(df: pd.DataFrame, table_name: str):
    """
    Inserts the DataFrame into the specified PostgreSQL table using ON CONFLICT DO UPDATE.
    
    Args:
        df (pd.DataFrame): The DataFrame to insert.
        table_name (str): The name of the table to insert data into.
    """
    if df.empty:
        print(f"No data in DataFrame to insert into '{table_name}'.")
        return

    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print(f"❌ Could not get a database connection pool. Aborting data insertion into '{table_name}'.")
        return
    
    # The SQL INSERT statement with ON CONFLICT DO UPDATE
    # This matches the structure you provided previously.
    insert_sql = """
    INSERT INTO nfl_weekly_data_raw (
        player_id, player_name, player_display_name, position, position_group, headshot_url, recent_team,
        season, week, season_type, opponent_team, completions, attempts, passing_yards, passing_tds,
        interceptions, sacks, sack_yards, sack_fumbles, sack_fumbles_lost, passing_air_yards,
        passing_yards_after_catch, passing_first_downs, passing_epa, passing_2pt_conversions, pacr, dakota,
        carries, rushing_yards, rushing_tds, rushing_fumbles, rushing_fumbles_lost, rushing_first_downs,
        rushing_epa, rushing_2pt_conversions, receptions, targets, receiving_yards, receiving_tds,
        receiving_fumbles, receiving_fumbles_lost, receiving_air_yards, receiving_yards_after_catch,
        receiving_first_downs, receiving_epa, receiving_2pt_conversions, racr, target_share,
        air_yards_share, wopr, special_teams_tds, fantasy_points, fantasy_points_ppr
    ) VALUES (
        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
        $11, $12, $13, $14, $15, $16, $17, $18, $19, $20,
        $21, $22, $23, $24, $25, $26, $27, $28, $29, $30,
        $31, $32, $33, $34, $35, $36, $37, $38, $39, $40,
        $41, $42, $43, $44, $45, $46, $47, $48, $49, $50,
        $51, $52, $53
    )
    ON CONFLICT (player_id, season, week) DO UPDATE SET
        player_name = EXCLUDED.player_name,
        player_display_name = EXCLUDED.player_display_name,
        position = EXCLUDED.position,
        position_group = EXCLUDED.position_group,
        headshot_url = EXCLUDED.headshot_url,
        recent_team = EXCLUDED.recent_team,
        season_type = EXCLUDED.season_type,
        opponent_team = EXCLUDED.opponent_team,
        completions = EXCLUDED.completions,
        attempts = EXCLUDED.attempts,
        passing_yards = EXCLUDED.passing_yards,
        passing_tds = EXCLUDED.passing_tds,
        interceptions = EXCLUDED.interceptions,
        sacks = EXCLUDED.sacks,
        sack_yards = EXCLUDED.sack_yards,
        sack_fumbles = EXCLUDED.sack_fumbles,
        sack_fumbles_lost = EXCLUDED.sack_fumbles_lost,
        passing_air_yards = EXCLUDED.passing_air_yards,
        passing_yards_after_catch = EXCLUDED.passing_yards_after_catch,
        passing_first_downs = EXCLUDED.passing_first_downs,
        passing_epa = EXCLUDED.passing_epa,
        passing_2pt_conversions = EXCLUDED.passing_2pt_conversions,
        pacr = EXCLUDED.pacr,
        dakota = EXCLUDED.dakota,
        carries = EXCLUDED.carries,
        rushing_yards = EXCLUDED.rushing_yards,
        rushing_tds = EXCLUDED.rushing_tds,
        rushing_fumbles = EXCLUDED.rushing_fumbles,
        rushing_fumbles_lost = EXCLUDED.rushing_fumbles_lost,
        rushing_first_downs = EXCLUDED.rushing_first_downs,
        rushing_epa = EXCLUDED.rushing_epa,
        rushing_2pt_conversions = EXCLUDED.rushing_2pt_conversions,
        receptions = EXCLUDED.receptions,
        targets = EXCLUDED.targets,
        receiving_yards = EXCLUDED.receiving_yards,
        receiving_tds = EXCLUDED.receiving_tds,
        receiving_fumbles = EXCLUDED.receiving_fumbles,
        receiving_fumbles_lost = EXCLUDED.receiving_fumbles_lost,
        receiving_air_yards = EXCLUDED.receiving_air_yards,
        receiving_yards_after_catch = EXCLUDED.receiving_yards_after_catch,
        receiving_first_downs = EXCLUDED.receiving_first_downs,
        receiving_epa = EXCLUDED.receiving_epa,
        receiving_2pt_conversions = EXCLUDED.receiving_2pt_conversions,
        racr = EXCLUDED.racr,
        target_share = EXCLUDED.target_share,
        air_yards_share = EXCLUDED.air_yards_share,
        wopr = EXCLUDED.wopr,
        special_teams_tds = EXCLUDED.special_teams_tds,
        fantasy_points = EXCLUDED.fantasy_points,
        fantasy_points_ppr = EXCLUDED.fantasy_points_ppr;
    """

    # Define the order of columns as they appear in the INSERT statement
    # This must EXACTLY match the order of $1, $2, ... in your SQL
    column_order = [
        'player_id', 'player_name', 'player_display_name', 'position', 'position_group',
        'headshot_url', 'recent_team', 'season', 'week', 'season_type',
        'opponent_team', 'completions', 'attempts', 'passing_yards', 'passing_tds',
        'interceptions', 'sacks', 'sack_yards', 'sack_fumbles', 'sack_fumbles_lost',
        'passing_air_yards', 'passing_yards_after_catch', 'passing_first_downs', 'passing_epa',
        'passing_2pt_conversions', 'pacr', 'dakota', 'carries', 'rushing_yards',
        'rushing_tds', 'rushing_fumbles', 'rushing_fumbles_lost', 'rushing_first_downs',
        'rushing_epa', 'rushing_2pt_conversions', 'receptions', 'targets',
        'receiving_yards', 'receiving_tds', 'receiving_fumbles', 'receiving_fumbles_lost',
        'receiving_air_yards', 'receiving_yards_after_catch', 'receiving_first_downs',
        'receiving_epa', 'receiving_2pt_conversions', 'racr', 'target_share',
        'air_yards_share', 'wopr', 'special_teams_tds', 'fantasy_points',
        'fantasy_points_ppr'
    ]

    # Prepare data for executemany
    # Convert DataFrame rows to a list of tuples, handling NaN/NaT values
    records_to_insert = []
    for index, row in df.iterrows():
        values = []
        for col in column_order:
            value = row.get(col) # Use .get() to safely access columns that might be missing in some dataframes
            # Convert pandas NaN/NaT to None for database compatibility
            if pd.isna(value):
                values.append(None)
            elif pd.api.types.is_datetime64_any_dtype(pd.Series(value)):
                # Convert Timestamp to datetime object if it's a datetime type
                values.append(value.to_pydatetime() if value is not None else None)
            else:
                values.append(value)
        records_to_insert.append(tuple(values))

    async with pool.acquire() as conn:
        async with conn.transaction():
            # Create table if it doesn't exist (important for initial runs)
            create_table_sql = generate_create_table_sql(df, table_name)
            await conn.execute(create_table_sql)
            print(f"Table '{table_name}' created or already exists.")
            
            # Insert data using executemany for efficiency
            try:
                # Use executemany for efficient bulk insertion
                await conn.executemany(insert_sql, records_to_insert)
                print(f"✅ Data inserted/updated into table '{table_name}' successfully. Total records: {len(records_to_insert)}")
            except asyncpg.PostgresError as e:
                print(f"❌ Database error during data insertion into '{table_name}': {e}")
                raise # Re-raise to propagate the error
            except Exception as e:
                print(f"❌ An unexpected error occurred during data insertion into '{table_name}': {e}")
                raise # Re-raise to propagate the error
    
    # The close_db_connection_pool() should ideally be called by the top-level orchestrator
    # if the pool is intended to be shared across multiple ingestion tasks.
    # If this function is the sole user of the pool, then keeping it here is fine.
    # For now, I'll assume it's part of a larger orchestration that handles closing.
    # await close_db_connection_pool() # Commented out as per typical orchestration pattern

# --- Example Usage (Main function to demonstrate) ---
async def main_example():
    # This is just for demonstration. In your actual ingestion script,
    # you'd call insert_data_to_db after fetching data.
    
    # 1. Get sample data (replace with your actual data fetching)
    # This part assumes nfl_data_py is imported and get_sample_weekly_data exists
    # If you don't have nfl_data_py setup, this will return an empty DataFrame
    try:
        import nfl_data_py as nfl
        def get_sample_weekly_data_for_example():
            try:
                # Fetch data for a single year to inspect its structure
                data = nfl.import_weekly_data(years=[2023], columns=['player_id', 'player_name', 'player_display_name', 'position', 'position_group', 'headshot_url', 'recent_team', 'season', 'week', 'season_type', 'opponent_team', 'completions', 'attempts', 'passing_yards', 'passing_tds', 'interceptions', 'sacks', 'sack_yards', 'sack_fumbles', 'sack_fumbles_lost', 'passing_air_yards', 'passing_yards_after_catch', 'passing_first_downs', 'passing_epa', 'passing_2pt_conversions', 'pacr', 'dakota', 'carries', 'rushing_yards', 'rushing_tds', 'rushing_fumbles', 'rushing_fumbles_lost', 'rushing_first_downs', 'rushing_epa', 'rushing_2pt_conversions', 'receptions', 'targets', 'receiving_yards', 'receiving_tds', 'receiving_fumbles', 'receiving_fumbles_lost', 'receiving_air_yards', 'receiving_yards_after_catch', 'receiving_first_downs', 'receiving_epa', 'receiving_2pt_conversions', 'racr', 'target_share', 'air_yards_share', 'wopr', 'special_teams_tds', 'fantasy_points', 'fantasy_points_ppr'])
                return data
            except Exception as e:
                print(f"❌ An error occurred while fetching sample weekly data for example: {e}")
                return pd.DataFrame() # Return empty DataFrame on error
        
        weekly_data_df = get_sample_weekly_data_for_example()
        if weekly_data_df.empty:
            print("No sample data fetched. Please ensure 'nfl_data_py' is installed and working.")
            return

        print(f"Fetched {len(weekly_data_df)} rows of sample weekly data.")
        
        # 2. Insert data into the database
        target_table = "nfl_weekly_data_raw"
        await insert_data_to_db(weekly_data_df, target_table)

    finally:
        await close_db_connection_pool() # Ensure pool is closed after example run

if __name__ == "__main__":
    asyncio.run(main_example())