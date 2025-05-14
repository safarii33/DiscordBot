# imports
import os
import discord
import asyncio
from datetime import datetime, timedelta, time
from discord.ext import commands, tasks
from dotenv import load_dotenv
from src.resources.db.database import get_biggest_moves
from discord_commands import register_commands
from src.scraper.ktc_scraper import get_ktc_risers_and_fallers
from src.scraper.web_driver import web_driver_manager
from src.jobs.sleeper_job import SleeperJob

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
LEAGUE_ID = os.getenv("LEAGUE_ID")

# Setup bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
sleeper = SleeperJob(LEAGUE_ID)
intents.message_content = True
channel_id = os.getenv("channel_id")
CHANNEL_ID = int(channel_id) if channel_id else None

#utilities

def seconds_until_next(day_of_week: int, target_time: time):
    now = datetime.now()
    target = datetime.combine(now.date(), target_time)

    # increment to next target day
    while target.weekday() != day_of_week or target <= now:
        target += timedelta(days=1)

    return (target - now).total_seconds()

def seconds_until_next_sunday_8pm():
    now = datetime.now()
    next_target = datetime.combine(now.date(), time(20, 0))  # 8 PM today
    while next_target <= now or next_target.weekday() != 6:  # 6 = Sunday
        next_target += timedelta(days=1)
    return (next_target - now).total_seconds()

async def schedule_median_update():
    await asyncio.sleep(seconds_until_next_sunday_8pm())
    while True:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send("📊 Here's the weekly median winners recap!")
            # Call your custom method here:
            # await post_median_winners(channel)

        # Sleep for 7 days until the next Sunday
        await asyncio.sleep(7 * 24 * 60 * 60)


# bot events

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await schedule_median_update()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # say hello
    if message.content.lower() == '!hello':
        await message.channel.send("👋 Hello! The Fantasy Football Fellowship Bot is Running.")
    await bot.process_commands(message)

    # list commands
    if message.content.lower() == '!help':
        await message.channel.send("🤖 **List of Commands:**\n"
                                   "`!hello` - Say hello to the bot\n"
                                   "`!movers` - Fetch biggest movers from KeepTradeCut\n"
                                   "`!standings` - Fetch and display standings from Sleeper")

# bot commands - Biggest moves - !movers from KTC   
@bot.command(name="movers")
async def movers(ctx):
    # fetch biggest movers from keeptradecut.com
    await ctx.send(f"Fetching biggest movers from KTC... hol' up I'm working on it gang. 🤖")
    data = get_ktc_risers_and_fallers()
    if not data:
        await ctx.send("I was not able to retrieve the data. Please check with a developer for assistance.")
        return
    await ctx.send(f"🏈⬆️⬇️ **Biggest Movers: Requested by {ctx.author.mention}**")
    risers = "\n".join([f"🔼 {r['name']} - {r['value']}" for r in data["risers"]])
    fallers = "\n".join([f"🔽 {f['name']} - {f['value']}" for f in data["fallers"]])

    # TODO: add embed

    # embed = discord.Embed(title="📈 KTC Market Movers (30 Days)", color=0x00FF00)
    # embed.add_field(name="🔥 Top 5 Risers", value=risers, inline=False)
    # embed.add_field(name="❄️ Top 5 Fallers", value=fallers, inline=False)

    resp = f"**🔥 Top 5 Risers (30 Days) 🔥**\n{risers}\n\n**❄️ Top 5 Fallers (30 Days) ❄️**\n{fallers}"

    await ctx.send(resp)


# Sleeper commands 
# Sleeper standings - !standings
@bot.command()
async def standings(ctx):
    """Command to fetch and display standings."""
    data = sleeper.get_standings()

    if "error" in data:
        await ctx.send(data["error"])
        return

    standings_msg = "**Sleeper Standings:**\n"
    calculated_win_percentage = 0
    for team in data:
        wins = team["settings"]["wins"]
        losses = team["settings"]["losses"]
        total_games = wins + losses

        if total_games == 0:
            calculated_win_percentage = 0  # Prevent division by zero
        else:
            calculated_win_percentage = (wins / total_games) * 100  # Convert to percentage

        team_name = sleeper.get_team_name(team["owner_id"])
        standings_msg += f"**{team_name}** | **{wins}W - {losses}L ----> Win % ➡️ {calculated_win_percentage:.2f}%**\n"

    await ctx.send(standings_msg)

# Sleeper Player - !players
@bot.command()
async def players(ctx):
    """Command to fetch and display player stats"""
    

# Shutdown driver
@bot.event
async def on_shutdown():
    """Cleanup WebDriver on shutdown."""
    global web_driver_manager
    web_driver_manager.quit_driver()

# Start the bot
bot.run(TOKEN)
