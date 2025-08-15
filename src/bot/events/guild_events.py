# src/bot/events/guild_events.py
import discord
from discord.ext import commands

class GeneralEvents(commands.Cog):
    def __init__(self, bot: commands.Bot, default_channel_id: int):
        self.bot = bot
        self.default_channel_id = default_channel_id # Store the default channel ID

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author == self.bot.user:
            return

        # Simple example of a direct message response (can also be a command)
        if message.content.lower() == '!hello':
            await message.channel.send("👋 Hello! The Fantasy Football Fellowship Bot is Running.")
        
        # Note: bot.process_commands(message) is automatically handled by commands.Bot
        # when a cog is loaded, so you typically don't need it in on_message unless
        # you're doing custom pre-processing.

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        print(f"Joined a new guild: {guild.name} ({guild.id})")
        # You could send a welcome message here
        # E.g., find a suitable channel to send to:
        # general_channel = discord.utils.get(guild.text_channels, name="general")
        # if general_channel:
        #     await general_channel.send("Hello everyone! I'm here to help manage your fantasy league. Use `!help` to see my commands.")

# This function is required by discord.py to load the cog
async def setup(bot: commands.Bot):
    # Pass the default channel ID from the bot's custom properties
    await bot.add_cog(GeneralEvents(bot, bot.default_channel_id))