"""This is the main module of the bot.

It defines all the basic behaviour of the bot.
"""
import os

import discord
from discord.ext.commands import Cog, Bot, Context, command, CommandError
from discord import Member


class MyBot(Cog):
    """Main class for the bot.
    """
    def __init__(
            self,
            bot: Bot,
        ):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        """Show the servers to which the bot is connected.

        This function is called once when the bot is launched.
        """
        for guild in self.bot.guilds:
            print(f'Connected to {guild.name}')

    @Cog.listener()
    async def on_message(self, context: Context):
        """Called each time there is a message in a server.

        Basic behaviours are called on specific commands, but if you
        need to add a specific behaviour that isn't triggered by a command,
        this can be the place.
        """
        # Check if the message is for the bot
        if context.content.startswith(self.bot.command_prefix):
            return  # Do nothing

    @Cog.listener()
    async def on_command_error(
            self,
            context: Context,
            error: CommandError,
        ):
        """Catch the error and deal with it.

        Useful to catch an unknown command for example.
        """
        if isinstance(error, discord.ext.commands.errors.CommandNotFound):
            await context.send('Unknown command, type `!help` to get the list of all commands.')
            return

        # Raise other errors
        raise error

    @command(name='command1')
    async def example_any_arg(self,
            context: Context,
            *,
            answer,  # Captures all args in the answer variable
        ):
        """This command accepts any arguments as input.

        If no argument is provided, a default answer is send.
        Otherwise, it returns the provided argument.

        Example
        -------
        `!command1`
        `!command1 Anything you want`
        """

        if answer:
            await context.reply(answer)
            return

        # Default answer
        await context.send('No argument sent: this is my default answer!')
