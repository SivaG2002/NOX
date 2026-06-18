import logging

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class StreamNotificationBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        logger.info("discord_bot_setup")

    async def on_ready(self) -> None:
        logger.info("discord_bot_ready", extra={"bot_user": str(self.user)})

    async def send_stream_embed(
        self,
        *,
        guild_id: str,
        channel_id: str,
        content: str | None,
        embed: discord.Embed,
        watch_url: str,
        allow_everyone: bool,
        allow_roles: bool,
    ) -> discord.Message:
        channel = self.get_channel(int(channel_id))
        if channel is None:
            channel = await self.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.abc.Messageable):
            raise ValueError(f"Channel {channel_id} is not messageable")

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Watch Stream", url=watch_url))
        allowed_mentions = discord.AllowedMentions(
            everyone=allow_everyone,
            roles=allow_roles,
            users=False,
        )
        return await channel.send(
            content=content or None,
            embed=embed,
            view=view,
            allowed_mentions=allowed_mentions,
        )

    async def list_text_channels(self, guild_id: str) -> list[dict[str, str]]:
        guild = self.get_guild(int(guild_id))
        if guild is None:
            return []
        return [{"id": str(channel.id), "name": channel.name} for channel in guild.text_channels]

    async def list_roles(self, guild_id: str) -> list[dict[str, str]]:
        guild = self.get_guild(int(guild_id))
        if guild is None:
            return []
        roles = [role for role in guild.roles if not role.is_default()]
        return [{"id": str(role.id), "name": role.name} for role in sorted(roles, key=lambda r: r.position)]

