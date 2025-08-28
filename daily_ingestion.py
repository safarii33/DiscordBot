# G:\Development\Git\DiscordBot\run_ingestion_jobs.py

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables (important for DB connection and API keys)
load_dotenv()

# Import the main asynchronous functions from your ingestion scripts
# Make sure these paths are correct relative to your 'src' directory
from src.housekeeping.ingest_sleeper_players import main as ingest_sleeper_players_main
from src.housekeeping.dynasty_rankings import DynastyRankingsJob
from src.housekeeping.espn_api import main as ingest_espn_nfl_players_main 
# Assuming nfl_data_py_test contains get_weekly_data and insert_data_to_db
# from src.api.nfl_data_py_test import get_weekly_data, insert_data_to_db
# Assuming create_psg_table contains generate_create_table_sql and execute_create_table_sql
from src.db.db_operations.connections import get_db_connection_pool, close_db_connection_pool
from src.db.db_operations.create_psg_table import generate_create_table_sql, execute_create_table_sql

DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

async def run_daily_jobs():
    """
    Orchestrates the running of all data ingestion jobs.
    This is the main entry point for running your data pipelines.
    """
    print("Starting all data ingestion jobs...")
    
    # --- Run Sleeper Player Data Ingestion ---
    print("\n--- Running Sleeper Player Ingestion ---")
    # try:
    #     await ingest_sleeper_players_main()
    #     print("✅ Sleeper Player Ingestion completed.")
    # except Exception as e:
    #     print(f"❌ Sleeper Player Ingestion failed: {e}")
    
    # --- Run RapidAPI Player & Team Data Ingestion ---
    print("\n--- Running RapidAPI Player & Team Ingestion ---")
    # try:
    #     await ingest_espn_nfl_players_main()
    #     print("✅ espn Player & Team Ingestion completed.")
    # except Exception as e:
    #     print(f"❌ espn Player & Team Ingestion failed: {e}")

    print("\nAll scheduled ingestion jobs attempted.")
    # If you have other ingestion jobs, you can add them here in a similar manner

    # create daily dynasty rankings

    print("\n------------Configuring Dynasty Rankings for the day....---------------")
    ranking_cols_exclude = []
    dynasty_ranking_table_name = "sleeper.sleeper_dynasty_rankings"
    pk=['player_id_player']
    try:
        job = DynastyRankingsJob(DATABASE_URL)
        df = await job.main()  # Call the instance method
        sql_statement = generate_create_table_sql(df, dynasty_ranking_table_name, pk_needed=True)
        success = await execute_create_table_sql(sql_statement)
        if success:
            await job.insert_dataframe_rankings(df=df, table_name=dynasty_ranking_table_name, omit_columns=ranking_cols_exclude, pk=pk)
            print("✅ Sleeper Dynasty Rankings Ingestion and Table Creation completed.")
    except Exception as e:
        print(f"❌ Sleeper Dynasty Rankings Ingestion failed: {e}")

if __name__ == "__main__":
    # This block ensures that run_all_ingestion_jobs() is called when the script is executed
    print("Executing data ingestion script...")
    asyncio.run(run_daily_jobs())
    print("Data ingestion script finished.")
