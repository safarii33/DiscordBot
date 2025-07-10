# config/settings.py

BOT_PREFIX = "!"
DEFAULT_CHANNEL_ID = int(os.getenv("CHANNEL_ID")) # Use 0 or a placeholder if not set
                                                     # This will be passed to the bot instance