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

# Load environment variables
load_dotenv()
# to use this, create a .env file and put the your token in it, label it "DISCORD_TOKEN" the bot literally wont work if you dont, if you arent smart enough to do this, you dont deserve to use this bot.


# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Define embed color
EMBED_COLOR = discord.Color.from_rgb(187, 144, 252)  # Soft purple color

# Initialize bot with both prefix and slash commands
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='?',
            intents=intents,
            application_id=os.getenv('APPLICATION_ID')  # Add this to your .env file
        )
        self.initial_extensions = [
            'image',
            'security'
        ]

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

bot = Bot()
bot.remove_command('help')  # Remove default help command

# Store last deleted message for snipe command
last_deleted_message = {}

# Load custom prefixes
def load_prefixes():
    try:
        with open('prefixes.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
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

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 