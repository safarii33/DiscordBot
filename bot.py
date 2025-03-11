# imports
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import get_biggest_moves
from discord_commands import register_commands

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Setup bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Register commands
register_commands(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# Start the bot
bot.run(TOKEN)