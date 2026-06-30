#!/usr/bin/env python3
"""
VRChat Cog for ARKA bot.
Handles VRChat authentication (cookie) and fetching group instances.
Provides data for dashboard.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from arka.utils.logger import get_logger

log = get_logger(__name__)

class VRChatCog(commands.Cog):
    """VRChat related commands and background tasks."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.cookie: str = getattr(bot, "vrchat_cookie", "")
        self.session: Optional[aiohttp.ClientSession] = None
        self.group_id: str = getattr(bot, "vrchat_group_id", "grp_9766cb0d-843f-4d81-827a-661ea9e2f346")
        self.target_channel_id: int = getattr(bot, "target_channel_id", 1496438095703441524)
        self.vrchat_role_id: int = getattr(bot, "vrchat_role_id", 1496879263767330987)
        # Store latest instance data for dashboard
        self.latest_instances: Dict[str, dict] = {}
        # Background tasks
        self._keep_alive_task = self.bot.loop.create_task(self._keep_session_alive())
        self._update_task = self.bot.loop.create_task(self._periodic_update())

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession()
        # Register the slash command group
        self.vrchat_group = app_commands.Group(name="vrchat", description="VRChat related commands")
        self.bot.tree.add_command(self.vrchat_group)
        log.info("VRChat cog loaded.")

    async def cog_unload(self) -> None:
        if self._keep_alive_task:
            self._keep_alive_task.cancel()
        if self._update_task:
            self._update_task.cancel()
        if self.session:
            await self.session.close()
        # Remove the group from tree
        self.bot.tree.remove_command(self.vrchat_group.name)
        log.info("VRChat cog unloaded.")

    async def _keep_session_alive(self) -> None:
        """Keep the aiohttp session alive; recreate if closed."""
        while not self.bot.is_closed():
            await asyncio.sleep(300)
            if self.session and self.session.closed:
                self.session = aiohttp.ClientSession()
                log.debug("Recreated VRChat aiohttp session.")

    async def _periodic_update(self) -> None:
        """Fetch instances every 2 minutes and store for dashboard; also post to Discord."""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                instances = await self._fetch_instances()
                self.latest_instances = {inst.get("id", str(i)): inst for i, inst in enumerate(instances)}
                await self._post_to_discord(instances)
            except Exception as e:
                log.error(f"Error in periodic VRChat update: {e}")
            await asyncio.sleep(120)  # 2 minutes

    async def _fetch_instances(self) -> List[Dict[str, Any]]:
        """Fetch raw instances from VRChat API."""
        if not self.cookie:
            return []
        if not self.session:
            return []
        url = f"https://vrchat.com/api/1/groups/{self.group_id}/instances"
        try:
            async with self.session.get(url, headers=self._get_headers(), timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data if isinstance(data, list) else []
                else:
                    text = await resp.text()
                    log.warning(f"VRChat API returned {resp.status}: {text}")
                    return []
        except asyncio.TimeoutError:
            return []
        except Exception as e:
            log.error(f"Exception fetching VRChat instances: {e}")
            return []

    async def _post_to_discord(self, instances: List[Dict[str, Any]]) -> None:
        """Send formatted embed to target channel."""
        channel = self.bot.get_channel(self.target_channel_id)
        if channel is None:
            return
        if not instances:
            desc = "Aucune instance trouvée."
        else:
            lines = []
            for inst in instances[:10]:
                world = inst.get("world", {})
                name = world.get("name", "Monde inconnu")
                nid = inst.get("id", "??")
                n = int(inst.get("nUsers", 0))
                cap = int(inst.get("capacity", 0))
                status = "🟢" if n > 0 else "⚪"
                lines.append(f"{status} {name} ({n}/{cap}) `{nid}`")
            desc = "\n".join(lines)
            if len(instances) > 10:
                desc += f"\n…et {len(instances)-10} autres."
        embed = discord.Embed(
            title="📊 Instances du groupe Arkana",
            description=desc,
            colour=0x1ABC9C,
        )
        if self.vrchat_role_id:
            content = f"<@&{self.vrchat_role_id}>"
        else:
            content = None
        try:
            await channel.send(content=content, embed=embed)
        except discord.Forbidden:
            pass
        except Exception as e:
            log.error(f"Failed to send VRChat embed: {e}")

    def set_cookie(self, cookie: str) -> None:
        """Update the VRChat authentication cookie."""
        self.cookie = cookie
        if hasattr(self.bot, "vrchat_cookie"):
            self.bot.vrchat_cookie = cookie
        log.info("VRChat cookie updated via dashboard.")

    def get_current_instances(self) -> dict:
        """Return latest_instances cleaned for JSON."""
        result = {}
        for iid, data in self.latest_instances.items():
            world = data.get("world", {})
            result[iid] = {
                "name": world.get("name", "Inconnu"),
                "nUsers": data.get("nUsers", 0),
                "capacity": data.get("capacity", 0),
            }
        return result

    def _get_headers(self) -> dict:
        headers = {
            "User-Agent": "VRChat/2022.4.2p1 UnityPlayer/2021.3.15f1 (UnityWebRequest/1.0; libcurl)",
            "Accept": "application/json",
        }
        if self.cookie:
            headers["Cookie"] = f"auth={self.cookie}"
        return headers

    # Slash command definitions
    @app_commands.command(name="setcookie", description="Set your VRChat authentication cookie (auth cookie).")
    async def setcookie(self, interaction: discord.Interaction, cookie: str) -> None:
        self.set_cookie(cookie)
        if hasattr(self.bot, "vrchat_cookie"):
            self.bot.vrchat_cookie = cookie
        await interaction.response.send_message("VRChat cookie saved.", ephemeral=True)

    @app_commands.command(name="status", description="Show current VRChat authentication status.")
    async def status(self, interaction: discord.Interaction) -> None:
        if self.cookie:
            await interaction.response.send_message("VRChat cookie is set.", ephemeral=True)
        else:
            await interaction.response.send_message("VRChat cookie is NOT set.", ephemeral=True)

    @app_commands.command(name="instances", description="Show current instances of the Arkana group.")
    async def instances(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        instances = await self._fetch_instances()
        if not instances:
            await interaction.followup.send("No instances found or unable to fetch.", ephemeral=True)
            return
        lines = [f"**Arkana Group Instances** ({len(instances)} active):"]
        for inst in instances[:10]:
            name = inst.get("world", {}).get("name", "Unknown World")
            iid = inst.get("id", "??")
            n = int(inst.get("nUsers", 0))
            cap = int(inst.get("capacity", 0))
            status = "🟢" if n > 0 else "⚪"
            lines.append(f"{status} {name} ({n}/{cap}) `{iid}`")
        if len(instances) > 10:
            lines.append(f"...and {len(instances) - 10} more.")
        await interaction.followup.send("\n".join(lines), ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VRChatCog(bot))