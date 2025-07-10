# src/db/repositories/trade_repo.py
import asyncpg
import json

class TradeRepository:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        # Ensure table exists
        asyncio.create_task(self._create_table())

    async def _create_table(self):
        """Creates the 'trades' table if it doesn't exist."""
        schema = """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id VARCHAR(255) PRIMARY KEY,
            trade_data JSONB NOT NULL,
            winning_roster_id VARCHAR(255),
            losing_roster_id VARCHAR(255),
            winner_grade VARCHAR(10),
            loser_grade VARCHAR(10),
            graded_at TIMESTAMPTZ DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS trade_outcomes (
            roster_id VARCHAR(255) PRIMARY KEY,
            wins INT DEFAULT 0,
            losses INT DEFAULT 0,
            last_updated TIMESTAMPTZ DEFAULT NOW()
        );
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute(schema)
            print("Database tables 'trades' and 'trade_outcomes' ensured.")

    async def save_trade(self, trade_id: str, trade_data: dict):
        """Saves a raw trade transaction to the database."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO trades (trade_id, trade_data)
                VALUES ($1, $2::jsonb)
                ON CONFLICT (trade_id) DO UPDATE SET
                    trade_data = EXCLUDED.trade_data,
                    graded_at = NOW();
                """,
                trade_id, json.dumps(trade_data)
            )

    async def get_trade(self, trade_id: str):
        """Fetches a trade by ID from the database."""
        async with self.db_pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT trade_data FROM trades WHERE trade_id = $1;",
                trade_id
            )
            return json.loads(record['trade_data']) if record else None

    async def record_trade_outcome(self, trade_id: str, winning_roster_id: str, 
                                   losing_roster_id: str, winner_grade: str, loser_grade: str):
        """Records the outcome of a graded trade and updates trade_outcomes."""
        async with self.db_pool.acquire() as conn:
            # Update the trades table with grading results
            await conn.execute(
                """
                UPDATE trades
                SET winning_roster_id = $2, losing_roster_id = $3,
                    winner_grade = $4, loser_grade = $5,
                    graded_at = NOW()
                WHERE trade_id = $1;
                """,
                trade_id, winning_roster_id, losing_roster_id, winner_grade, loser_grade
            )

            # Update trade_outcomes for the winner
            await conn.execute(
                """
                INSERT INTO trade_outcomes (roster_id, wins, losses, last_updated)
                VALUES ($1, 1, 0, NOW())
                ON CONFLICT (roster_id) DO UPDATE SET
                    wins = trade_outcomes.wins + 1,
                    last_updated = NOW();
                """,
                winning_roster_id
            )

            # Update trade_outcomes for the loser
            await conn.execute(
                """
                INSERT INTO trade_outcomes (roster_id, wins, losses, last_updated)
                VALUES ($1, 0, 1, NOW())
                ON CONFLICT (roster_id) DO UPDATE SET
                    losses = trade_outcomes.losses + 1,
                    last_updated = NOW();
                """,
                losing_roster_id
            )
        print(f"Trade {trade_id} outcome recorded: Winner={winning_roster_id}, Loser={losing_roster_id}")


    async def get_aggregated_trade_wins_losses(self):
        """Fetches aggregated trade wins and losses for all rosters."""
        async with self.db_pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT roster_id, wins, losses FROM trade_outcomes ORDER BY wins DESC;"
            )
            # You'll need to map roster_id to display names here for presentation
            # This is where PlayerDataManager/SleeperClient comes in handy
            results = {}
            for record in records:
                # This part needs an external lookup to get the team name
                # For now, just use roster_id or pass the bot instance to repo
                results[record['roster_id']] = {
                    'team_name': record['roster_id'], # Placeholder
                    'wins': record['wins'],
                    'losses': record['losses']
                }
            return results

# Add this import to the top of your `trade_repo.py`
import asyncio # For asyncio.create_task in __init__