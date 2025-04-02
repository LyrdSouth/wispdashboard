import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import requests

# Load environment variables
load_dotenv()

# Settings cache
settings_cache = {}

# Get the full path for a file in the dashboard directory
def get_file_path(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

# Bot API connection details
BOT_API_URL = "http://45.90.13.151:6150/api"
BOT_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_API_TIMEOUT = 10  # Increased timeout from 5 to 10 seconds

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

class BotConnection:
    def __init__(self):
        self.bot_token = os.getenv('DISCORD_TOKEN')
        self.dashboard_url = os.getenv('DASHBOARD_URL', 'https://wispbot.site')
        self._settings_cache = {}
        self._bot = None

# Create an instance of BotConnection for set_bot
set_bot = BotConnection()

# Direct connection to the bot API
def sync_with_bot(guild_id: str, settings: Dict[str, Any]) -> bool:
    """Synchronize settings with the bot"""
    try:
        headers = {
            'Authorization': f'Bearer {BOT_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Send settings to bot API
        response = requests.post(
            f"{BOT_API_URL}/settings/{guild_id}",
            headers=headers,
            json=settings,
            timeout=BOT_API_TIMEOUT
        )
        
        if response.status_code == 200:
            print(f"Successfully synced settings for guild {guild_id} with bot")
            return True
        else:
            print(f"Failed to sync settings with bot: {response.status_code} - {response.text}")
            return False
    except requests.exceptions.ConnectTimeout:
        print(f"Connection to bot API timed out after {BOT_API_TIMEOUT} seconds")
        return False
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to bot API at {BOT_API_URL}")
        return False
    except Exception as e:
        print(f"Error syncing with bot: {e}")
        return False

# Get settings from bot directly
def get_bot_settings(guild_id: str) -> Dict[str, Any]:
    """Get settings directly from the bot"""
    try:
        headers = {
            'Authorization': f'Bearer {BOT_TOKEN}'
        }
        
        response = requests.get(
            f"{BOT_API_URL}/settings/{guild_id}",
            headers=headers,
            timeout=BOT_API_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get settings from bot: {response.status_code} - {response.text}")
            return {}
    except requests.exceptions.ConnectTimeout:
        print(f"Connection to bot API timed out after {BOT_API_TIMEOUT} seconds")
        return {}
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to bot API at {BOT_API_URL}")
        return {}
    except Exception as e:
        print(f"Error getting settings from bot: {e}")
        return {}

def get_guild_settings(guild_id: str) -> Dict[str, Any]:
    """Get settings for a specific guild"""
    if guild_id is None:
        return {}
    
    try:
        # First try to get settings from the bot
        bot_settings = get_bot_settings(guild_id)
        if bot_settings:
            # Update local cache with bot settings
            settings_cache[guild_id] = bot_settings
            return bot_settings
        
        # Fall back to local cache/file if bot is unavailable
        if guild_id not in settings_cache:
            # Load settings from file
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

def get_default_settings():
    """Get default settings for a new guild"""
    return {
        'prefix': '?',
        'cogs': ['moderation', 'utility', 'image'],
        'log_channel': None,
        'command_count': 0,
        'mod_actions': 0,
        'last_updated': datetime.now().isoformat()
    }

def get_prefix(guild_id):
    """Get prefix for a specific guild"""
    try:
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)
            return prefixes.get(str(guild_id), '?')
    except FileNotFoundError:
        return '?'

def get_enabled_cogs(guild_id):
    """Get enabled cogs for a specific guild"""
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
            return settings.get(str(guild_id), {}).get('cogs', ['moderation', 'utility', 'image'])
    except FileNotFoundError:
        return ['moderation', 'utility', 'image']

def get_log_channel(guild_id):
    """Get log channel for a specific guild"""
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
            return settings.get(str(guild_id), {}).get('log_channel')
    except FileNotFoundError:
        return None

def get_command_count(guild_id):
    """Get command count for a specific guild"""
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
            return settings.get(str(guild_id), {}).get('command_count', 0)
    except FileNotFoundError:
        return 0

def get_mod_action_count(guild_id):
    """Get moderation action count for a specific guild"""
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
            return settings.get(str(guild_id), {}).get('mod_actions', 0)
    except FileNotFoundError:
        return 0

def update_guild_settings(guild_id: str, settings: Dict[str, Any]) -> bool:
    """Update settings for a specific guild"""
    try:
        # Update cache
        settings_cache[guild_id] = settings.copy()
        
        # Try to sync with bot first
        if sync_with_bot(guild_id, settings):
            return True
            
        # Fall back to local file if bot sync fails
        # Save to local file as backup
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
        
        return True
    except Exception as e:
        print(f"Error updating settings: {e}")
        return False

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

async def notify_bot(self, guild_id: str, action: str, data: Dict[str, Any]):
    """Log action in server's activity feed"""
    try:
        settings = get_guild_settings(guild_id)
        
        # Add to activity history
        timestamp = datetime.now().isoformat()
        activity = {
            'timestamp': timestamp,
            'action': action,
            'data': data
        }
        
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, activity)
        # Keep only the most recent 50 activities
        settings['activity'] = settings['activity'][:50]
        
        # Apply the requested change to settings
        if action == 'prefix_update':
            settings['prefix'] = data.get('prefix', '?')
        elif action == 'cogs_update':
            settings['cogs'] = data.get('cogs', [])
        elif action == 'log_channel_update':
            settings['log_channel'] = data.get('channel_id')
        
        # Save updated settings
        update_guild_settings(guild_id, settings)
        
        # Try to send a notification in the log channel if one is set
        log_channel_id = settings.get('log_channel')
        if log_channel_id and self._bot:
            try:
                channel = self._bot.get_channel(int(log_channel_id))
                if channel:
                    action_text = {
                        'prefix_update': f"Prefix updated to `{data.get('prefix')}`",
                        'cogs_update': f"Enabled features updated: {', '.join(data.get('cogs', []))}",
                        'log_channel_update': f"Log channel updated"
                    }.get(action, f"Settings updated: {action}")
                    
                    embed = discord.Embed(
                        title="Dashboard Update",
                        description=action_text,
                        color=discord.Color.blue(),
                        timestamp=datetime.now()
                    )
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"Error sending log message: {e}")
        
        return True
    except Exception as e:
        print(f"Error logging activity: {e}")
        return False

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

# Get channels from bot directly
def get_bot_channels(guild_id: str) -> list:
    """Get channels directly from the bot"""
    try:
        headers = {
            'Authorization': f'Bearer {BOT_TOKEN}'
        }
        
        response = requests.get(
            f"{BOT_API_URL}/channels/{guild_id}",
            headers=headers,
            timeout=BOT_API_TIMEOUT
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed to get channels from bot: {response.status_code} - {response.text}")
            return []
    except requests.exceptions.ConnectTimeout:
        print(f"Connection to bot API timed out after {BOT_API_TIMEOUT} seconds")
        return []
    except requests.exceptions.ConnectionError:
        print(f"Could not connect to bot API at {BOT_API_URL}")
        return []
    except Exception as e:
        print(f"Error getting channels from bot: {e}")
        return [] 