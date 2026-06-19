import logging
from collections.abc import Awaitable, Callable

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.services.temporary_voice_channels import TemporaryVoiceChannelService, VoiceChannelError

logger = logging.getLogger(__name__)


class TemporaryVoiceChannelCog(commands.Cog):
    vc = app_commands.Group(name="vc", description="Manage your temporary voice channel")

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.service = TemporaryVoiceChannelService()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        await self.service.handle_voice_state_update(member, before, after)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel) -> None:
        await self.service.handle_channel_delete(channel)

    @vc.command(name="rename", description="Rename your temporary voice channel")
    @app_commands.describe(name="New channel name")
    async def rename(self, interaction: discord.Interaction, name: str) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.rename_channel(db, member, name),
            "Channel renamed.",
        )

    @vc.command(name="limit", description="Change your temporary voice channel user limit")
    @app_commands.describe(number="User limit from 0 to 99. Use 0 for no limit.")
    async def limit(self, interaction: discord.Interaction, number: int) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.set_user_limit(db, member, number),
            f"User limit changed to {max(0, min(99, number))}.",
        )

    @vc.command(name="lock", description="Lock your temporary voice channel")
    async def lock(self, interaction: discord.Interaction) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.set_locked(db, member, True),
            "Channel locked.",
        )

    @vc.command(name="unlock", description="Unlock your temporary voice channel")
    async def unlock(self, interaction: discord.Interaction) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.set_locked(db, member, False),
            "Channel unlocked.",
        )

    @vc.command(name="transfer", description="Transfer ownership to someone in your channel")
    @app_commands.describe(user="New temporary voice channel owner")
    async def transfer(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.transfer_owner(db, member, user),
            f"Ownership transferred to {user.display_name}.",
        )

    @vc.command(name="claim", description="Claim an abandoned temporary voice channel")
    async def claim(self, interaction: discord.Interaction) -> None:
        await self._run_member_command(
            interaction,
            lambda db, member: self.service.claim_channel(db, member),
            "Channel claimed.",
        )

    @vc.command(name="public", description="Make your temporary voice channel public")
    async def make_public(self, interaction: discord.Interaction) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.set_private(db, member, False),
            "Channel is now public.",
        )

    @vc.command(name="private", description="Make your temporary voice channel private")
    async def make_private(self, interaction: discord.Interaction) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.set_private(db, member, True),
            "Channel is now private.",
        )

    @vc.command(name="allow", description="Allow a user into your temporary voice channel")
    @app_commands.describe(user="User to allow")
    async def allow(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.allow_user(db, member, user),
            f"{user.display_name} can now join.",
        )

    @vc.command(name="deny", description="Deny a user from your temporary voice channel")
    @app_commands.describe(user="User to deny")
    async def deny(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.deny_user(db, member, user),
            f"{user.display_name} can no longer join.",
        )

    @vc.command(name="kick", description="Kick a member from your temporary voice channel")
    @app_commands.describe(user="Member to kick")
    async def kick(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self._run_owner_command(
            interaction,
            lambda db, member: self.service.kick_member(db, member, user),
            f"{user.display_name} was kicked.",
        )

    async def _run_owner_command(
        self,
        interaction: discord.Interaction,
        operation: Callable[[AsyncSession, discord.Member], Awaitable[object]],
        success_message: str,
    ) -> None:
        await self._run_member_command(interaction, operation, success_message)

    async def _run_member_command(
        self,
        interaction: discord.Interaction,
        operation: Callable[[AsyncSession, discord.Member], Awaitable[object]],
        success_message: str,
    ) -> None:
        if interaction.guild is None or not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Use this command inside a server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        async with AsyncSessionLocal() as db:
            try:
                await operation(db, interaction.user)
                await db.commit()
            except VoiceChannelError as exc:
                await db.rollback()
                await interaction.followup.send(str(exc), ephemeral=True)
                return
            except discord.Forbidden:
                await db.rollback()
                await interaction.followup.send(
                    "I need Manage Channels and Move Members permissions for that.",
                    ephemeral=True,
                )
                return
            except discord.HTTPException:
                await db.rollback()
                logger.exception("temporary_voice_channel_command_failed")
                await interaction.followup.send(
                    "Discord rejected that voice channel update.", ephemeral=True
                )
                return

        await interaction.followup.send(success_message, ephemeral=True)
