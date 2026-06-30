#!/usr/bin/env python3
"""
ARKABot - Core Discord bot class with Lavalink and VRChat integration.
"""
import asyncio
import logging
import os
from typing import Optional

import discord
from discord.ext import commands
import wavelink

from arka.utils.logger import get_logger
from arka.utils.system import get_system_stats
from arka.cogs.vrchat import VRChatCog
from arka.cogs.music import MusicCog

log = get_logger(__name__)

class ARKABot(commands.AutoShardedBot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.guild_messages = True
        intents.message_content = True  # needed for prefix commands if used
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            application_id=int(os.getenv("APPLICATION_ID", "0")) if os.getenv("APPLICATION_ID") else None,
        )
        # Configuration from environment
        self.lavalink_host = os.getenv("LAVALINK_HOST", "127.0.0.1")
        self.lavalink_port = int(os.getenv("LAVALINK_PORT", "2333"))
        self.lavalink_password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
        self.vrchat_cookie = os.getenv("VRCHAT_COOKIE", "")
        self.vrchat_group_id = os.getenv("VRCHAT_GROUP_ID", "grp_9766cb0d-843f-4d81-827a-661ea9e2f346")
        self.target_channel_id = int(os.getenv("TARGET_CHANNEL_ID", "1496438095703441524"))
        self.vrchat_role_id = 1496438095703441524"))
        self.vrchat_role_id = int(os.getenv("VRCHAT_ROLE_ID", "1496879263767330987"))
        # Expose for cogs (they read from bot attributes)
        self.vrchat_cookie_attr = self.vrchat_cookie
        self.vrchat_group_id_attr = self.vrchat_group_id
        self.target_channel_id_attr = self.target_channel_id
        self.vrchat_role_id_attr = self.vrchat_role_id

    async def setup_hook(self) -> None:
        """Initialize Lavalink node and load cogs."""
        node = wavelink.Node(
            uri=f"http://{self.lavalink_host}:{self.lavalink_port}",
            password=self.lavalink_password,
            retry_attempts=5,
            retry_delay=5.0,
            timeout=10.0,
        )
        try:
            await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)
            log.info("Connected to Lavalink node at %s:%s", self.lavalink_host, self.lavalink_port)
        except Exception as e:
            log.error(f"Failed to connect to Lavalink: {e}")

        # Load cogs
        await self.add_cog(VRChatCog(self))
        await self.add_cog(MusicCog(self))
        log.info("Cogs loaded.")

        # Sync slash commands
        try:
            await self.tree.sync()
            log.info("Slash commands synced.")
        except Exception as e:
            log.error(f"Failed to sync slash commands: {e}")

    async def on_ready(self) -> None:
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.change_presence(activity=discord.Game(name="VRChat Arkana"))

    async def on_close(self) -> None:
        log.info("Bot shutting down, closing Lavalink pool.")
        try:
            await wavelink.Pool.close()
        except Exception:
            pass
        await super().on_close()

    # Helper methods for cog access
    def get_vrchat_cookie(self) -> str:
        return self.vrchat_cookie

    def update_vrchat_cookie(self, cookie: str) -> None:
        self.vrchat_cookie = cookie
        self.vrchat_cookie_attr = cookie
        cog = self.get_cog("VRChatCog")
        if cog:
            cog.set_cookie(cookie)