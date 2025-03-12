# imports
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from database import get_biggest_moves
from discord_commands import register_commands
from ktc_scraper import get_ktc_risers_and_fallers
from webdriver_manager import web_driver_manager

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

@bot.command(name="movers")
async def movers(ctx):
    # fetch biggest movers from keeptradecut.com
    await ctx.send(f"Fetching biggest movers from KTC... hol' up I'm working on it gang. 🤖")
    data = get_ktc_risers_and_fallers()
    if not data:
        await ctx.send("I was not able to retrieve the data. Please check with a developer for assistance.")
        return
    await ctx.send("🏈⬆️⬇️ **Biggest Movers:**")
    risers = "\n".join([f"🔼 {r['name']} - {r['value']}" for r in data["risers"]])
    fallers = "\n".join([f"🔽 {f['name']} - {f['value']}" for f in data["fallers"]])

    embed = discord.Embed(title="📈 KTC Market Movers (30 Days)", color=0x00FF00)
    embed.add_field(name="🔥 Top 5 Risers", value=risers, inline=False)
    embed.add_field(name="❄️ Top 5 Fallers", value=fallers, inline=False)

    # resp = f"**🔥 Top 5 Risers (30 Days) 🔥**\n{risers}\n\n**❄️ Top 5 Fallers (30 Days) ❄️**\n{fallers}"

    # await ctx.send(resp)
@bot.event
async def on_shutdown():
    """Cleanup WebDriver on shutdown."""
    web_driver_manager.quit_driver()

# Start the bot
bot.run(TOKEN)
