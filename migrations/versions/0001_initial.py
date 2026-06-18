"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guilds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_guilds_guild_id"), "guilds", ["guild_id"], unique=True)

    op.create_table(
        "embed_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False),
        sa.Column("footer_text", sa.String(length=256), nullable=True),
        sa.Column("author_text", sa.String(length=256), nullable=True),
        sa.Column("show_thumbnail", sa.Boolean(), nullable=False),
        sa.Column("show_preview", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_embed_templates_guild_id"), "embed_templates", ["guild_id"], unique=True)

    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("channel_id", sa.String(length=32), nullable=True),
        sa.Column("role_id", sa.String(length=32), nullable=True),
        sa.Column("mention_everyone", sa.Boolean(), nullable=False),
        sa.Column("mention_here", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_settings_guild_id"),
        "notification_settings",
        ["guild_id"],
        unique=True,
    )

    op.create_table(
        "streamers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("streamer_name", sa.String(length=120), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "platform in ('twitch', 'youtube', 'kick')", name="ck_streamers_platform"
        ),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("guild_id", "platform", "streamer_name", name="uq_streamer_per_guild"),
    )
    op.create_index(op.f("ix_streamers_guild_id"), "streamers", ["guild_id"], unique=False)

    op.create_table(
        "notification_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("streamer_id", sa.Integer(), nullable=True),
        sa.Column("platform", sa.String(length=20), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("notification_message_id", sa.String(length=32), nullable=True),
        sa.Column("log_metadata", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["streamer_id"], ["streamers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notification_logs_event_type"), "notification_logs", ["event_type"])
    op.create_index(op.f("ix_notification_logs_guild_id"), "notification_logs", ["guild_id"])
    op.create_index(op.f("ix_notification_logs_streamer_id"), "notification_logs", ["streamer_id"])
    op.create_index(op.f("ix_notification_logs_timestamp"), "notification_logs", ["timestamp"])

    op.create_table(
        "stream_states",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("streamer_id", sa.Integer(), nullable=False),
        sa.Column("is_live", sa.Boolean(), nullable=False),
        sa.Column("stream_id", sa.String(length=128), nullable=True),
        sa.Column("notification_message_id", sa.String(length=32), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["streamer_id"], ["streamers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("streamer_id", name="uq_stream_state_streamer"),
    )
    op.create_index(op.f("ix_stream_states_guild_id"), "stream_states", ["guild_id"])
    op.create_index(op.f("ix_stream_states_streamer_id"), "stream_states", ["streamer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_stream_states_streamer_id"), table_name="stream_states")
    op.drop_index(op.f("ix_stream_states_guild_id"), table_name="stream_states")
    op.drop_table("stream_states")
    op.drop_index(op.f("ix_notification_logs_timestamp"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_streamer_id"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_guild_id"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_event_type"), table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_index(op.f("ix_streamers_guild_id"), table_name="streamers")
    op.drop_table("streamers")
    op.drop_index(op.f("ix_notification_settings_guild_id"), table_name="notification_settings")
    op.drop_table("notification_settings")
    op.drop_index(op.f("ix_embed_templates_guild_id"), table_name="embed_templates")
    op.drop_table("embed_templates")
    op.drop_index(op.f("ix_guilds_guild_id"), table_name="guilds")
    op.drop_table("guilds")

