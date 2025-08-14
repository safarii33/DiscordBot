import requests
import json
import os
from datetime import datetime
import asyncio # New: For running async code

# New: Import the async connection pool functions
from src.db.connections import get_db_connection_pool, close_db_connection_pool
import asyncpg # New: Import asyncpg for type hinting and error handling

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Construct the database_url from environment variables
# This is the format asyncpg expects
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

def fetch_players():
    """Fetches player data from Sleeper API and returns it as JSON."""
    url = "https://api.sleeper.app/v1/players/nfl"
    
    try:
        response = requests.get(url, timeout=30) # Add a timeout for robustness
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print("✅ Player data fetched successfully from Sleeper API.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch players from Sleeper API: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON response from Sleeper API: {e}")
        return None

def clean_int(value):
    """
    Converts a value to an integer if possible, otherwise returns None.
    Handles strings that might contain non-digit characters or be empty.
    """
    if value is None:
        return None
    s_value = str(value).strip()
    if s_value.isdigit() or (s_value.startswith('-') and s_value[1:].isdigit()):
        return int(s_value)
    return None

# Changed to an async function
async def process_and_store_players(players):
    """
    Inserts or updates player data into the PostgreSQL nfl_players table using asyncpg.
    Uses ON CONFLICT (UPSERT) for efficient updates.
    """
    if not players:
        print("No player data to process.")
        return

    # Get the connection pool. It will be created if it doesn't exist.
    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print("❌ Could not get a database connection pool. Aborting player processing.")
        return

    # Acquire a connection from the pool and use a transaction
    async with pool.acquire() as conn:
        async with conn.transaction(): 
            try:
                # Create table if not exists - executed within the transaction
                # Ensure 'years_exp' is TEXT and 'last_updated' exists
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS nfl_players_sleeper (
                    player_id TEXT PRIMARY KEY,
                    team TEXT,
                    espn_id TEXT,
                    fantasy_data_id INTEGER,
                    first_name TEXT,
                    last_name TEXT,
                    college TEXT,
                    position TEXT,
                    search_rank INTEGER,
                    age INTEGER,
                    height TEXT,
                    weight TEXT,
                    high_school TEXT,
                    rookie_year INTEGER,
                    years_exp TEXT, -- Changed to TEXT to accommodate 'R' for Rookie
                    depth_chart_order INTEGER,
                    rotoworld_id INTEGER,
                    active BOOLEAN,
                    sportradar_id TEXT,
                    number INTEGER,
                    rotowire_id INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """)
                print("✅ nfl_players table checked/created.")

                # Insert or update all players
                for player_id, data in players.items():
                    # Explicitly ensure player_id is a string
                    player_id_str = str(player_id)

                    # Safely get metadata and then rookie_year from it
                    metadata = data.get("metadata") or {}
                    rookie_year = clean_int(metadata.get("rookie_year"))
                    
                    # Clean integer values for other fields
                    search_rank = clean_int(data.get("search_rank"))
                    age = clean_int(data.get("age"))
                    depth_chart_order = clean_int(data.get("depth_chart_order"))
                    rotoworld_id = clean_int(data.get("rotoworld_id"))
                    number = clean_int(data.get("number"))
                    rotowire_id = clean_int(data.get("rotowire_id"))
                    fantasy_data_id = clean_int(data.get("fantasy_data_id"))
                    
                    # Explicitly convert to string to handle both 'R' and integer values
                    years_exp_raw = data.get("years_exp")
                    years_exp_str = str(years_exp_raw) if years_exp_raw is not None else None
                    
                    # Explicitly convert espn_id to string as well
                    espn_id_raw = data.get("espn_id")
                    espn_id_str = str(espn_id_raw) if espn_id_raw is not None else None

                    # --- Debugging Print Statements ---
                    # These will show you the exact types and values being sent for problematic fields
                    # You can remove these once the issue is resolved.
                    print(f"--- Player {player_id_str} Data Types & Values ---")
                    print(f"  espn_id_str: '{espn_id_str}' (Type: {type(espn_id_str)})")
                    print(f"  years_exp_str: '{years_exp_str}' (Type: {type(years_exp_str)})")
                    print(f"  fantasy_data_id: {fantasy_data_id} (Type: {type(fantasy_data_id)})")
                    print(f"  rookie_year: {rookie_year} (Type: {type(rookie_year)})")
                    print(f"  number: {number} (Type: {type(number)})")
                    print(f"------------------------------------")
                    # --- End Debugging Print Statements ---
                    try:
                        await conn.execute("""
                            INSERT INTO nfl_players_sleeper (
                                player_id, team, espn_id, fantasy_data_id, first_name, last_name, college, position, search_rank,
                                age, height, weight, high_school, rookie_year, years_exp, depth_chart_order, rotoworld_id,
                                active, sportradar_id, number, rotowire_id, created_at, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23)
                            ON CONFLICT (player_id) DO UPDATE 
                            SET 
                                team = EXCLUDED.team,
                                espn_id = EXCLUDED.espn_id,
                                fantasy_data_id = EXCLUDED.fantasy_data_id,
                                first_name = EXCLUDED.first_name,
                                last_name = EXCLUDED.last_name,
                                college = EXCLUDED.college,
                                position = EXCLUDED.position,
                                search_rank = EXCLUDED.search_rank,
                                age = EXCLUDED.age,
                                height = EXCLUDED.height,
                                weight = EXCLUDED.weight,
                                high_school = EXCLUDED.high_school,
                                rookie_year = EXCLUDED.rookie_year,
                                years_exp = EXCLUDED.years_exp,
                                depth_chart_order = EXCLUDED.depth_chart_order,
                                rotoworld_id = EXCLUDED.rotoworld_id,
                                active = EXCLUDED.active,
                                sportradar_id = EXCLUDED.sportradar_id,
                                number = EXCLUDED.number,
                                rotowire_id = EXCLUDED.rotowire_id,
                                last_updated = NOW(); -- Update the last_updated timestamp
                        """, 
                        player_id,
                        data.get("team"),
                        espn_id_str, # Use the string version
                        fantasy_data_id,
                        data.get("first_name"),
                        data.get("last_name"),
                        data.get("college"),
                        data.get("position"),
                        search_rank,
                        age,
                        data.get("height"),
                        data.get("weight"),
                        data.get("high_school"),
                        rookie_year,
                        years_exp_str, # Use the string version
                        depth_chart_order,
                        rotoworld_id,
                        data.get("active"),
                        data.get("sportradar_id"),
                        number,
                        rotowire_id,
                        datetime.now(), # created_at for initial insert
                        datetime.now()  # last_updated will always be updated
                        )
                        
                    except asyncpg.PostgresError as e:
                        print(f"❌ Database error processing player {player_id}: {e}")
                        # No need for conn.rollback() here because we are in an async with conn.transaction() block
                        # The transaction will be rolled back automatically if an unhandled exception occurs.
                        # Or you can explicitly raise if a single player failure should stop the whole batch.
                    except Exception as e:
                        print(f"❌ Unexpected error processing player {player_id}: {e}")
                
                print(f"✅ All player data processed and stored successfully!")

            except Exception as e:
                print(f"❌ An error occurred during player data processing: {e}")
                raise # Re-raise to trigger transaction rollback

# Main execution block
async def main():
    players_data = fetch_players()
    if players_data:
        await process_and_store_players(players_data)
    
    # Ensure the connection pool is closed when the script finishes
    await close_db_connection_pool()

if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())