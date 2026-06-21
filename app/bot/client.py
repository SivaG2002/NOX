import logging
from datetime import UTC, datetime
from pathlib import Path

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class StreamNotificationBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        from app.bot.temporary_voice import TemporaryVoiceChannelCog

        await self.add_cog(TemporaryVoiceChannelCog(self))
        try:
            synced_commands = await self.tree.sync()
            logger.info(
                "discord_slash_commands_synced", extra={"count": len(synced_commands)}
            )
        except discord.HTTPException:
            logger.exception("discord_slash_command_sync_failed")
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
        embed_file_path: Path | None = None,
        embed_file_name: str | None = None,
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
        embed_file = (
            discord.File(str(embed_file_path), filename=embed_file_name or embed_file_path.name)
            if embed_file_path
            else None
        )
        try:
            return await channel.send(
                content=content or None,
                embed=embed,
                view=view,
                allowed_mentions=allowed_mentions,
                file=embed_file,
            )
        finally:
            if embed_file:
                embed_file.close()

    async def fetch_notification_message(
        self,
        *,
        channel_id: str,
        message_id: str,
    ) -> discord.Message | None:
        try:
            channel = self.get_channel(int(channel_id))
            if channel is None:
                channel = await self.fetch_channel(int(channel_id))
            if not hasattr(channel, "fetch_message"):
                raise ValueError(f"Channel {channel_id} does not support message fetching")
            return await channel.fetch_message(int(message_id))
        except discord.NotFound:
            return None

    async def delete_notification_message(
        self,
        *,
        channel_id: str,
        message_id: str,
    ) -> bool:
        message = await self.fetch_notification_message(
            channel_id=channel_id,
            message_id=message_id,
        )
        if message is None:
            return False
        try:
            await message.delete()
        except discord.NotFound:
            return False
        return True

    async def mark_notification_stream_ended(
        self,
        *,
        channel_id: str,
        message_id: str,
    ) -> bool:
        message = await self.fetch_notification_message(
            channel_id=channel_id,
            message_id=message_id,
        )
        if message is None:
            return False

        embed = message.embeds[0].copy() if message.embeds else discord.Embed()
        embed.colour = discord.Colour.dark_grey()
        embed.timestamp = datetime.now(UTC)
        if embed.title:
            ended_title = f"{embed.title} - Stream Ended"
            embed.title = ended_title[:256]
        else:
            embed.title = "Stream Ended"
        if len(embed.fields) < 25:
            embed.add_field(name="Status", value="Stream Ended", inline=True)

        try:
            await message.edit(embed=embed, view=None)
        except discord.NotFound:
            return False
        return True

    async def list_text_channels(self, guild_id: str) -> list[dict[str, str]]:
        guild = self.get_guild(int(guild_id))
        if guild is None:
            return []
        return [{"id": str(channel.id), "name": channel.name} for channel in guild.text_channels]

    async def list_voice_channels(self, guild_id: str) -> list[dict[str, str]]:
        guild = self.get_guild(int(guild_id))
        if guild is None:
            return []
        return [
            {"id": str(channel.id), "name": channel.name} for channel in guild.voice_channels
        ]

    async def list_categories(self, guild_id: str) -> list[dict[str, str]]:
        guild = self.get_guild(int(guild_id))
        if guild is None:
            return []
        return [{"id": str(category.id), "name": category.name} for category in guild.categories]

    async def list_roles(self, guild_id: str) -> list[dict[str, str]]:
        guild = self.get_guild(int(guild_id))
        if guild is None:
            return []
        roles = [role for role in guild.roles if not role.is_default()]
        return [
            {"id": str(role.id), "name": role.name}
            for role in sorted(roles, key=lambda r: r.position)
        ]
