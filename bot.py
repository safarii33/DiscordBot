# imports
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import get_biggest_moves
from discord_commands import register_commands

# # Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# # Setup bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
intents.message_content = True

# Register commands
# register_commands(bot)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.content.lower() == '!hello':
        await message.channel.send("👋 Hello! I'm alive!")
    await bot.process_commands(message)

# Start the bot
bot.run(TOKEN)






#Enable all intents, including message content

# Working code below
# intents = discord.Intents.default()
# intents.message_content = True  # Explicitly enable message content intent

# bot = commands.Bot(command_prefix="!", intents=intents)

# @bot.event
# async def on_ready():
#     print(f"Logged in as {bot.user}")

# @bot.command()
# async def hello(ctx):
#     await ctx.send("Hello!")

# bot.run(os.getenv("DISCORD_BOT_TOKEN"))