"""custom thumbnails and notification cleanup

Revision ID: 0004_custom_thumbnails_and_notification_cleanup
Revises: 0003_voice_channel_triggers
Create Date: 2026-06-21
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_custom_thumbnails_and_notification_cleanup"
down_revision = "0003_voice_channel_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "embed_templates",
        sa.Column("custom_thumbnail_url", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "notification_settings",
        sa.Column(
            "delete_notification_on_end",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )
    op.add_column(
        "stream_states",
        sa.Column("last_notification_message_id", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "stream_states",
        sa.Column("last_notification_channel_id", sa.String(length=32), nullable=True),
    )
    op.execute(
        """
        UPDATE stream_states
        SET last_notification_message_id = notification_message_id
        WHERE notification_message_id IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("stream_states", "last_notification_channel_id")
    op.drop_column("stream_states", "last_notification_message_id")
    op.drop_column("notification_settings", "delete_notification_on_end")
    op.drop_column("embed_templates", "custom_thumbnail_url")
