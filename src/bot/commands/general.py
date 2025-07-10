# src/bot/commands/general.py
import discord
from discord.ext import commands

class GeneralCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help_bot", aliases=["help"])
    async def help_command(self, ctx: commands.Context):
        """Displays a list of available commands."""
        help_message = "🤖 **List of Commands:**\n" \
                       "`!hello` - Say hello to the bot\n" \
                       "`!movers` - Fetch biggest movers from KeepTradeCut\n" \
                       "`!standings` - Fetch and display standings from Sleeper\n" \
                       "`!trades [week]` - Fetch and display recent league trades (for a specific week)\n" \
                       "`!gradetrade [trade_id]` - Analyze and grade a specific trade.\n" \
                       "`!tradewins` - Display trade wins/losses for the league."
        await ctx.send(help_message)

    @commands.command(name="ping")
    async def ping_command(self, ctx: commands.Context):
        """Responds with Pong! and bot latency."""
        await ctx.send(f"Pong! {round(self.bot.latency * 1000)}ms")

# This function is required by discord.py to load the cog
async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCommands(bot))