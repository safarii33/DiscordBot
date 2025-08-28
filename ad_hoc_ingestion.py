# G:\Development\Git\DiscordBot\run_ingestion_jobs.py
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables (important for DB connection and API keys)
load_dotenv()

# Import the main asynchronous functions from your ingestion scripts
# Assuming nfl_data_py_test contains get_weekly_data and insert_data_to_db
from src.api.nfl_data_py_test import get_weekly_data, insert_data_to_db
# Assuming create_psg_table contains generate_create_table_sql and execute_create_table_sql
from src.db.db_operations.create_psg_table import generate_create_table_sql, execute_create_table_sql

async def sleeper_team_update():
    """
    Placeholder for any future Sleeper team update logic.
    Currently, it does not perform any operations.
    """

    print("Sleeper team update logic is not implemented yet.")

async def run_adhoc_ingestion_jobs():
    """
    Orchestrates the ad_hoc running of all necessary data ingestion jobs."""
    # try:
    # --- Run NFL Data Py Weekly Data Ingestion ---
    # Weekly only needs to be ran once a year.
        # print("\n--- Running NFL Data Py Weekly Data Ingestion ---")
    # Corrected: get_weekly_data does not take arguments as per its definition
        # weekly_data = get_weekly_data([2024, 2023, 2022, 2021, 2020, 2019])  # Adjust years as needed
        # print(f"Fetched {len(weekly_data)} records from NFL Data Py for weekly data.")
        # if not weekly_data.empty:
        #     print("\n--- Sample Weekly Data Head ---")
  
            
    # print("\n--- Generated CREATE TABLE SQL Statement ---")
            # table_name = "nfl.nfl_weekly_data_raw" # Ensure this matches the table name in insert_data_to_db
            # sql_output = generate_create_table_sql(weekly_data, table_name, False)
            # print(sql_output)

    # Execute the generated SQL statement
            # success = await execute_create_table_sql(sql_output)
            # if success:
            #     print(f"Table '{table_name}' is ready in your database.")
            # else:
            #     print(f"Failed to create table '{table_name}'. Check logs for errors.")
            
    # Corrected: Await the async function insert_data_to_db
    #         await insert_data_to_db(weekly_data, table_name)
    #         print(f"✅ Data insertion into '{table_name}' initiated.")
    #     else:
    #         print("Could not generate SQL as no data was fetched.")
    # except Exception as e:
    #     print(f"❌ NFL Data Py Weekly Data Ingestion failed: {e}")



async def main():
    await run_adhoc_ingestion_jobs()

if __name__ == "__main__":
    # This block ensures that run_all_ingestion_jobs() is called when the script is executed
    print("Executing data ingestion script...")
    asyncio.run(main())
    print("Data ingestion script finished.")
