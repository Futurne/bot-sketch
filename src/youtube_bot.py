"""Basic Youtube player for discord.

Can stream Youtube sounds from any given URL.
Also implements a queue, a stop and next command, all of this being handled over multiple guilds.

Thanks to @Vinicius Mesquita for his post on SO: https://stackoverflow.com/questions/56060614/how-to-make-a-discord-bot-play-youtube-audio.

Requirements: YoutubDl, ffmpeg, PyNaCl
"""
from typing import Optional
import asyncio

import discord
from discord.ext.commands import Cog, Bot, Context, command, CommandError

import youtube_dl


youtube_dl.utils.bug_reports_message = lambda e: print('Error:', e)

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(
            cls,
            url: str,
            *,
            loop=None,
            stream: bool = False
        ):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class GuildState:
    """Contains all informations about a
    guild state concerning voice channels
    and listened songs.
    """
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.voice_client = None
        self.currently_playing = None
        self.playlist = list()

    async def reset(self):
        """Disconnect from the voice channel if possible,
        and erase the current playlist.
        """
        await self.disconnect()
        self.voice_client = None
        self.currently_playing = None
        self.playlist = []

    async def disconnect(self):
        """Disconnect if possible.
        """
        if self.voice_client and self.voice_client.is_connected():
            await self.voice_client.disconnect()

        self.voice_client = None

    def cleanup_source(self):
        """Make sure FFmpeg process is cleaned up.
        """
        if self.voice_client and self.voice_client.source:
            self.voice_client.source.cleanup()


class YoutubeBot(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.guild_states = dict()  # guild.id -> GuildState

    def get_guildstate(self, guild_id: int):
        """Return the GuildState associated with the
        guild_id.
        Instanciate a new GuildState if needed.
        """
        if guild_id not in self.guild_states:
            self.guild_states[guild_id] = GuildState(guild_id)
        return self.guild_states[guild_id]

    @command(name='play')
    async def yt_play(
            self,
            context: Context,
            *,
            url: Optional[str]
        ):
        """Add to the playlist the Youtube song given.

        You have to be connected to a voice channel.
        """
        voice = context.author.voice
        guild = context.guild
        if voice is None:  # Sender isn't connected to a voice channel
            await context.send('You have to be connected to a voice channel!')
            return

        gs = self.get_guildstate(guild.id)

        if gs.voice_client and gs.voice_client.channel != voice.channel:
            # We have to change the channel the bot is connected to
            gs.disconnect()  # Disconnect the bot

        if gs.voice_client is None:  # Connect the bot to the author's channel
            gs.voice_client = await voice.channel.connect()

        gs.playlist.append(url)

        if not gs.voice_client.is_playing():
            await self.play_next(gs)

    @command(name='stop')
    async def yt_stop(self, context: Context):
        """Stop the current song.
        """
        voice = context.author.voice
        guild = context.guild
        gs = self.get_guildstate(guild.id)

        if gs.voice_client is None or not gs.voice_client.is_connected() or \
                not gs.voice_client.is_playing():
            await context.send('I am not playing anything right now.')
            return

        if voice is None or voice.channel != gs.voice_client.channel:
            await context.send("You're not connected to the same voice channel as me.")
            return

        await gs.reset()  # Reset all variables

    @command(name='next')
    async def yt_next(self, context: Context):
        """Pass to the next song in the playlist.

        If there are no songs next, disconnect the bot
        from the channel.
        """
        voice = context.author.voice
        guild = context.guild
        gs = self.get_guildstate(guild.id)

        if gs.voice_client is None or not gs.voice_client.is_connected() or\
                not gs.voice_client.is_playing():
            await context.send('I am not playing anything right not.')
            return

        if voice is None or voice.channel != gs.voice_client.channel:
            await context.send("You're not connected to the same voice channel as me.")
            return

        gs.voice_client.stop()  # Calls after_play (which does what we want)

    async def play_next(self, gs: GuildState):
        """Play the next song in the playlist.
        The playlist shouln't be empty.
        """
        assert len(gs.playlist) > 0, "Playlist empty!"

        url = gs.playlist.pop(0)
        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        gs.voice_client.play(player, after=lambda e: self.after_play(e, gs))
        # await context.send(f'Now playing: {player.title}')
        gs.currently_playing = url

    def after_play(self, error, gs: GuildState):
        """Called when a song is finished.

        The bot either plays the next song if there is one,
        or disconnect.
        """
        if not gs.voice_client or\
                not gs.voice_client.is_connected():
            return  # Nothing to do

        if gs.playlist == []:  # Nothing to play next
            coro = gs.reset()
            asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            return

        # Cleanup ending source
        gs.cleanup_source()
        # Plays the next song
        coro = self.play_next(gs)
        asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
