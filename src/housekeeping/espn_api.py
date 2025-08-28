import requests
import json
import os
from datetime import datetime
import asyncio
import asyncpg

# Import the async connection pool functions
from src.db.db_operations.connections import get_db_connection_pool, close_db_connection_pool

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# --- ESPN Configuration ---
# IMPORTANT: Updated for ESPN Core API Athletes endpoint.
# This endpoint provides all active athletes directly, no need to iterate by team.
ESPN_BASE_URL = "https://sports.core.api.espn.com/v3/sports/football/nfl/"

# --- Database Configuration ---
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)

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

# --- Player Data Ingestion ---

async def fetch_espn_players(route):
    """
    Fetches all active player data from the ESPN Core API Athletes endpoint.
    Returns a list of all fetched player data.
    """
    players_url = f"{ESPN_BASE_URL}{route}"
    print(f"Fetching players from ESPN Core API URL: {players_url}")

    all_players_data = []

    try:
        print(f"Attempting to fetch all active players from ESPN Core API URL: {players_url}")
        response = requests.get(players_url) # Increased timeout for large response
        response.raise_for_status()
        full_players_response = response.json()
        
        # ESPN Core API for lists often nests items under an 'items' key
        if isinstance(full_players_response, dict) and 'items' in full_players_response:
            if isinstance(full_players_response['items'], list):
                all_players_data.extend(full_players_response['items'])
                print(f"✅ Fetched {len(full_players_response['items'])} active players from ESPN Core API.")
            else:
                print(f"⚠️ Unexpected 'items' format: Expected list, got {type(full_players_response['items'])}. Skipping.")
        else:
            # Fallback if 'items' key is not present, assume response is direct list or dict
            if isinstance(full_players_response, list):
                all_players_data.extend(full_players_response)
                print(f"✅ Fetched {len(full_players_response)} active players (direct list) from ESPN Core API.")
            elif isinstance(full_players_response, dict):
                all_players_data.extend(list(full_players_response.values()))
                print(f"✅ Fetched {len(full_players_response)} active players (dict values) from ESPN Core API.")
            else:
                print(f"⚠️ Unexpected top-level player data format: {type(full_players_response)}. Skipping.")

    except requests.exceptions.Timeout:
        print(f"❌ Failed to fetch players from ESPN Core API: Request timed out after 120 seconds.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch players from ESPN Core API: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON response from ESPN Core API: {e}")
        print(f"Raw response content (first 500 chars): {response.text[:500]}")
    except Exception as e:
        print(f"❌ An unexpected error occurred while fetching players from ESPN Core API: {e}")

    print(f"✅ Total players fetched from ESPN Core API: {len(all_players_data)}")
    return all_players_data


async def process_and_store_espn_players(players_data_from_api):
    """
    Processes and stores player data fetched from espn (ESPN Core API) into the PostgreSQL nfl_players table.
    Only inserts columns defined in the current CREATE TABLE statement.
    """
    if not players_data_from_api:
        print("No espn player data to process.")
        return

    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print("❌ Could not get a database connection pool. Aborting espn player processing.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction(): 
            try:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS nfl.nfl_players (
                    player_id TEXT PRIMARY KEY,
                    espn_id TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    age INTEGER,
                    height TEXT,
                    years_exp TEXT,
                    active BOOLEAN,
                    number INTEGER,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """)
                print("✅ nfl_players table schema checked/created for espn ingestion.")

                if not isinstance(players_data_from_api, list):
                    print("❌ Unexpected espn player response format. Expected a list of player dictionaries.")
                    return

                processed_count = 0
                skip_count = 0
                skip_inactive = 0
                # skipped players
                for player_raw_data in players_data_from_api:
                    if not isinstance(player_raw_data, dict):
                        skip_count += 1
                        continue
                    # --- Only map columns that exist in the table ---
                    player_id = str(player_raw_data.get("id")) if player_raw_data.get("id") else None
                    if not player_id:
                        skip_count += 1
                        continue

                    if player_raw_data.get("active") is not True:
                        skip_inactive += 1
                        continue

                    espn_id = player_id
                    first_name = player_raw_data.get("firstName")
                    last_name = player_raw_data.get("lastName")
                    age = clean_int(player_raw_data.get("age"))
                    height = player_raw_data.get("displayHeight") or player_raw_data.get("height")
                    years_exp_raw = player_raw_data.get("experience", {}).get("years")
                    years_exp = str(years_exp_raw) if years_exp_raw is not None else None
                    active = player_raw_data.get("active")
                    number = clean_int(player_raw_data.get("jersey"))

                    try:
                        await conn.execute("""
                            INSERT INTO nfl.nfl_players (
                                player_id, espn_id, first_name, last_name, age, height, years_exp, active, number, created_at, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            ON CONFLICT (player_id) DO UPDATE 
                            SET 
                                espn_id = EXCLUDED.espn_id,
                                first_name = EXCLUDED.first_name,
                                last_name = EXCLUDED.last_name,
                                age = EXCLUDED.age,
                                height = EXCLUDED.height,
                                years_exp = EXCLUDED.years_exp,
                                active = EXCLUDED.active,
                                number = EXCLUDED.number,
                                last_updated = NOW();
                        """, 
                        player_id,
                        espn_id,
                        first_name,
                        last_name,
                        age,
                        height,
                        years_exp,
                        active,
                        number,
                        datetime.now(),
                        datetime.now()
                        )
                        processed_count += 1
                        
                    except asyncpg.PostgresError as e:
                        print(f"❌ Database error processing espn player {player_id}: {e}")
                    except Exception as e:
                        print(f"❌ Unexpected error processing espn player {player_id}: {e}")
                
                print(f"✅ Processed {processed_count} espn player records.")
                print(f"✅ All espn player data processed and stored successfully!")

            except Exception as e:
                print(f"❌ An error occurred during espn player data processing: {e}")
                raise
            print(f'skipped players, not a dict or player_id not found: {skip_count}, '
                  f'skipped inactive players: {skip_inactive}')
# --- Team Data Ingestion ---

def fetch_espn_teams(route):
    """Fetches team data from espn and returns it as JSON."""
    teams_url = f"{ESPN_BASE_URL}{route}"

    try:
        print(f"Attempting to fetch team data from espn URL: {teams_url}")
        response = requests.get(teams_url)
        response.raise_for_status()
        print("✅ Team data fetched successfully from espn.")
        return response.json()
    except requests.exceptions.Timeout:
        print(f"❌ Failed to fetch teams from espn: Request timed out after 60 seconds.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to fetch teams from espn: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Failed to decode JSON response from espn: {e}")
        print(f"Raw response content (first 500 chars): {response.text[:500]}")
        return None

async def process_and_store_espn_teams(teams_data_from_api):
    """
    Processes and stores team data fetched from espn into the PostgreSQL nfl_teams table.
    """
    if not teams_data_from_api:
        print("No espn team data to process.")
        return

    pool = await get_db_connection_pool(DATABASE_URL)
    if not pool:
        print("❌ Could not get a database connection pool. Aborting espn team processing.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            try:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS nfl.nfl_teams (
                    team_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    short_display_name TEXT,
                    location TEXT,
                    abbreviation TEXT UNIQUE,
                    nickname TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """)
                print("✅ nfl_teams table schema checked/created.")

                teams_to_process = []
                if isinstance(teams_data_from_api, dict):
                    if 'team' in teams_data_from_api and isinstance(teams_data_from_api['team'], dict):
                        teams_to_process.append(teams_data_from_api['team'])
                    elif 'data' in teams_data_from_api and isinstance(teams_data_from_api['data'], list):
                        teams_to_process = teams_data_from_api['data']
                    else:
                        teams_to_process = list(teams_data_from_api.values())
                elif isinstance(teams_data_from_api, list):
                    teams_to_process = teams_data_from_api
                else:
                    print("❌ Unexpected espn team response format. Expected a list or dictionary of teams.")
                    return

                processed_count = 0
                skip_count = 0
                for team_raw_data in teams_to_process:
                    if not isinstance(team_raw_data, dict):
                        print(f"⚠️ Skipping team record: Not a dictionary ({type(team_raw_data)}).")
                        skip_count += 1
                        continue

                    team_data = team_raw_data.get('team', team_raw_data)

                    team_id = clean_int(team_data.get("id"))
                    if team_id is None:
                        skip_count += 1
                        print(f"⚠️ Skipping team: No valid 'id' found in record: {team_data.get('displayName', 'Unknown Team')}")
                        continue

                    name = team_data.get("name")
                    display_name = team_data.get("displayName")
                    short_display_name = team_data.get("shortDisplayName")
                    location = team_data.get("location")
                    abbreviation = team_data.get("abbreviation")
                    nickname = team_data.get("nickname")
                    processed_count += 1

                    if not name or not display_name or not abbreviation:
                        skip_count += 1
                        print(f"⚠️ Skipping team {team_id}: Missing required fields (name, displayName, or abbreviation).")
                        continue

                    try:
                        await conn.execute("""
                            INSERT INTO nfl.nfl_teams (
                                team_id, name, display_name, short_display_name, location, abbreviation, nickname, created_at, last_updated
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (team_id) DO UPDATE 
                            SET 
                                name = EXCLUDED.name,
                                display_name = EXCLUDED.display_name,
                                short_display_name = EXCLUDED.short_display_name,
                                location = EXCLUDED.location,
                                abbreviation = EXCLUDED.abbreviation,
                                nickname = EXCLUDED.nickname,
                                last_updated = NOW();
                        """, 
                        team_id,
                        name,
                        display_name,
                        short_display_name,
                        location,
                        abbreviation,
                        nickname,
                        datetime.now(),
                        datetime.now()
                        )
                        
                        
                    except asyncpg.PostgresError as e:
                        print(f"❌ Database error processing team {team_id}: {e}")
                    except Exception as e:
                        print(f"❌ Unexpected error processing team {team_id}: {e}")
                print(f'skipped teams, not a dict or team_id not found: {skip_count}')
                print(f"✅ Processed {processed_count} team records.")
                print(f"✅ All espn team data processed and stored successfully!")

            except Exception as e:
                print(f"❌ An error occurred during team data processing: {e}")
                raise
                        
# Main execution block
async def main():
    # --- Ingest Teams First ---
    espn_teams_data = fetch_espn_teams("teams")
    if espn_teams_data:
        await process_and_store_espn_teams(espn_teams_data)
    
    # --- Then Ingest Players ---
    espn_players_data = await fetch_espn_players("athletes?limit=20000&active=true") # Fetch all active players
    
    if espn_players_data:
        await process_and_store_espn_players(espn_players_data)
    
    await close_db_connection_pool()

if __name__ == "__main__":
    asyncio.run(main())
