# discord db import import
from discord.ext import commands
from database import get_biggest_moves

def register_commands(bot):
    @bot.command(name="moves")
    async def get_moves(ctx, time_period="daily"):
        """Get biggest KTC player moves for a given period (daily, weekly, monthly)."""
        moves = get_biggest_moves(time_period)
        if not moves:
            await ctx.send("No data available.")
            return

        message = f"📊 **Biggest {time_period.capitalize()} Moves:**\n"
        for player, value, change in moves:
            message += f"**{player}**: {value} KTC ({'+' if change > 0 else ''}{change})\n"

        await ctx.send(message)