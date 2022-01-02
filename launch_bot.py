"""Main module. Load the environment and launch the bot.

The environment must be fully functional! A file '.env' should be
placed in the executing directory (this one a priori).

This is where all the global variables are given (DISCORD_TOKEN, BOT_PREFIX...).
"""
import os
from dotenv import load_dotenv

from discord.ext.commands import Bot

from src.bot import MyBot
from src.youtube_bot import YoutubeBot


load_dotenv()

# Bot ID, you got this when you create a bot on the discord developer portal
TOKEN = os.getenv('DISCORD_TOKEN')
# Defines which prefix will trigger the bot commands, usually '!'
PREFIX = os.getenv('BOT_PREFIX')

bot = Bot(command_prefix=PREFIX)

# Add Cog to the bot, a Cog is an object with methods that will interact with discord servers
bot.add_cog(MyBot(bot))  # Main Cog
bot.add_cog(YoutubeBot(bot))

bot.run(TOKEN)
