#!/usr/bin/env python3
"""
Music Cog for ARKA bot using wavelink.
Provides slash commands for playback control.
"""
import discord
from discord import app_commands
from discord.ext import commands
import wavelink

from arka.utils.logger import get_logger

log = get_logger(__name__)

class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queues: dict[int, list[wavelink.Playable]] = {}

    async def cog_load(self) -> None:
        self.bot.loop.create_task(self._start_node())
        log.info("Music cog loaded.")

    async def cog_unload(self) -> None:
        log.info("Music cog unloaded.")

    async def _start_node(self) -> None:
        """Ensure a Lavalink node is ready; if not, create one."""
        await self.bot.wait_until_ready()
        try:
            node = await wavelink.Pool.get_node()
            if not node.is_connected:
                await node.connect()
            log.info("Connected to Lavalink node.")
        except Exception as e:
            # Node may have been set up in bot's setup_hook; ignore if already present
            log.debug(f"Node already connected or error: {e}")

    # Helper to get player for a guild
    def _get_player(self, guild: discord.Guild) -> wavelink.Player | None:
        vc: wavelink.Player | None = guild.voice_client  # type: ignore
        return vc if isinstance(vc, wavelink.Player) else None

    # Slash command group for music
    music = app_commands.Group(name="music", description="Music playback controls")

    @music.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction) -> None:
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("You are not in a voice channel.", ephemeral=True)
            return
        channel = interaction.user.voice.channel
        try:
            player: wavelink.Player = await channel.connect(cls=wavelink.Player)
            await interaction.response.send_message(f"Joined {channel.name}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to join: {e}", ephemeral=True)

    @music.command(name="leave", description="Leave the voice channel")
    async def leave(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild) if interaction.guild else None
        if player:
            await player.disconnect()
            await interaction.response.send_message("Disconnected.", ephemeral=True)
        else:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)

    @music.command(name="play", description="Play a song from YouTube or SoundCloud")
    @app_commands.describe(query="Search query or URL")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer()
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("You need to be in a voice channel.", ephemeral=True)
            return
        # Ensure we are connected
        player = self._get_player(interaction.guild) if interaction.guild else None
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)  # type: ignore
            except Exception as e:
                await interaction.followup.send(f"Could not connect: {e}", ephemeral=True)
                return
        try:
            tracks: wavelink.Search = await wavelink.Playable.search(query)
            if not tracks:
                await interaction.followup.send("No results found.", ephemeral=True)
                return
            track: wavelink.Playable = tracks[0]  # take first result
            if player.playing:
                # Add to queue
                self.queues.setdefault(interaction.guild.id, []).append(track)
                await interaction.followup.send(f"Queued: {track.title}", ephemeral=True)
            else:
                await player.play(track)
                await interaction.followup.send(f"Now playing: {track.title}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error: {e}", ephemeral=True)

    @music.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild) if interaction.guild else None
        if player and player.playing:
            await player.pause(True)
            await interaction.response.send_message("Paused.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)

    @music.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild) if interaction.guild else None
        if player and player.paused:
            await player.pause(False)
            await interaction.response.send_message("Resumed.", ephemeral=True)
        else:
            await interaction.response.send_message("Not paused.", ephemeral=True)

    @music.command(name="skip", description="Skip current track")
    async def skip(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild) if interaction.guild else None
        if player and (player.playing or player.paused):
            await player.stop()
            await interaction.response.send_message("Skipped.", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

    @music.command(name="stop", description="Stop playback and clear queue")
    async def stop(self, interaction: discord.Interaction) -> None:
        player = self._get_player(interaction.guild) if interaction.guild else None
        if player:
            await player.stop()
            if interaction.guild.id in self.queues:
                self.queues[interaction.guild.id].clear()
            await interaction.response.send_message("Stopped and cleared queue.", ephemeral=True)
        else:
            await interaction.response.send_message("Not playing anything.", ephemeral=True)

    @music.command(name="queue", description="Show current queue")
    async def queue(self, interaction: discord.Interaction) -> None:
        q = self.queues.get(interaction.guild.id, [])
        if not q:
            await interaction.response.send_message("Queue is empty.", ephemeral=True)
            return
        desc = "\n".join(f"{i+1}. {t.title}" for i, t in enumerate(q[:10]))
        await interaction.response.send_message(f"Queue ({len(q)} tracks):\n{desc}", ephemeral=True)

    @music.command(name="volume", description="Set player volume (0-100)")
    @app_commands.describe(volume="Volume percentage")
    async def volume(self, interaction: discord.Interaction, volume: int) -> None:
        player = self._get_player(interaction.guild) if interaction.guild else None
        if player:
            if 0 <= volume <= 100:
                await player.volume(volume)
                await interaction.response.send_message(f"Volume set to {volume}%.", ephemeral=True)
            else:
                await interaction.response.send_message("Volume must be between 0 and 100.", ephemeral=True)
        else:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)

    # Event: when a track finishes, play next from queue
    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload) -> None:
        player: wavelink.Player = payload.player
        guild_id = player.guild.id
        # If there is a track in the player's internal queue, play it
        if player.queue and not player.queue.is_empty:
            next_track = await player.queue.get()
            await player.play(next_track)
            return
        # Else check our custom queue
        if guild_id in self.queues and self.queues[guild_id]:
            next_track = self.queues[guild_id].pop(0)
            await player.play(next_track)
        else:
            # Queue empty; do nothing
            pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MusicCog(bot))