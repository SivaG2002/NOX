"""temporary voice channels

Revision ID: 0002_temporary_voice_channels
Revises: 0001_initial
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_temporary_voice_channels"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_channel_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("create_channel_id", sa.String(length=32), nullable=True),
        sa.Column("create_channel_ids", sa.JSON(), nullable=True),
        sa.Column("category_id", sa.String(length=32), nullable=True),
        sa.Column("default_user_limit", sa.Integer(), nullable=False),
        sa.Column("naming_template", sa.String(length=100), nullable=False),
        sa.Column("auto_delete", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_voice_channel_settings_guild_id"),
        "voice_channel_settings",
        ["guild_id"],
        unique=True,
    )

    op.create_table(
        "temporary_voice_channels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(length=32), nullable=False),
        sa.Column("owner_id", sa.String(length=32), nullable=False),
        sa.Column("owner_name", sa.String(length=120), nullable=False),
        sa.Column("user_limit", sa.Integer(), nullable=False),
        sa.Column("is_locked", sa.Boolean(), nullable=False),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_temporary_voice_channels_channel_id"),
        "temporary_voice_channels",
        ["channel_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_temporary_voice_channels_guild_id"),
        "temporary_voice_channels",
        ["guild_id"],
    )
    op.create_index(
        op.f("ix_temporary_voice_channels_owner_id"),
        "temporary_voice_channels",
        ["owner_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_temporary_voice_channels_owner_id"), table_name="temporary_voice_channels"
    )
    op.drop_index(
        op.f("ix_temporary_voice_channels_guild_id"), table_name="temporary_voice_channels"
    )
    op.drop_index(
        op.f("ix_temporary_voice_channels_channel_id"), table_name="temporary_voice_channels"
    )
    op.drop_table("temporary_voice_channels")
    op.drop_index(
        op.f("ix_voice_channel_settings_guild_id"), table_name="voice_channel_settings"
    )
    op.drop_table("voice_channel_settings")
