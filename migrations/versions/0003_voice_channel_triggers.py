"""Add voice channel triggers support

Revision ID: 0003_voice_channel_triggers
Revises: 0002_temporary_voice_channels
Create Date: 2026-06-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_voice_channel_triggers"
down_revision = "0002_temporary_voice_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the voice_channel_triggers table
    op.create_table(
        "voice_channel_triggers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("guild_id", sa.Integer(), nullable=False),
        sa.Column("trigger_channel_id", sa.String(length=32), nullable=False),
        sa.Column("trigger_channel_name", sa.String(length=120), nullable=False),
        sa.Column("category_id", sa.String(length=32), nullable=True),
        sa.Column("user_limit", sa.Integer(), nullable=False),
        sa.Column("size_preset", sa.String(length=20), nullable=False),
        sa.Column("naming_template", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["guild_id"], ["guilds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_voice_channel_triggers_guild_id"),
        "voice_channel_triggers",
        ["guild_id"],
    )

    # Migrate existing data from voice_channel_settings to voice_channel_triggers
    # This creates a trigger for each existing create_channel_id
    connection = op.get_bind()
    
    # Get all voice_channel_settings
    result = connection.execute(
        sa.text("""
            SELECT vcs.id, vcs.guild_id, vcs.create_channel_ids, 
                   vcs.category_id, vcs.default_user_limit, 
                   vcs.naming_template, vcs.enabled
            FROM voice_channel_settings vcs
            WHERE vcs.enabled = 1
        """)
    )
    
    rows = result.fetchall()
    
    # For each guild with voice channel settings, create triggers
    for row in rows:
        guild_id, channel_ids_json, category_id, user_limit, naming_template, enabled = (
            row[1], row[2], row[3], row[4], row[5], row[6]
        )
        
        # Parse the JSON array of channel IDs
        if channel_ids_json:
            import json
            try:
                channel_ids = json.loads(channel_ids_json)
            except (json.JSONDecodeError, TypeError):
                channel_ids = []
        else:
            channel_ids = []
        
        # For each channel ID, create a trigger
        for idx, channel_id in enumerate(channel_ids):
            if channel_id:
                # Get the size preset based on user limit
                size_preset = "custom"
                presets = {
                    1: "solo", 2: "duo", 3: "trio", 
                    4: "squad", 5: "party", 10: "team"
                }
                for limit, preset_name in presets.items():
                    if limit == user_limit:
                        size_preset = preset_name
                        break
                
                connection.execute(
                    sa.text("""
                        INSERT INTO voice_channel_triggers 
                        (guild_id, trigger_channel_id, trigger_channel_name, 
                         category_id, user_limit, size_preset, naming_template, enabled,
                         created_at, updated_at)
                        VALUES (:guild_id, :channel_id, :channel_name, 
                                :category_id, :user_limit, :size_preset, :naming_template, :enabled,
                                datetime('now'), datetime('now'))
                    """),
                    {
                        "guild_id": guild_id,
                        "channel_id": str(channel_id),
                        "channel_name": f"Channel {idx + 1}",  # Placeholder name
                        "category_id": category_id,
                        "user_limit": user_limit,
                        "size_preset": size_preset,
                        "naming_template": naming_template,
                        "enabled": 1,
                    },
                )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_voice_channel_triggers_guild_id"),
        table_name="voice_channel_triggers",
    )
    op.drop_table("voice_channel_triggers")
