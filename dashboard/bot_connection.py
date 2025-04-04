import os
from dotenv import load_dotenv
import json
from datetime import datetime
from typing import Dict, Any
import traceback

# Load environment variables
load_dotenv()

# Settings cache
settings_cache = {}

# Get the full path for a file in the dashboard directory
def get_file_path(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

# Ensure settings file exists
def ensure_settings_file():
    try:
        settings_file = get_file_path('settings.json')
        if not os.path.exists(settings_file):
            with open(settings_file, 'w') as f:
                json.dump({}, f)
            print(f"Created empty settings file: {settings_file}")
        return True
    except Exception as e:
        print(f"Error creating settings file: {e}")
        return False

# Initialize settings file
ensure_settings_file()

def get_guild_settings(guild_id: str) -> Dict[str, Any]:
    """Get settings for a guild"""
    try:
        if os.path.exists(get_file_path('settings.json')):
            with open(get_file_path('settings.json'), 'r') as f:
                all_settings = json.load(f)
                return all_settings.get(str(guild_id), {})
    except Exception as e:
        print(f"Error loading guild settings: {e}")
    return {}

def update_guild_settings(guild_id: str, settings: Dict[str, Any]) -> bool:
    """Update settings for a guild"""
    try:
        # Create settings directory if it doesn't exist
        os.makedirs(os.path.dirname(get_file_path('settings.json')), exist_ok=True)
        
        # Load existing settings
        if os.path.exists(get_file_path('settings.json')):
            with open(get_file_path('settings.json'), 'r') as f:
                all_settings = json.load(f)
        else:
            all_settings = {}
        
        # Update settings for this guild
        all_settings[str(guild_id)] = settings
        
        # Save back to file
        with open(get_file_path('settings.json'), 'w') as f:
            json.dump(all_settings, f, indent=4)
            
        print(f"Successfully saved settings for guild {guild_id}")
        return True
    except Exception as e:
        print(f"Error updating guild settings: {e}")
        return False

# Store guild info received from Discord in our settings
def store_guild_info(guild_id: str, guild_data: Dict[str, Any]) -> None:
    """Store guild information from Discord API in our settings"""
    try:
        print(f"Storing guild info for {guild_id}: {guild_data.get('name')}")
        print(f"Guild data: {json.dumps(guild_data, indent=2)}")
        
        # Get current settings
        settings = get_guild_settings(guild_id)
        
        # Update with guild data
        if 'name' in guild_data:
            settings['name'] = guild_data['name']
            print(f"Stored name: {guild_data['name']}")
        
        if 'icon' in guild_data and guild_data['icon']:
            settings['icon'] = guild_data['icon']
            print(f"Stored icon: {guild_data['icon']}")
            
        if 'owner_id' in guild_data:
            settings['owner_id'] = guild_data['owner_id']
            
        # Try different member count fields that Discord might provide
        if 'approximate_member_count' in guild_data and guild_data['approximate_member_count']:
            settings['member_count'] = guild_data['approximate_member_count']
            print(f"Stored member count from approximate_member_count: {guild_data['approximate_member_count']}")
        elif 'member_count' in guild_data and guild_data['member_count']:
            settings['member_count'] = guild_data['member_count']
            print(f"Stored member count from member_count: {guild_data['member_count']}")
        elif 'approximate_presence_count' in guild_data and guild_data['approximate_presence_count']:
            # If we don't have member count but have presence count, use that as an estimate
            settings['member_count'] = guild_data['approximate_presence_count']
            print(f"Stored member count from approximate_presence_count: {guild_data['approximate_presence_count']}")
        
        # Save the updated settings
        update_guild_settings(guild_id, settings)
        
        print(f"Successfully stored guild info for {guild_id}: {settings.get('name', 'Unknown')}")
    except Exception as e:
        print(f"Error storing guild info: {e}")
        print(traceback.format_exc())

# Get bot and guild data combined
def get_combined_guild_data(guild_id: str) -> Dict[str, Any]:
    """Get combined bot settings and guild data"""
    settings = get_guild_settings(guild_id)
    
    # Build a response with settings and any stored guild info
    result = {
        'id': guild_id,
        'name': settings.get('name', 'Unknown Server'),
        'icon': settings.get('icon'),
        'owner_id': settings.get('owner_id'),
        'member_count': settings.get('member_count', 0),  # Always include member_count, default to 0
        'settings': {
            'prefix': settings.get('prefix', '?'),
            'cogs': settings.get('cogs', ['image', 'security']),
            'command_count': settings.get('command_count', 0),
            'mod_actions': settings.get('mod_actions', 0),
            'log_channel': settings.get('log_channel'),
            'activity': settings.get('activity', []),
            'member_count': settings.get('member_count', 0)  # Include in settings too for backward compatibility
        }
    }
    
    print(f"Combined guild data for {guild_id}: member_count = {result['member_count']}")
    return result

def increment_command_count(guild_id: str):
    """Increment command count for a specific guild"""
    try:
        settings = get_guild_settings(guild_id)
        settings['command_count'] = settings.get('command_count', 0) + 1
        update_guild_settings(guild_id, settings)
    except Exception as e:
        print(f"Error incrementing command count: {e}")

def increment_mod_action(guild_id: str):
    """Increment moderation action count for a specific guild"""
    try:
        settings = get_guild_settings(guild_id)
        settings['mod_actions'] = settings.get('mod_actions', 0) + 1
        update_guild_settings(guild_id, settings)
    except Exception as e:
        print(f"Error incrementing mod action: {e}")

def add_activity(guild_id: str, activity_data: Dict[str, Any]):
    """Add an activity entry to the guild's settings"""
    try:
        settings = get_guild_settings(guild_id)
        
        if 'activity' not in settings:
            settings['activity'] = []
        
        # Add timestamp if not present
        if 'timestamp' not in activity_data:
            activity_data['timestamp'] = datetime.now().isoformat()
        
        settings['activity'].insert(0, activity_data)
        # Keep only the most recent 50 activities
        settings['activity'] = settings['activity'][:50]
        
        update_guild_settings(guild_id, settings)
    except Exception as e:
        print(f"Error adding activity: {e}")

# Since we're running on the same server, we can just use the local settings
def sync_with_bot(guild_id: str, settings: dict) -> bool:
    """Update settings locally since we're running on the same server"""
    try:
        return update_guild_settings(guild_id, settings)
    except Exception as e:
        print(f"Error syncing settings: {e}")
        return False

def get_bot_settings(guild_id: str) -> dict:
    """Get settings from local storage since we're running on the same server"""
    return get_guild_settings(guild_id)

def get_bot_channels(guild_id: str) -> list:
    """Get channels from local storage since we're running on the same server"""
    settings = get_guild_settings(guild_id)
    return settings.get('cached_channels', []) 