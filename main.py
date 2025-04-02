import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import json
from PIL import Image
import io
import aiohttp
import asyncio
import typing
from datetime import datetime
from flask import Flask, request, jsonify

# Load environment variables
load_dotenv()

# Settings file path
SETTINGS_FILE = 'settings.json'

# Flask app for API
api_app = Flask(__name__)
api_app.config['JSON_SORT_KEYS'] = False

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Define embed color
EMBED_COLOR = discord.Color.from_rgb(187, 144, 252)  # Soft purple color

# Settings management
settings_cache = {}

# API Authentication
def authenticate_request():
    auth_header = request.headers.get('Authorization')
    expected_token = f"Bearer {os.getenv('DISCORD_TOKEN')}"
    
    if not auth_header or auth_header != expected_token:
        return False
    return True

# API Routes
@api_app.route('/api/settings/<guild_id>', methods=['GET'])
def api_get_guild_settings(guild_id):
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    settings = get_guild_settings(guild_id)
    return jsonify(settings)

@api_app.route('/api/settings/<guild_id>', methods=['POST'])
def api_update_guild_settings(guild_id):
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    success = update_guild_settings(guild_id, data)
    
    if success:
        return jsonify({"success": True, "settings": data})
    else:
        return jsonify({"error": "Failed to update settings"}), 500

@api_app.route('/api/guilds', methods=['GET'])
def api_get_guilds():
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    guilds = []
    for guild in bot.guilds:
        guilds.append({
            "id": str(guild.id),
            "name": guild.name,
            "icon": guild.icon.url if guild.icon else None,
            "member_count": guild.member_count
        })
    
    return jsonify(guilds)

@api_app.route('/api/channels/<guild_id>', methods=['GET'])
def api_get_channels(guild_id):
    if not authenticate_request():
        return jsonify({"error": "Unauthorized"}), 401
    
    guild = bot.get_guild(int(guild_id))
    if not guild:
        return jsonify({"error": "Guild not found"}), 404
    
    channels = []
    for channel in guild.text_channels:
        channels.append({
            "id": str(channel.id),
            "name": channel.name,
            "type": 0,  # Text channel
            "position": channel.position
        })
    
    return jsonify(channels)

def get_guild_settings(guild_id: str) -> dict:
    """Get settings for a specific guild"""
    if guild_id is None:
        return settings_cache
    
    if guild_id not in settings_cache:
        # Load settings from file
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings_cache.update(json.load(f))
        except FileNotFoundError:
            settings_cache[guild_id] = {}
        except json.JSONDecodeError:
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
    
    # Add guild info from Discord if available
    guild = bot.get_guild(int(guild_id)) if bot else None
    if guild:
        settings['name'] = guild.name
        settings['icon'] = str(guild.icon.url) if guild.icon else None
        settings['member_count'] = guild.member_count
    
    return settings

def update_guild_settings(guild_id: str, settings: dict) -> bool:
    """Update settings for a specific guild"""
    try:
        # Update cache
        settings_cache[guild_id] = settings.copy()
        
        # Load existing settings
        try:
            with open(SETTINGS_FILE, 'r') as f:
                all_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_settings = {}
        
        # Update settings for this guild
        all_settings[guild_id] = settings
        
        # Save to file
        with open(SETTINGS_FILE, 'w') as f:
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

# Initialize bot with both prefix and slash commands
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix,
            intents=intents,
            application_id=os.getenv('APPLICATION_ID')
        )
        self.initial_extensions = [
            'image',
            'security'
        ]
        self.settings_cache = {}

    async def get_prefix(self, message):
        """Get prefix for a guild"""
        if not message.guild:
            return '?'
        
        guild_id = str(message.guild.id)
        if guild_id not in self.settings_cache:
            settings = get_guild_settings(guild_id)
            self.settings_cache[guild_id] = settings
        
        return self.settings_cache[guild_id].get('prefix', '?')

    async def setup_hook(self):
        """Load extensions and sync commands"""
        for ext in self.initial_extensions:
            await self.load_extension(ext)
        
        # Sync commands with Discord
        await self.tree.sync()
        print("Slash commands synced!")

    async def on_ready(self):
        print(f'Bot is ready! Logged in as {self.user.name}')
        await self.change_presence(activity=discord.Game(name="?help or /help"))
        
        # Start the API in a separate thread
        import threading
        def run_api():
            api_app.run(host='0.0.0.0', port=6150)
        
        api_thread = threading.Thread(target=run_api)
        api_thread.daemon = True
        api_thread.start()
        print("API server started on port 6150")

    async def on_command(self, ctx):
        """Track command usage"""
        if ctx.guild:
            increment_command_count(str(ctx.guild.id))

    async def on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to use this command!")
        else:
            print(f"Error in command {ctx.command}: {error}")
            await ctx.send("An error occurred while executing this command.")

bot = Bot()
bot.remove_command('help')  # Remove default help command

# Store last deleted message for snipe command
last_deleted_message = {}

# Load custom prefixes
def load_prefixes():
    try:
        # First, try to read from settings.json which the dashboard uses
        try:
            with open(SETTINGS_FILE, 'r') as f:
                all_settings = json.load(f)
                
                # Convert to prefix format
                prefix_dict = {}
                for guild_id, settings in all_settings.items():
                    if 'prefix' in settings:
                        prefix_dict[guild_id] = settings['prefix']
                
                print(f"Loaded {len(prefix_dict)} prefixes from settings.json")
                return prefix_dict
        except (FileNotFoundError, json.JSONDecodeError):
            pass
            
        # Fall back to prefixes.json for backward compatibility
        with open('prefixes.json', 'r') as f:
            prefixes = json.load(f)
            print(f"Loaded {len(prefixes)} prefixes from prefixes.json")
            return prefixes
    except FileNotFoundError:
        print("No prefix files found, using default prefix")
        return {}

prefixes = load_prefixes()

@bot.event
async def on_message_delete(message):
    if message.author != bot.user:
        last_deleted_message[message.guild.id] = message

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, user: typing.Union[discord.Member, discord.User, int], *, reason=None):
    try:
        # If an integer ID was passed, fetch the user
        if isinstance(user, int):
            user = await bot.fetch_user(user)
        
        # Check if user is a member of the server
        member = None
        try:
            member = await ctx.guild.fetch_member(user.id)
        except discord.NotFound:
            pass

        # If they're a member, check role hierarchy
        if member and member.top_role >= ctx.author.top_role:
            await ctx.send("You cannot ban this user due to role hierarchy!")
            return

        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title="You have been banned",
                description=f"You have been banned from {ctx.guild.name}\nReason: {reason if reason else 'No reason provided'}",
                color=EMBED_COLOR
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # Silently fail if we can't DM the user

        await ctx.guild.ban(user, reason=reason)
        
        # Track moderation action
        increment_mod_action(str(ctx.guild.id))
        
        embed = discord.Embed(
            description=f'Banned {user.mention}\nReason: {reason if reason else "No reason provided"}',
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("User not found! Please provide a valid user ID or mention.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to ban this user!")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@ban.error
async def ban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a user to ban!")
    elif isinstance(error, commands.BadUnionArgument):
        try:
            # Try one last time with raw ID
            user_id = int(ctx.message.content.split()[1])
            user = await bot.fetch_user(user_id)
            reason = ' '.join(ctx.message.content.split()[2:]) if len(ctx.message.content.split()) > 2 else None
            await ctx.guild.ban(user, reason=reason)
            embed = discord.Embed(
                description=f'Banned {user.mention}\nReason: {reason if reason else "No reason provided"}',
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
        except (ValueError, discord.NotFound):
            await ctx.send("User not found! Please provide a valid user ID or mention.")
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban this user!")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    if member.top_role >= ctx.author.top_role:
        await ctx.send("You cannot kick this user due to role hierarchy!")
        return
    
    # Try to DM the user
    try:
        dm_embed = discord.Embed(
            title="You have been kicked",
            description=f"You have been kicked from {ctx.guild.name}\nReason: {reason if reason else 'No reason provided'}",
            color=EMBED_COLOR
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # Silently fail if we can't DM the user
    
    await member.kick(reason=reason)
    embed = discord.Embed(
        description=f'Kicked {member.mention}\nReason: {reason if reason else "No reason provided"}',
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        try:
            # Try to fetch member by ID
            member_id = int(ctx.message.content.split()[1])
            member = await ctx.guild.fetch_member(member_id)
            if member.top_role >= ctx.author.top_role:
                await ctx.send("You cannot kick this user due to role hierarchy!")
                return
            await member.kick(reason=ctx.message.content.split(maxsplit=2)[2] if len(ctx.message.content.split()) > 2 else None)
            await ctx.send(f'Kicked {member.mention} for reason: {ctx.message.content.split(maxsplit=2)[2] if len(ctx.message.content.split()) > 2 else None}')
        except (ValueError, discord.NotFound):
            await ctx.send("Member not found! Please provide a valid mention or ID.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a member to kick!")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(ctx, member: discord.Member, duration: int, *, reason=None):
    if member.top_role >= ctx.author.top_role:
        await ctx.send("You cannot timeout this user due to role hierarchy!")
        return
    
    # Try to DM the user
    try:
        dm_embed = discord.Embed(
            title="You have been timed out",
            description=f"You have been timed out in {ctx.guild.name}\nDuration: {duration} seconds\nReason: {reason if reason else 'No reason provided'}",
            color=EMBED_COLOR
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # Silently fail if we can't DM the user
    
    await member.timeout(duration=duration, reason=reason)
    embed = discord.Embed(
        description=f'Timed out {member.mention} for {duration} seconds\nReason: {reason if reason else "No reason provided"}',
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

@timeout.error
async def timeout_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        try:
            # Try to fetch member by ID
            args = ctx.message.content.split()
            member_id = int(args[1])
            duration = int(args[2])
            member = await ctx.guild.fetch_member(member_id)
            if member.top_role >= ctx.author.top_role:
                await ctx.send("You cannot timeout this user due to role hierarchy!")
                return
            reason = ' '.join(args[3:]) if len(args) > 3 else None
            await member.timeout(duration=duration, reason=reason)
            await ctx.send(f'Timed out {member.mention} for {duration} seconds. Reason: {reason}')
        except (ValueError, discord.NotFound):
            await ctx.send("Member not found! Please provide a valid mention or ID.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a member and duration to timeout!")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def untimeout(ctx, member: discord.Member, *, reason=None):
    if member.top_role >= ctx.author.top_role:
        await ctx.send("You cannot remove timeout from this user due to role hierarchy!")
        return
    
    # Try to DM the user
    try:
        dm_embed = discord.Embed(
            title="Your timeout has been removed",
            description=f"Your timeout in {ctx.guild.name} has been removed\nReason: {reason if reason else 'No reason provided'}",
            color=EMBED_COLOR
        )
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # Silently fail if we can't DM the user
    
    await member.timeout(duration=None, reason=reason)
    embed = discord.Embed(
        description=f'Removed timeout from {member.mention}\nReason: {reason if reason else "No reason provided"}',
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

@untimeout.error
async def untimeout_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        try:
            # Try to fetch member by ID
            member_id = int(ctx.message.content.split()[1])
            member = await ctx.guild.fetch_member(member_id)
            if member.top_role >= ctx.author.top_role:
                await ctx.send("You cannot remove timeout from this user due to role hierarchy!")
                return
            reason = ' '.join(ctx.message.content.split()[2:]) if len(ctx.message.content.split()) > 2 else None
            await member.timeout(duration=None, reason=reason)
            embed = discord.Embed(
                description=f'Removed timeout from {member.mention}\nReason: {reason if reason else "No reason provided"}',
                color=EMBED_COLOR
            )
            await ctx.send(embed=embed)
        except (ValueError, discord.NotFound):
            await ctx.send("Member not found! Please provide a valid mention or ID.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a member to remove timeout from!")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason=None):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        embed = discord.Embed(
            description=f'Unbanned {user.mention}\nReason: {reason if reason else "No reason provided"}',
            color=EMBED_COLOR
        )
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send("User not found! Please provide a valid user ID.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to unban members!")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

@unban.error
async def unban_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to use this command!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Please provide a user ID to unban!")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please provide a valid user ID!")

@bot.command()
async def snipe(ctx):
    if ctx.guild.id not in last_deleted_message:
        await ctx.send("There's nothing to snipe!")
        return
    
    message = last_deleted_message[ctx.guild.id]
    embed = discord.Embed(
        description=message.content,
        color=EMBED_COLOR,
        timestamp=message.created_at
    )
    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url if message.author.avatar else None)
    
    if message.attachments:
        embed.add_field(name="Attachments", value="\n".join([a.url for a in message.attachments]))
    
    await ctx.send(embed=embed)

@bot.command()
async def prefix(ctx):
    prefix = prefixes.get(str(ctx.guild.id), '?')
    await ctx.send(f'The current prefix is: `{prefix}`')

@bot.command()
@commands.has_permissions(administrator=True)
async def setprefix(ctx, new_prefix):
    if len(new_prefix) > 3:
        await ctx.send("Prefix must be 3 characters or less!")
        return
    
    prefixes[str(ctx.guild.id)] = new_prefix
    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f)
    
    bot.command_prefix = new_prefix
    await ctx.send(f'Prefix changed to: `{new_prefix}`')

@bot.command()
async def ping(ctx):
    """Check the bot's latency"""
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot Latency: `{latency}ms`",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    """Show all available commands"""
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are all available commands:",
        color=EMBED_COLOR
    )

    # Moderation Commands
    mod_commands = [
        "`?ban` - Ban a user",
        "`?kick` - Kick a user",
        "`?timeout` - Timeout a user",
        "`?untimeout` - Remove timeout from a user",
        "`?unban` - Unban a user"
    ]
    embed.add_field(
        name="Moderation Commands",
        value="\n".join(mod_commands),
        inline=False
    )

    # Utility Commands
    util_commands = [
        "`?snipe` - Show last deleted message",
        "`?prefix` - Show current prefix",
        "`?setprefix` - Change command prefix",
        "`?ping` - Check bot latency",
        "`?help` - Show this help message",
        "`?repo` - Get the bot's repository link"
    ]
    embed.add_field(
        name="Utility Commands",
        value="\n".join(util_commands),
        inline=False
    )

    # Image Commands
    image_commands = [
        "`?gif` - Convert image to GIF",
        "`?caption <text>` - Add text caption to an image",
        "`?fry` - Deepfry an image",
        "`?mirror` - Mirror an image horizontally"
    ]
    embed.add_field(
        name="Image Commands",
        value="\n".join(image_commands),
        inline=False
    )

    # Security Commands
    security_commands = [
        "`?setsecuritylog <channel>` - Set channel for security alerts"
    ]
    embed.add_field(
        name="Security Commands",
        value="\n".join(security_commands),
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command()
async def repo(ctx):
    """Get the bot's repository link"""
    embed = discord.Embed(
        title="Repository Link",
        description="[Click here to view the bot's repository](https://github.com/LyrdSouth/template.py)",
        color=EMBED_COLOR
    )
    await ctx.send(embed=embed)

#### SLASH COMMANDS ####

@bot.tree.command(name="ban", description="Ban a user from the server")
@commands.has_permissions(ban_members=True)
async def slash_ban(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    try:
        # Check role hierarchy
        if user.top_role >= interaction.user.top_role:
            await interaction.response.send_message("You cannot ban this user due to role hierarchy!", ephemeral=True)
            return

        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title="You have been banned",
                description=f"You have been banned from {interaction.guild.name}\nReason: {reason if reason else 'No reason provided'}",
                color=EMBED_COLOR
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass  # Silently fail if we can't DM the user

        await interaction.guild.ban(user, reason=reason)
        embed = discord.Embed(
            description=f'Banned {user.mention}\nReason: {reason if reason else "No reason provided"}',
            color=EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to ban this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a user from the server")
@commands.has_permissions(kick_members=True)
async def slash_kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if user.top_role >= interaction.user.top_role:
        await interaction.response.send_message("You cannot kick this user due to role hierarchy!", ephemeral=True)
        return
    
    # Try to DM the user
    try:
        dm_embed = discord.Embed(
            title="You have been kicked",
            description=f"You have been kicked from {interaction.guild.name}\nReason: {reason if reason else 'No reason provided'}",
            color=EMBED_COLOR
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # Silently fail if we can't DM the user
    
    await user.kick(reason=reason)
    embed = discord.Embed(
        description=f'Kicked {user.mention}\nReason: {reason if reason else "No reason provided"}',
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="timeout", description="Timeout a user")
@commands.has_permissions(moderate_members=True)
async def slash_timeout(interaction: discord.Interaction, user: discord.Member, duration: int, reason: str = None):
    if user.top_role >= interaction.user.top_role:
        await interaction.response.send_message("You cannot timeout this user due to role hierarchy!", ephemeral=True)
            return
        
    # Try to DM the user
    try:
        dm_embed = discord.Embed(
            title="You have been timed out",
            description=f"You have been timed out in {interaction.guild.name}\nDuration: {duration} seconds\nReason: {reason if reason else 'No reason provided'}",
            color=EMBED_COLOR
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # Silently fail if we can't DM the user
    
    await user.timeout(duration=duration, reason=reason)
    embed = discord.Embed(
        description=f'Timed out {user.mention} for {duration} seconds\nReason: {reason if reason else "No reason provided"}',
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="untimeout", description="Remove timeout from a user")
@commands.has_permissions(moderate_members=True)
async def slash_untimeout(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    if user.top_role >= interaction.user.top_role:
        await interaction.response.send_message("You cannot remove timeout from this user due to role hierarchy!", ephemeral=True)
            return
        
    # Try to DM the user
    try:
        dm_embed = discord.Embed(
            title="Your timeout has been removed",
            description=f"Your timeout in {interaction.guild.name} has been removed\nReason: {reason if reason else 'No reason provided'}",
            color=EMBED_COLOR
        )
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # Silently fail if we can't DM the user
    
    await user.timeout(duration=None, reason=reason)
    embed = discord.Embed(
        description=f'Removed timeout from {user.mention}\nReason: {reason if reason else "No reason provided"}',
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unban", description="Unban a user")
@commands.has_permissions(ban_members=True)
async def slash_unban(interaction: discord.Interaction, user_id: str, reason: str = None):
    try:
        user_id = int(user_id)
        user = await bot.fetch_user(user_id)
        await interaction.guild.unban(user, reason=reason)
        embed = discord.Embed(
            description=f'Unbanned {user.mention}\nReason: {reason if reason else "No reason provided"}',
            color=EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed)
    except ValueError:
        await interaction.response.send_message("Please provide a valid user ID!", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("User not found! Please provide a valid user ID.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to unban members!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="snipe", description="Show the last deleted message")
async def slash_snipe(interaction: discord.Interaction):
    if interaction.guild.id not in last_deleted_message:
        await interaction.response.send_message("There's nothing to snipe!", ephemeral=True)
        return
    
    message = last_deleted_message[interaction.guild.id]
    embed = discord.Embed(
        description=message.content,
        color=EMBED_COLOR,
        timestamp=message.created_at
    )
    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url if message.author.avatar else None)
    
    if message.attachments:
        embed.add_field(name="Attachments", value="\n".join([a.url for a in message.attachments]))
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="prefix", description="Show the current command prefix")
async def slash_prefix(interaction: discord.Interaction):
    prefix = prefixes.get(str(interaction.guild.id), '?')
    await interaction.response.send_message(f'The current prefix is: `{prefix}`')

@bot.tree.command(name="setprefix", description="Change the command prefix")
@commands.has_permissions(administrator=True)
async def slash_setprefix(interaction: discord.Interaction, new_prefix: str):
    if len(new_prefix) > 3:
        await interaction.response.send_message("Prefix must be 3 characters or less!", ephemeral=True)
        return
    
    prefixes[str(interaction.guild.id)] = new_prefix
    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f)
    
    bot.command_prefix = new_prefix
    await interaction.response.send_message(f'Prefix changed to: `{new_prefix}`')

@bot.tree.command(name="ping", description="Check the bot's latency")
async def slash_ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot Latency: `{latency}ms`",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show all available commands")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are all available commands:",
        color=EMBED_COLOR
    )

    # Moderation Commands
    mod_commands = [
        "`/ban` - Ban a user",
        "`/kick` - Kick a user",
        "`/timeout` - Timeout a user",
        "`/untimeout` - Remove timeout from a user",
        "`/unban` - Unban a user"
    ]
    embed.add_field(
        name="Moderation Commands",
        value="\n".join(mod_commands),
        inline=False
    )

    # Utility Commands
    util_commands = [
        "`/snipe` - Show last deleted message",
        "`/prefix` - Show current prefix",
        "`/setprefix` - Change command prefix",
        "`/ping` - Check bot latency",
        "`/help` - Show this help message",
        "`/repo` - Get the bot's repository link"
    ]
    embed.add_field(
        name="Utility Commands",
        value="\n".join(util_commands),
        inline=False
    )

    # Image Commands
    image_commands = [
        "`/gif` - Convert image to GIF",
        "`/caption` - Add text caption to an image",
        "`/fry` - Deepfry an image",
        "`/mirror` - Mirror an image horizontally"
    ]
    embed.add_field(
        name="Image Commands",
        value="\n".join(image_commands),
        inline=False
    )

    # Security Commands
    security_commands = [
        "`/setsecuritylog` - Set channel for security alerts"
    ]
    embed.add_field(
        name="Security Commands",
        value="\n".join(security_commands),
        inline=False
    )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="repo", description="Get the bot's repository link")
async def slash_repo(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Repository Link",
        description="[Click here to view the bot's repository](https://github.com/LyrdSouth/template.py)",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)

# Save prefix to the JSON file
def save_prefix(guild_id, prefix):
    prefixes = load_prefixes()
    prefixes[str(guild_id)] = prefix
    
    # Save to prefixes.json for backward compatibility
    with open('prefixes.json', 'w') as f:
        json.dump(prefixes, f, indent=4)
    
    # Also update settings.json which the dashboard uses
    try:
        # Load existing settings
        try:
            with open(SETTINGS_FILE, 'r') as f:
                all_settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_settings = {}
        
        # Update prefix in settings
        guild_id_str = str(guild_id)
        if guild_id_str not in all_settings:
            all_settings[guild_id_str] = {}
        
        all_settings[guild_id_str]['prefix'] = prefix
        
        # Save updated settings
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(all_settings, f, indent=4)
            
        print(f"Updated prefix in {SETTINGS_FILE} for guild {guild_id}")
    except Exception as e:
        print(f"Error updating prefix in settings.json: {e}")

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 