# G:\Development\Git\DiscordBot\run_ingestion_jobs.py

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables (important for DB connection and API keys)
load_dotenv()

# Import the main asynchronous functions from your ingestion scripts
# Make sure these paths are correct relative to your 'src' directory
from src.api.ingest_sleeper_players import main as ingest_sleeper_players_main
from src.api.espn_api import main as ingest_espn_nfl_players_main
# Assuming nfl_data_py_test contains get_weekly_data and insert_data_to_db
from src.api.nfl_data_py_test import get_weekly_data, insert_data_to_db
# Assuming create_psg_table contains generate_create_table_sql and execute_create_table_sql
from src.db.db_operations.create_psg_table import generate_create_table_sql, execute_create_table_sql

async def run_all_ingestion_jobs():
    """
    Orchestrates the running of all data ingestion jobs.
    This is the main entry point for running your data pipelines.
    """
    print("Starting all data ingestion jobs...")
    
    # --- Run Sleeper Player Data Ingestion ---
    print("\n--- Running Sleeper Player Ingestion ---")
    try:
        await ingest_sleeper_players_main()
        print("✅ Sleeper Player Ingestion completed.")
    except Exception as e:
        print(f"❌ Sleeper Player Ingestion failed: {e}")
    
    # --- Run RapidAPI Player & Team Data Ingestion ---
    print("\n--- Running RapidAPI Player & Team Ingestion ---")
    try:
        await ingest_espn_nfl_players_main()
        print("✅ espn Player & Team Ingestion completed.")
    except Exception as e:
        print(f"❌ espn Player & Team Ingestion failed: {e}")

    print("\nAll scheduled ingestion jobs attempted.")
    
    try:
    #     # --- Run NFL Data Py Weekly Data Ingestion ---
        print("\n--- Running NFL Data Py Weekly Data Ingestion ---")
    #     # Corrected: get_weekly_data does not take arguments as per its definition
        weekly_data = get_weekly_data([2024, 2022, 2021, 2020, 2019])  # Adjust years as needed
        print(f"Fetched {len(weekly_data)} records from NFL Data Py for weekly data.")
        if not weekly_data.empty:
            print("\n--- Sample Weekly Data Head ---")
            print(weekly_data.head())
            
    #         print("\n--- Generated CREATE TABLE SQL Statement ---")
            table_name = "nfl_weekly_data_raw" # Ensure this matches the table name in insert_data_to_db
            sql_output = generate_create_table_sql(weekly_data, table_name)
            print(sql_output)

    #         # Execute the generated SQL statement
            success = await execute_create_table_sql(sql_output)
            if success:
                print(f"Table '{table_name}' is ready in your database.")
            else:
                print(f"Failed to create table '{table_name}'. Check logs for errors.")
            
    #         # Corrected: Await the async function insert_data_to_db
            await insert_data_to_db(weekly_data, table_name)
            print(f"✅ Data insertion into '{table_name}' initiated.")
        else:
            print("Could not generate SQL as no data was fetched.")
    except Exception as e:
        print(f"❌ NFL Data Py Weekly Data Ingestion failed: {e}")

if __name__ == "__main__":
    # This block ensures that run_all_ingestion_jobs() is called when the script is executed
    print("Executing data ingestion script...")
    asyncio.run(run_all_ingestion_jobs())
    print("Data ingestion script finished.")
