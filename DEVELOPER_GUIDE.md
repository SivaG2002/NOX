# Voice Channel Triggers - Developer Quick Reference

## Quick Links

| Item | Location |
|------|----------|
| Model | `app/models/voice_channel_trigger.py` |
| Service CRUD | `app/services/temporary_voice_channels.py` (lines 172-258) |
| Dashboard Routes | `app/dashboard/routes.py` (lines 340-493) |
| Templates | `app/templates/guilds/voice.html` |
| JavaScript | `app/static/js/voice_channels.js` |
| Migration | `migrations/versions/0003_voice_channel_triggers.py` |

## Database Schema Quick View

```sql
CREATE TABLE voice_channel_triggers (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER NOT NULL,
    trigger_channel_id VARCHAR(32) NOT NULL,
    trigger_channel_name VARCHAR(120) NOT NULL,
    category_id VARCHAR(32),
    user_limit INTEGER NOT NULL,
    size_preset VARCHAR(20) NOT NULL,
    naming_template VARCHAR(100) NOT NULL,
    enabled BOOLEAN NOT NULL,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (guild_id) REFERENCES guilds(id) ON DELETE CASCADE
);

CREATE INDEX ix_voice_channel_triggers_guild_id 
ON voice_channel_triggers(guild_id);
```

## Common Operations

### Get all triggers for a guild
```python
triggers = await list_voice_channel_triggers(db, guild_id)
```

### Find trigger that matches a channel
```python
trigger = await get_voice_channel_trigger_by_channel(db, guild_id, channel_id)
```

### Create new trigger
```python
trigger = await create_voice_channel_trigger(
    db,
    guild_pk=guild_id,
    trigger_channel_id="123456789",
    trigger_channel_name="Create Squad",
    category_id="987654321",
    user_limit=4,
    size_preset="squad",
    naming_template="{owner}'s Squad",
    enabled=True
)
await db.commit()
```

### Update trigger
```python
trigger = await update_voice_channel_trigger(
    db,
    guild_id,
    trigger_id,
    user_limit=8,
    size_preset="custom"
)
await db.commit()
```

### Delete trigger
```python
deleted = await delete_voice_channel_trigger(db, guild_id, trigger_id)
await db.commit()
```

## Bot Integration

When member joins trigger channel, flow is:
```python
# In bot/temporary_voice.py - on_voice_state_update()
# Calls:
service.create_channel_for_join(db, member, channel)

# Which calls:
trigger = await get_voice_channel_trigger_by_channel(db, guild_id, channel.id)

# Then uses trigger's configuration:
# - trigger.user_limit
# - trigger.naming_template
# - trigger.category_id
```

## Form Fields in Dashboard

### Add Trigger Form
```html
<input name="trigger_channel_id" required> <!-- Discord channel ID -->
<input name="trigger_channel_name"> <!-- Display name -->
<select name="category_id"> <!-- Optional category -->
<select name="size_preset"> <!-- Preset or "custom" -->
<input name="custom_user_limit"> <!-- Only if size_preset="custom" -->
<input name="naming_template"> <!-- Template string -->
<input name="enabled" type="checkbox"> <!-- Enabled status -->
```

### Modal Edit Form
Same fields, auto-populated from button data attributes:
```
data-trigger-channel-name
data-trigger-category-id
data-trigger-user-limit
data-trigger-size-preset
data-trigger-template
data-trigger-enabled
```

## Size Preset Constant

```python
VOICE_SIZE_PRESETS = {
    "solo": ("Solo", 1),
    "duo": ("Duo", 2),
    "trio": ("Trio", 3),
    "squad": ("Squad", 4),
    "party": ("Party", 5),
    "team": ("Team", 10),
    "custom": ("Custom", 4),
}
```

## Template Variables

```
{owner}        → Member's display name or username
{username}     → Member's Discord username
{display_name} → Member's server nickname if set
{guild}        → Guild/server name
```

Example: `"{owner}'s {guild} Channel"` 

## Query Examples

### Get trigger with highest user limit
```python
result = await db.execute(
    select(VoiceChannelTrigger)
    .where(VoiceChannelTrigger.guild_id == guild_id)
    .order_by(desc(VoiceChannelTrigger.user_limit))
    .limit(1)
)
trigger = result.scalar_one_or_none()
```

### Count enabled triggers
```python
count = await db.scalar(
    select(func.count(VoiceChannelTrigger.id))
    .where(
        VoiceChannelTrigger.guild_id == guild_id,
        VoiceChannelTrigger.enabled.is_(True)
    )
)
```

### Find duplicate channel IDs (should not happen)
```python
result = await db.execute(
    select(VoiceChannelTrigger.trigger_channel_id, func.count())
    .where(VoiceChannelTrigger.guild_id == guild_id)
    .group_by(VoiceChannelTrigger.trigger_channel_id)
    .having(func.count() > 1)
)
duplicates = result.all()
```

## Error Handling

```python
try:
    trigger = await create_voice_channel_trigger(db, ...)
    await db.commit()
except Exception as e:
    await db.rollback()
    # Log error, flash message to user
    flash(request, f"Error: {e}", "danger")
```

## Validation Rules

- `trigger_channel_id`: Non-empty string, length ≤ 32
- `user_limit`: Integer, 0-99 (clamped by `clamp_user_limit()`)
- `naming_template`: String, length ≤ 100 (can contain variables)
- `category_id`: String or None, length ≤ 32
- `size_preset`: One of the keys in `VOICE_SIZE_PRESETS`
- `enabled`: Boolean

## Logging Events

Create trigger event:
```python
await log_voice_event(
    db,
    guild_pk=guild_id,
    event_type="voice_trigger_created",  # Custom event type
    message=f"Created trigger for channel {trigger.trigger_channel_name}",
    metadata={
        "trigger_id": trigger.id,
        "trigger_channel_id": trigger.trigger_channel_id,
        "user_limit": trigger.user_limit,
    },
)
```

## Testing Checklist

- [ ] Add trigger channel successfully
- [ ] Edit trigger field values
- [ ] Delete trigger with confirmation
- [ ] Join trigger channel in Discord
- [ ] Verify created channel matches trigger config
- [ ] Verify channel name uses template
- [ ] Verify user limit applied
- [ ] Verify category used
- [ ] Check metrics (should show created channel)
- [ ] Disable trigger and verify no creation
- [ ] Enable trigger again
- [ ] Multiple triggers in one guild work independently

## Performance Tips

- Triggers are cached queries by channel ID
- Index on guild_id is automatic
- No N+1 issues with proper eager loading
- Metrics queries use aggregation

## Migration Notes

If you need to modify the migration:
1. Backup database first
2. Downgrade: `alembic downgrade -1`
3. Edit migration file
4. Re-upgrade: `alembic upgrade head`
5. Test thoroughly

## Debugging Commands

```bash
# Check current migration version
alembic current

# Show migration history
alembic history

# Show what would run
alembic upgrade head --sql

# Downgrade one migration
alembic downgrade -1
```

## Related Classes

- `VoiceChannelTrigger` - SQLAlchemy model
- `Guild` - Has relationship: `voice_channel_triggers`
- `TemporaryVoiceChannel` - Actual created channels
- `VoiceChannelSettings` - Legacy settings (still exists)

## Related Routes

- `GET /dashboard/{guild_id}/voice` - View all triggers
- `POST /dashboard/{guild_id}/voice-triggers/create` - Create
- `POST /dashboard/{guild_id}/voice-triggers/{id}/update` - Update
- `POST /dashboard/{guild_id}/voice-triggers/{id}/delete` - Delete
- `POST /dashboard/{guild_id}/voice` - Save global settings

## UI Components

- Triggers table with inline actions
- Add trigger form (collapsible panel)
- Edit modal (Bootstrap modal)
- Size preset selector with sync
- Template variable reference
- Enable/disable badges

## Dependencies

```python
from app.models import VoiceChannelTrigger
from app.services.temporary_voice_channels import (
    create_voice_channel_trigger,
    update_voice_channel_trigger,
    delete_voice_channel_trigger,
    list_voice_channel_triggers,
    get_voice_channel_trigger_by_channel,
)
```
