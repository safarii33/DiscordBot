import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import pandas as pd
import re
import json
import datetime
import numpy as np

now = datetime.datetime.now()

# Import the main asynchronous functions from your ingestion scripts
# Assuming nfl_data_py_test contains get_weekly_data and insert_data_to_db

# Assuming create_psg_table contains generate_create_table_sql and execute_create_table_sql
from src.db.db_operations.create_psg_table import generate_create_table_sql, execute_create_table_sql
from src.db.db_operations.connections import get_db_connection_pool, close_db_connection_pool

load_dotenv()
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
)
class DynastyRankingsJob:
    def __init__(self, db_url):
        self.db_url = db_url
        self.pool = None

    async def setup(self):
        self.pool = await get_db_connection_pool(self.db_url)

    async def close(self):
        await close_db_connection_pool()

    def make_name_key(self, first, last):
        key = f"{first} {last}".lower()
        key = re.sub(r'[^\w\s]', '', key)
        return key.strip()
    
    def safe_int(self, value, default=0):
        try:
            if pd.isna(value):
                return default
            return int(value)
        except Exception:
            return default

    # For stats_df, split player_display_name into first and last name
    def split_display_name(self, display_name):
        parts = display_name.split()
        first = parts[0] if len(parts) > 0 else ""
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        return first, last

    def get_position_multiplier(self, position, roster_positions):
        if "SUPER_FLEX" in roster_positions:
            if position == 'QB':
                return 2.0
            elif position == 'RB':
                return 1.0
            elif position == 'WR':
                return 1.25
        return 1.0

    def calculate_dynasty_score(self, row, stats, super_flex):
        player_stats = stats[stats['player_id'] == row['player_id_stats']]
        first_name = str(row.get('first_name_player', '') or '')
        last_name = str(row.get('last_name_player', '') or '')
        player_id = str(row.get('player_id_player', '') or '')
        if player_stats.empty:
            print(f"⚠️ No stats found for player: {first_name} {last_name} ({player_id})")
        player_stats['fantasy_points_ppr'] = player_stats['fantasy_points_ppr'].astype(float)
        avg_points = player_stats['fantasy_points_ppr'].mean()
        std_dev = player_stats['fantasy_points_ppr'].std()
        peak_weeks = (player_stats['fantasy_points_ppr'] > player_stats['fantasy_points_ppr'].quantile(0.9)).sum()
        durability = len(player_stats) / (2 * 17)

        # acquire the position list as it indicates super flex eligibility
        position_mult = self.get_position_multiplier(row['position'], super_flex)
        age = self.safe_int(row.get('age'), 0)
        years_exp = self.safe_int(row.get('years_exp'), 0)
        rank = self.safe_int(row.get('rank'), 999)
        age_factor = max(0.5, 1.5 - 0.06 * age)  # Example: younger = higher, older = lower

        # renamed to rank in fetch_players
        rank_boost = np.exp(-0.07 * rank) * 5  # The multiplier (5) can be tuned
        rank_boost = max(rank_boost, 0.05)     # Prevent zero/negative boost
        if rank <= 5:
            rank_boost += 3
        elif rank <= 10:
            rank_boost += 2
        elif rank <= 30:
            rank_boost += 1
        if years_exp <= 2:
            durability = max(durability, 0.7)  # Don't penalize too harshly

        rookie_bonus = 0
        if years_exp <= 1 or age <= 23:
            rookie_bonus = 2  # Tune this value as needed
        elif years_exp == 2 or age <= 25:
            rookie_bonus = 1  # Slight bonus for sophomores
        score = (
            avg_points * position_mult * age_factor * durability * rank_boost
            + peak_weeks * 0.5
            + rookie_bonus
        )
        return score

    async def fetch_players(self, pool):
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT player_id, first_name, last_name, search_rank as rank, years_exp, age " \
            "FROM nfl.nfl_players_sleeper " \
            "WHERE search_rank < 300 AND active = true AND position IN ('WR', 'RB', 'TE', 'QB')")
            dict_rows = [dict(row) for row in rows]
            return pd.DataFrame(dict_rows)

    async def fetch_stats(self, pool):
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT NWDR.PLAYER_ID, nwdr.player_display_name, nwdr.passing_yards, nwdr.completions, nwdr.attempts,"\
                                    "nwdr.passing_tds, nwdr.interceptions as thrown_ints, nwdr.sacks as sacked, " \
                                    "nwdr.sack_yards as sacked_yards, nwdr.sack_fumbles as sacked_fumbles, nwdr.passing_air_yards,"\
                                    "nwdr.passing_yards after_catch, nwdr.passing_first_downs, nwdr.passing_epa, nwdr.passing_2pt_conversions, " \
                                    "nwdr.pacr, nwdr.rushing_fumbles, nwdr.rushing_fumbles_lost,"\
                                    "nwdr.position, nwdr.recent_team, nwdr.week, nwdr.opponent_team, nwdr.receptions, " \
                                    "nwdr.targets, nwdr.receiving_yards, nwdr.receiving_tds, nwdr.carries, nwdr.season,"\
                                    "nwdr.rushing_yards, nwdr.receiving_air_yards, nwdr.receiving_yards_after_catch, " \
                                    "nwdr.receiving_first_downs, nwdr.fantasy_points, nwdr.fantasy_points_ppr," 
                                    "nwdr.fantasy_points_ppr - receptions * .5 fantasy_points_half_ppr " \
                                    "FROM nfl.nfl_weekly_data_raw nwdr WHERE NWDR.SEASON > 2022")
            dict_rows = [dict(row) for row in rows]
            return pd.DataFrame(dict_rows)

    async def fetch_roster_positions(self, pool, league_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT roster_positions FROM sleeper.leagues WHERE league_id = $1", league_id)
            return json.loads(row['roster_positions']) if row else {}
        

    async def insert_dataframe_rankings(self, df: pd.DataFrame, table_name: str, omit_columns: list = None, pk: list = None):
            """
            Bulk upserts all rows from a DataFrame into the specified PostgreSQL table.
            Uses (user_id, league_id) as the composite key.
            Allows omitting specified columns from insert.
            """
            if df.empty:
                print("❌ DataFrame is empty. No data to insert.")
                return False

            # Omit specified columns
            if omit_columns:
                for col in omit_columns:
                    if col in df.columns:
                        df = df.drop(columns=[col])

            # Cast 'metadata' dicts to JSON strings if present
            # Define which columns should be treated as dicts and which as lists
            dict_columns = ['metadata', 'settings', 'scoring_settings', 'co_owners']
            list_columns = ['roster_positions', 'players', 'reserve', 'starters', 'taxi']

            for col in dict_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, dict) else str(x))

            for col in list_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else str(x))

            if 'owner_id' in df.columns:
                df = df.rename(columns={'owner_id': 'user_id'})

            pool = await get_db_connection_pool(DATABASE_URL)
            if not pool:
                print("❌ Could not get a database connection pool. Aborting insert.")
                return False
            async with pool.acquire() as conn:
                async with conn.transaction():
                    columns = [ ''.join(c if c.isalnum() else '_' for c in col).lower() for col in df.columns ]
                    values = [tuple(row) for row in df.values]
                    placeholders = ', '.join([f"${i+1}" for i in range(len(columns))])
                    update_assignments = ', '.join([f"{col}=EXCLUDED.{col}" for col in columns if col not in pk and col != 'updated_timestamp'] + ["updated_timestamp = NOW()"])
                    upsert_sql = (
                        f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) "
                        f"ON CONFLICT ({', '.join(pk)}) DO UPDATE SET {update_assignments}"
                    )
                    try:
                        await conn.executemany(upsert_sql, values)
                        print(f"✅ Bulk upserted {len(values)} rows into {table_name}.")
                        return True
                    except asyncpg.PostgresError as e:
                        print(f"❌ Database error during bulk upsert: {e}")
                        return False
                    except Exception as e:
                        print(f"❌ Unexpected error during bulk upsert: {e}")
                        return False
    async def main(self):
        await self.setup()
        players_df = await self.fetch_players(self.pool)
        stats_df = await self.fetch_stats(self.pool)
        super_flex = await self.fetch_roster_positions(self.pool, league_id=os.environ.get('LEAGUE_ID'))

        # Build name_key for joining
        players_df['name_key'] = players_df.apply(lambda row: self.make_name_key(row['first_name'], row['last_name']), axis=1)
        stats_df[['first_name', 'last_name']] = stats_df['player_display_name'].apply(
            lambda name: pd.Series(self.split_display_name(name))
        )
        stats_df['name_key'] = stats_df.apply(lambda row: self.make_name_key(row['first_name'], row['last_name']), axis=1)

        merged_df = pd.merge(
            players_df,
            stats_df,
            on='name_key',
            how='left',  # <-- This ensures all players are included
            suffixes=('_player', '_stats')
        )
        merged_df['dynasty_score'] = merged_df.apply(lambda row: self.calculate_dynasty_score(row, stats_df, super_flex), axis=1)
        merged_df = merged_df.sort_values('dynasty_score', ascending=False)
        merged_df['created_timestamp'] = now
        merged_df['updated_timestamp'] = now
        merged_df['age'] = merged_df['age'].fillna(0)
        merged_df['years_exp'] = merged_df['years_exp'].fillna(0)
        merged_df['rank'] = merged_df['rank'].fillna(999)
        final_df = merged_df[['player_display_name', 'player_id_player', 'name_key', 'dynasty_score', 'created_timestamp', 'updated_timestamp']]
        final_df['player_id_player'] = final_df['player_id_player'].astype(str)
        final_df['player_display_name'] = final_df['player_display_name'].astype(str)
        final_df['name_key'] = final_df['name_key'].astype(str)
        final_df['dynasty_score'] = final_df['dynasty_score'].astype(float)
        final_df['created_timestamp'] = pd.to_datetime(final_df['created_timestamp'])
        final_df['updated_timestamp'] = pd.to_datetime(final_df['updated_timestamp'])
        await self.close()
        return final_df