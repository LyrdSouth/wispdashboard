import os
from dotenv import load_dotenv
import json
from datetime import datetime
from typing import Dict, Any
import requests
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
    """Get settings for a specific guild"""
    if guild_id is None:
        return {}
    
    try:
        # Check cache first
        if guild_id in settings_cache:
            return settings_cache[guild_id].copy()
        
        # Load from file if not in cache
        try:
            settings_file = get_file_path('settings.json')
            with open(settings_file, 'r') as f:
                all_settings = json.load(f)
                settings_cache.update(all_settings)
        except FileNotFoundError:
            # Create an empty settings file
            settings_file = get_file_path('settings.json')
            with open(settings_file, 'w') as f:
                json.dump({}, f)
            settings_cache[guild_id] = {}
        except json.JSONDecodeError:
            # Reset the file if it's corrupted
            settings_file = get_file_path('settings.json')
            with open(settings_file, 'w') as f:
                json.dump({}, f)
            settings_cache[guild_id] = {}
        
        # Initialize with defaults if not exist
        if guild_id not in settings_cache:
            settings_cache[guild_id] = {}
        
        # Return a copy to prevent unintended modifications
        settings = settings_cache.get(guild_id, {}).copy()
        
        # Ensure required fields exist
        if 'prefix' not in settings:
            settings['prefix'] = '?'
        if 'cogs' not in settings:
            settings['cogs'] = ['image', 'security']
        if 'command_count' not in settings:
            settings['command_count'] = 0
        if 'mod_actions' not in settings:
            settings['mod_actions'] = 0
        if 'activity' not in settings:
            settings['activity'] = []
        
        return settings
    except Exception as e:
        print(f"Error in get_guild_settings: {e}")
        # Return default settings on error
        return {
            'prefix': '?',
            'cogs': ['image', 'security'],
            'command_count': 0,
            'mod_actions': 0,
            'activity': []
        }

def update_guild_settings(guild_id: str, settings: Dict[str, Any]) -> bool:
    """Update settings for a specific guild"""
    try:
        # Store the last update time
        settings['last_updated'] = datetime.now().isoformat()
        
        # Make sure we preserve any server info we have
        if 'name' not in settings and guild_id in settings_cache and 'name' in settings_cache[guild_id]:
            settings['name'] = settings_cache[guild_id]['name']
        
        if 'icon' not in settings and guild_id in settings_cache and 'icon' in settings_cache[guild_id]:
            settings['icon'] = settings_cache[guild_id]['icon']
            
        if 'member_count' not in settings and guild_id in settings_cache and 'member_count' in settings_cache[guild_id]:
            settings['member_count'] = settings_cache[guild_id]['member_count']
        
        # Update cache
        settings_cache[guild_id] = settings.copy()
            
        # Save to local file
        try:
            settings_file = get_file_path('settings.json')
            with open(settings_file, 'r') as f:
                all_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_settings = {}
        
        # Update settings for this guild
        all_settings[guild_id] = settings
        
        # Save to file
        settings_file = get_file_path('settings.json')
        with open(settings_file, 'w') as f:
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

# This function is the key one for communicating with the remote bot on SillyDev
def sync_with_bot(guild_id: str, settings: Dict[str, Any]) -> bool:
    """Synchronize settings with the remote bot on SillyDev"""
    try:
        # Get config from environment variables with fallbacks
        bot_api_url = os.getenv('BOT_API_URL', 'http://45.90.13.151:6150/api')
        bot_token = os.getenv('DISCORD_TOKEN')
        
        headers = {
            'Authorization': f'Bearer {bot_token}',
            'Content-Type': 'application/json'
        }
        
        # Send settings to remote bot API
        response = requests.post(
            f"{bot_api_url}/settings/{guild_id}",
            headers=headers,
            json=settings,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"Successfully synced settings for guild {guild_id} with remote bot")
            return True
        else:
            print(f"Failed to sync settings with remote bot: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectTimeout:
        print(f"Connection to remote bot API timed out after 10 seconds")
        return False
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to remote bot API at {bot_api_url}")
        return False
    except Exception as e:
        print(f"Error syncing with remote bot: {e}")
        return False

# Get settings from remote bot directly
def get_bot_settings(guild_id: str) -> Dict[str, Any]:
    """Get settings directly from the remote bot"""
    try:
        bot_api_url = os.getenv('BOT_API_URL', 'http://45.90.13.151:6150/api')
        bot_token = os.getenv('DISCORD_TOKEN')
        
        headers = {
            'Authorization': f'Bearer {bot_token}'
        }
        
        response = requests.get(
            f"{bot_api_url}/settings/{guild_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get settings from remote bot: {response.status_code} - {response.text}")
            return {}
    except requests.exceptions.ConnectTimeout:
        print(f"Connection to remote bot API timed out after 10 seconds")
        return {}
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to remote bot API at {bot_api_url}")
        return {}
    except Exception as e:
        print(f"Error getting settings from remote bot: {e}")
        return {}

def get_bot_channels(guild_id: str) -> list:
    """Get channels directly from the remote bot"""
    try:
        bot_api_url = os.getenv('BOT_API_URL', 'http://45.90.13.151:6150/api')
        bot_token = os.getenv('DISCORD_TOKEN')
        
        headers = {
            'Authorization': f'Bearer {bot_token}'
        }
        
        response = requests.get(
            f"{bot_api_url}/channels/{guild_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            channels = response.json()
            print(f"Got {len(channels)} channels from remote bot for guild {guild_id}")
            
            # Cache channels in local settings for backup
            try:
                settings = get_guild_settings(guild_id)
                settings['cached_channels'] = channels
                update_guild_settings(guild_id, settings)
                print(f"Cached {len(channels)} channels for guild {guild_id}")
            except Exception as e:
                print(f"Error caching channels: {e}")
            
            return channels
        else:
            print(f"Failed to get channels from remote bot: {response.status_code} - {response.text}")
            
            # Fall back to cached channels
            settings = get_guild_settings(guild_id)
            if 'cached_channels' in settings:
                print(f"Using {len(settings['cached_channels'])} cached channels for guild {guild_id}")
                return settings['cached_channels']
            
            return []
    except requests.exceptions.ConnectTimeout:
        print(f"Connection to remote bot API timed out after 10 seconds")
        
        # Fall back to cached channels
        settings = get_guild_settings(guild_id)
        if 'cached_channels' in settings:
            print(f"Using {len(settings['cached_channels'])} cached channels for guild {guild_id}")
            return settings['cached_channels']
        
        return []
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to remote bot API at {bot_api_url}")
        
        # Fall back to cached channels
        settings = get_guild_settings(guild_id)
        if 'cached_channels' in settings:
            print(f"Using {len(settings['cached_channels'])} cached channels for guild {guild_id}")
            return settings['cached_channels']
        
        return []
    except Exception as e:
        print(f"Error getting channels from remote bot: {e}")
        
        # Fall back to cached channels
        settings = get_guild_settings(guild_id)
        if 'cached_channels' in settings:
            print(f"Using {len(settings['cached_channels'])} cached channels for guild {guild_id}")
            return settings['cached_channels']
        
        return [] 