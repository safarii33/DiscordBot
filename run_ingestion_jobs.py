# G:\Development\Git\DiscordBot\run_ingestion_jobs.py

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables (important for DB connection and API keys)
load_dotenv()

# Import the main asynchronous functions from your ingestion scripts
# Make sure these paths are correct relative to your 'src' directory
from src.api.ingest_sleeper_players import main as ingest_sleeper_players_main
from src.api.espn_api import main as ingest_rapidapi_nfl_players_main

async def run_all_ingestion_jobs():
    """
    Orchestrates the running of all data ingestion jobs.
    This is the main entry point for running your data pipelines.
    """
    print("Starting all data ingestion jobs...")
    
    # --- Run Sleeper Player Data Ingestion ---
    # print("\n--- Running Sleeper Player Ingestion ---")
    # try:
    #     await ingest_sleeper_players_main()
    #     print("✅ Sleeper Player Ingestion completed.")
    # except Exception as e:
    #     print(f"❌ Sleeper Player Ingestion failed: {e}")
    
    # --- Run RapidAPI Player & Team Data Ingestion ---
    print("\n--- Running RapidAPI Player & Team Ingestion ---")
    try:
        await ingest_rapidapi_nfl_players_main()
        print("✅ RapidAPI Player & Team Ingestion completed.")
    except Exception as e:
        print(f"❌ RapidAPI Player & Team Ingestion failed: {e}")

    print("\nAll scheduled ingestion jobs attempted.")

if __name__ == "__main__":
    # This block ensures that run_all_ingestion_jobs() is called when the script is executed
    print("Executing data ingestion script...")
    asyncio.run(run_all_ingestion_jobs())
    print("Data ingestion script finished.")