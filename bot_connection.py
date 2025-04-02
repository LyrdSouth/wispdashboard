import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv
import asyncio
import aiohttp
from typing import Dict, Any

class BotConnection:
    def __init__(self):
        self.settings_file = 'guild_settings.json'
        self.activity_file = 'guild_activity.json'
        self.bot_token = os.getenv('DISCORD_TOKEN')
        self.dashboard_url = os.getenv('DASHBOARD_URL', 'https://wispbot.site')
        self._settings_cache = {}
        self._activity_cache = {}

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from JSON file"""
        try:
            with open(self.settings_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_settings(self, settings: Dict[str, Any]):
        """Save settings to JSON file"""
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=4)

    def load_activity(self) -> Dict[str, list]:
        """Load activity from JSON file"""
        try:
            with open(self.activity_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_activity(self, activity: Dict[str, list]):
        """Save activity to JSON file"""
        with open(self.activity_file, 'w') as f:
            json.dump(activity, f, indent=4)

    def update_guild_settings(self, guild_id: str, settings: Dict[str, Any]):
        """Update settings for a specific guild"""
        current_settings = self.load_settings()
        current_settings[guild_id] = settings
        self.save_settings(current_settings)
        self._settings_cache[guild_id] = settings

    def get_guild_settings(self, guild_id: str) -> Dict[str, Any]:
        """Get settings for a specific guild"""
        if guild_id in self._settings_cache:
            return self._settings_cache[guild_id]
        
        settings = self.load_settings()
        guild_settings = settings.get(guild_id, {})
        self._settings_cache[guild_id] = guild_settings
        return guild_settings

    def add_activity(self, guild_id: str, activity: Dict[str, Any]):
        """Add new activity for a guild"""
        current_activity = self.load_activity()
        if guild_id not in current_activity:
            current_activity[guild_id] = []
        
        current_activity[guild_id].insert(0, activity)
        # Keep only last 50 activities
        current_activity[guild_id] = current_activity[guild_id][:50]
        self.save_activity(current_activity)

    async def notify_bot(self, guild_id: str, action: str, data: Dict[str, Any]):
        """Notify the bot about dashboard changes"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.dashboard_url}/api/bot/update",
                    json={
                        'guild_id': guild_id,
                        'action': action,
                        'data': data
                    },
                    headers={'Authorization': f'Bearer {self.bot_token}'}
                ) as response:
                    if response.status != 200:
                        print(f"Failed to notify bot: {await response.text()}")
            except Exception as e:
                print(f"Error notifying bot: {e}")

    def increment_command_count(self, guild_id: str):
        """Increment command usage count for a guild"""
        settings = self.get_guild_settings(guild_id)
        settings['command_count'] = settings.get('command_count', 0) + 1
        self.update_guild_settings(guild_id, settings)

    def increment_mod_action(self, guild_id: str):
        """Increment moderation action count for a guild"""
        settings = self.get_guild_settings(guild_id)
        settings['mod_actions'] = settings.get('mod_actions', 0) + 1
        self.update_guild_settings(guild_id, settings)

# Create a global instance
bot_connection = BotConnection() 