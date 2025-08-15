# main.py
import os
import asyncio
import discord
from dotenv import load_dotenv
from config.settings import BOT_PREFIX, DEFAULT_CHANNEL_ID # Import from your config
from src.bot.client import MyDiscordBot # Your custom bot class
from src.db.connections import get_db_connection_pool, close_db_connection_pool

async def main():
    load_dotenv() # Load environment variables

    # 1. Get credentials and configurations
    token = os.getenv("DISCORD_BOT_TOKEN")
    league_id = os.getenv("LEAGUE_ID")
    database_url = os.getenv("DATABASE_URL")

    if not token:
        raise ValueError("DISCORD_BOT_TOKEN environment variable not set.")
    if not league_id:
        print("Warning: LEAGUE_ID not set. Some Sleeper features may not work.")
    if not database_url:
        print("Warning: DATABASE_URL not set. Database features will be unavailable.")

    # 2. Setup Intents
    intents = discord.Intents.default()
    intents.message_content = True # Required for reading message content for commands
    intents.members = True         # Required for member-related events/caching
    intents.guilds = True          # Required for guild-related events/caching

    # 3. Initialize shared resources (DB Pool, API clients, etc.)
    db_pool = None
    if database_url:
        db_pool = await get_db_connection_pool(database_url)

    # 4. Initialize your custom Bot class
    bot = MyDiscordBot(
        command_prefix=BOT_PREFIX,
        intents=intents,
        league_id=league_id,      # Pass league_id to the bot instance
        db_pool=db_pool,          # Pass database pool to the bot instance
        default_channel_id=DEFAULT_CHANNEL_ID # Pass default channel ID
    )

    # 5. Define global shutdown hook (optional, can also be in client.py setup_hook)
    @bot.event
    async def on_shutdown():
        print("Bot is shutting down...")
        await close_db_connection_pool() # Close the DB pool gracefully
        # Add any other cleanup here (e.g., closing web drivers)

    # 6. Start the bot
    print("Starting bot...")
    await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    except Exception as e:
        print(f"An error occurred during bot startup: {e}")