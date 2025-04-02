import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
import aiohttp
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

# Load environment variables
load_dotenv()

# Bot instance
bot: Optional[commands.Bot] = None
settings_cache: Dict[str, Dict[str, Any]] = {}

def set_bot(bot_instance: commands.Bot):
    """Set the bot instance for the dashboard to use"""
    global bot
    bot = bot_instance

def get_guild_settings(guild_id: str) -> Dict[str, Any]:
    """Get settings for a specific guild"""
    if guild_id is None:
        return settings_cache
    
    if guild_id not in settings_cache:
        # Load settings from file
        try:
            with open('settings.json', 'r') as f:
                settings_cache.update(json.load(f))
        except FileNotFoundError:
            settings_cache[guild_id] = {}
        except json.JSONDecodeError:
            settings_cache[guild_id] = {}
    
    return settings_cache.get(guild_id, {})

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
        settings_cache[guild_id] = settings
        
        # Load existing settings
        try:
            with open('settings.json', 'r') as f:
                all_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_settings = {}
        
        # Update settings for this guild
        all_settings[guild_id] = settings
        
        # Save to file
        with open('settings.json', 'w') as f:
            json.dump(all_settings, f, indent=4)
        
        return True
    except Exception as e:
        print(f"Error updating settings: {e}")
        return False

def increment_command_count(guild_id: str):
    """Increment command count for a specific guild"""
    settings = get_guild_settings(guild_id)
    settings['command_count'] = settings.get('command_count', 0) + 1
    update_guild_settings(guild_id, settings)

def increment_mod_action(guild_id: str):
    """Increment moderation action count for a specific guild"""
    settings = get_guild_settings(guild_id)
    settings['mod_actions'] = settings.get('mod_actions', 0) + 1
    update_guild_settings(guild_id, settings)

async def notify_bot(guild_id: str, action: str, data: Dict[str, Any]):
    """Notify the bot about a settings change."""
    if bot is None:
        return
    
    try:
        guild = bot.get_guild(int(guild_id))
        if guild:
            # Add activity entry
            settings = get_guild_settings(guild_id)
            activity = settings.get('activity', [])
            activity.append({
                'timestamp': datetime.utcnow().isoformat(),
                'action': action,
                'data': data
            })
            settings['activity'] = activity[-10:]  # Keep last 10 activities
            update_guild_settings(guild_id, settings)
            
            # Notify bot about the change
            await bot.get_channel(int(settings.get('log_channel', 0))).send(
                f"🔄 Settings updated: {action}"
            )
    except Exception as e:
        print(f"Error notifying bot: {e}")

def add_activity(guild_id: str, activity_data: Dict[str, Any]):
    """Add an activity entry to the guild's settings."""
    settings = get_guild_settings(guild_id)
    activity = settings.get('activity', [])
    activity.append({
        'timestamp': datetime.utcnow().isoformat(),
        **activity_data
    })
    settings['activity'] = activity[-10:]  # Keep last 10 activities
    update_guild_settings(guild_id, settings) 