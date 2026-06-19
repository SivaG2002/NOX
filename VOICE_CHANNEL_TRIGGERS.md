# Voice Channel Trigger System - Implementation Guide

## Overview

This upgrade redesigns the Temporary Voice Channel system to support independent trigger channels with separate configurations. Previously, all trigger channels shared a single configuration. Now, each trigger channel can have its own user limit, category, and naming template.

## What's Changed

### 1. Database Schema

#### New Table: `voice_channel_triggers`
```
id                   - Primary key
guild_id             - Foreign key to guilds table
trigger_channel_id   - Discord voice channel ID (string, 32 chars)
trigger_channel_name - Human-readable channel name
category_id          - Target category (optional)
user_limit           - Max users allowed in created channel (0-99)
size_preset          - Size preset name (solo, duo, trio, squad, party, team, custom)
naming_template      - Template for naming created channels
enabled              - Boolean flag
created_at           - Timestamp
updated_at           - Timestamp
```

**Size Presets:**
- solo = 1 user
- duo = 2 users
- trio = 3 users
- squad = 4 users
- party = 5 users
- team = 10 users
- custom = user-defined

### 2. Data Migration

The Alembic migration (`0003_voice_channel_triggers.py`) automatically converts existing settings:
- For each enabled guild in `voice_channel_settings`, it creates individual `voice_channel_triggers` records
- Each existing `create_channel_id` becomes a separate trigger
- Settings are preserved: category, naming_template, user_limit
- Size preset is inferred from user_limit

### 3. Dashboard Changes

#### Voice Channel Page: `/dashboard/{guild_id}/voice`

**Left Column:**
- **Voice Channel Settings Panel**
  - Enable/Disable toggle
  - Auto Delete toggle
  - Save button

- **Add Trigger Channel Panel**
  - Trigger Voice Channel dropdown (required)
  - Category dropdown (optional)
  - Size preset dropdown (with custom option)
  - Custom limit input (shows when custom selected)
  - Naming template input
  - Enable toggle
  - Add button

**Right Column:**
- **Trigger Channels Table**
  - Channel Name
  - Size (user limit)
  - Category
  - Naming Template (truncated)
  - Enabled/Disabled badge
  - Edit & Delete buttons

- **Active Temporary Channels Table** (unchanged)
  - Lists currently active temporary voice channels

### 4. API Routes

#### Create Trigger
```
POST /dashboard/{guild_id}/voice-triggers/create
```

#### Update Trigger
```
POST /dashboard/{guild_id}/voice-triggers/{trigger_id}/update
```

#### Delete Trigger
```
POST /dashboard/{guild_id}/voice-triggers/{trigger_id}/delete
```

### 5. Backend Changes

#### New CRUD Functions in `temporary_voice_channels.py`

```python
async def get_voice_channel_trigger(db, guild_pk, trigger_id)
async def get_voice_channel_trigger_by_channel(db, guild_pk, channel_id)
async def list_voice_channel_triggers(db, guild_pk, enabled_only=False)
async def create_voice_channel_trigger(db, *, guild_pk, trigger_channel_id, ...)
async def update_voice_channel_trigger(db, guild_pk, trigger_id, ...)
async def delete_voice_channel_trigger(db, guild_pk, trigger_id)
```

#### Updated Service Logic

`create_channel_for_join()` now:
1. Looks up the trigger channel in `voice_channel_triggers` table
2. Uses that trigger's specific configuration (not shared settings)
3. Logs the trigger_id in metadata

### 6. Bot Event Handler

The Discord bot's `on_voice_state_update` handler automatically uses the new trigger system:
1. When a member joins a voice channel
2. Service looks for matching `VoiceChannelTrigger`
3. Uses that trigger's configuration to create the temporary channel
4. Member is moved to the created channel

No changes needed in `bot/temporary_voice.py` - it uses the updated service layer.

### 7. Dashboard UI/UX

#### Edit Modal
- Click "Edit" on any trigger to open a modal
- Modal shows all trigger fields
- Change any field and click "Save Changes"
- Modal submits to `/voice-triggers/{trigger_id}/update`

#### Delete Confirmation
- Click "Delete" button
- JavaScript confirms action
- Form submits to `/voice-triggers/{trigger_id}/delete`

#### Size Presets
- Selecting a preset auto-fills custom limit input
- Custom option allows manual entry
- JavaScript syncs both preset dropdowns (add form and edit modal)

### 8. Backward Compatibility

#### Old Settings Still Exist
- `VoiceChannelSettings` table remains unchanged
- `enabled` and `auto_delete` flags still control voice channel system
- Old multi-select fields persist for reference

#### Migration Strategy
1. Run Alembic: `alembic upgrade head`
2. Existing triggers are created automatically
3. System works with new trigger model
4. Old settings table is not modified

### 9. Logging & Metrics

#### Logging
- Events logged to `NotificationLog` table
- Platform: "discord"
- Event types:
  - `voice_channel_created`: Includes trigger_id in metadata
  - `voice_channel_deleted`
  - Other owner-change events

#### Metrics (unchanged)
- Active Temporary Channels count
- Channels Created Today
- Channels Deleted Today
- Most Active Owners (top 5)

### 10. Example Workflows

#### Creating Multiple Independent Triggers

1. **Trigger: "🎮 Create Duo"**
   - Size: 2
   - Naming Template: `{owner}'s Duo`
   - Category: General

2. **Trigger: "🎮 Create Squad"**
   - Size: 4
   - Naming Template: `{owner}'s Squad`
   - Category: Gaming

3. **Trigger: "🎮 Create Team"**
   - Size: 10
   - Naming Template: `{owner}'s Team`
   - Category: Events

When member joins "Create Duo":
- Creates channel "Siva's Duo" with limit 2 in General category

When same member joins "Create Squad":
- Creates channel "Siva's Squad" with limit 4 in Gaming category

## Installation Steps

1. **Backup Database**
   ```bash
   cp streambot.sqlite3 streambot.sqlite3.backup
   ```

2. **Run Migration**
   ```bash
   alembic upgrade head
   ```

3. **Restart Application**
   - Old settings are preserved
   - New trigger system is active
   - Existing triggers created from old settings

4. **Test**
   - Visit dashboard voice settings page
   - Verify triggers are displayed
   - Test adding/editing/deleting triggers
   - Test joining trigger channels in Discord

## Rollback

If needed, rollback to previous version:
```bash
alembic downgrade -1
```

This removes the triggers table but doesn't modify `voice_channel_settings`.

## File Changes Summary

### New Files
- `app/models/voice_channel_trigger.py` - New model
- `migrations/versions/0003_voice_channel_triggers.py` - Migration

### Modified Files
- `app/models/__init__.py` - Added VoiceChannelTrigger export
- `app/models/guild.py` - Added voice_channel_triggers relationship
- `app/services/temporary_voice_channels.py` - Added CRUD functions, updated create_channel_for_join()
- `app/dashboard/routes.py` - Added trigger management routes, updated voice_channels_page
- `app/templates/guilds/voice.html` - Redesigned UI with trigger table and modal
- `app/static/js/voice_channels.js` - Added modal handling and field sync logic

## Future Enhancements

1. **Bulk Operations**: Import/export trigger configurations
2. **Templates**: Save and reuse trigger templates across guilds
3. **Analytics**: Track which triggers are used most
4. **Permissions**: Role-based access to specific triggers
5. **Scheduling**: Time-based trigger activation
