# src/bot/client.py
import discord
from discord.ext import commands

# Import your API clients and core logic classes
from src.api.sleeper import SleeperClient
# from src.api.rapidapi_nfl import RapidApiNFLClient
from src.api.ktc_scraper import KTCScraper
from src.core.player_data_manager import PlayerDataManager
from src.core.trade_analyzer import TradeAnalyzer # The class for trade wins logic
from src.db.repositories.trade_repo import TradeRepository # For saving/fetching trades and wins

class MyDiscordBot(commands.Bot):
    def __init__(self, command_prefix, intents, league_id: str, db_pool, default_channel_id: int, **kwargs):
        super().__init__(command_prefix=command_prefix, intents=intents, help_command=None, **kwargs)

        # Custom properties/attributes accessible across Cogs via bot.sleeper_client etc.
        self.league_id = league_id
        self.db_pool = db_pool
        self.default_channel_id = default_channel_id # Use for sending messages to a default channel

        # Initialize API clients (these manage their own connections/sessions)
        self.sleeper_client = SleeperClient(self.league_id)
        # self.rapidapi_nfl_client = RapidApiNFLClient()
        self.ktc_scraper = KTCScraper()

        # Initialize core logic managers
        self.player_data_manager = PlayerDataManager(
            sleeper_client=self.sleeper_client,
            rapidapi_nfl_client=self.rapidapi_nfl_client
        )
        self.trade_repository = TradeRepository(self.db_pool) # Pass db_pool to repo
        self.trade_analyzer = TradeAnalyzer(
            sleeper_client=self.sleeper_client,
            player_data_manager=self.player_data_manager,
            trade_repository=self.trade_repository # Pass repo for saving wins
        )

        # List of cogs to load
        self.initial_extensions = [
            'src.bot.events.guild_events',
            'src.bot.commands.general',
            'src.bot.commands.sleeper',
            'src.bot.commands.trade', # New trade commands cog
            # 'src.bot.tasks.scheduled_updates', # If you had background tasks in a cog
        ]

    async def setup_hook(self):
        """
        This is called after the bot is connected, but before on_ready.
        It's the ideal place to load cogs.
        """
        print("Running setup_hook to load extensions...")
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                print(f"Loaded extension: {extension}")
            except commands.ExtensionFailed as e:
                print(f"Failed to load extension {extension}: {e}")
            except commands.ExtensionNotFound:
                print(f"Extension not found: {extension}")
            except Exception as e:
                print(f"An unexpected error occurred loading {extension}: {e}")

        # Sync command tree if using application commands (optional for now)
        # await self.tree.sync()
        print("Setup hook complete. All extensions attempted to load.")


    async def on_ready(self):
        """Called when the bot is ready and has connected to Discord."""
        print(f"✅ Logged in as {self.user} (ID: {self.user.id})")
        print(f"Bot connected to {len(self.guilds)} guild(s).")
        # Start any background tasks here if they are part of a Cog that has been loaded
        # For example, if you have a cog for background tasks, it would start its loops in its own on_ready or cog_load method.
        # Example: self.get_cog('BackgroundTasksCog').start_all_loops()
        
        # Optionally, fetch player data into cache on startup
        print("Warming up player data cache...")
        # cache once a day, or on startup
        # This can be a long operation, so you might want to run it in the background
        ##########################################################################
        # await self.player_data_manager.warm_cache()
        ##########################################################################
        print("Player data cache warmed.")


    async def on_command_error(self, context: commands.Context, error: commands.CommandError):
        """Global command error handler."""
        if isinstance(error, commands.CommandNotFound):
            return # Silently ignore
        if isinstance(error, commands.MissingRequiredArgument):
            await context.send(f"Missing arguments. Usage: `{context.clean_prefix}{context.command.name} {context.command.signature}`")
        elif isinstance(error, commands.BadArgument):
            await context.send(f"Bad argument provided. Please check your input.")
        elif isinstance(error, commands.CommandOnCooldown):
            await context.send(f"This command is on cooldown. Try again in {error.retry_after:.2f}s.")
        else:
            print(f"Unhandled command error in {context.command}: {error}")
            await context.send(f"An unexpected error occurred: {error}")