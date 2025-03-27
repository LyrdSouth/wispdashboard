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

bot = commands.Bot(command_prefix='?', intents=intents)
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
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="?help"))

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
async def gif(ctx):
    if not ctx.message.reference:
        await ctx.send("Please reply to an image to convert it to a GIF!")
        return
    
    try:
        referenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not referenced_message.attachments:
            await ctx.send("The referenced message doesn't contain any images!")
            return
        
        attachment = referenced_message.attachments[0]
        if not attachment.content_type.startswith('image'):
            await ctx.send("The referenced message doesn't contain a valid image!")
            return
        
        # Download the image
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    
                    # Convert to GIF
                    image = Image.open(io.BytesIO(image_data))
                    if image.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', image.size, (255, 255, 255))
                        background.paste(image, mask=image.split()[-1])
                        image = background
                    
                    # Save as GIF
                    output = io.BytesIO()
                    image.save(output, format='GIF')
                    output.seek(0)
                    
                    # Send the GIF
                    await ctx.send(file=discord.File(output, filename='converted.gif'))
                else:
                    await ctx.send("Failed to download the image!")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

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
        "`?gif` - Convert image to GIF",
        "`?ping` - Check bot latency",
        "`?help` - Show this help message",
        "`?repo` - Get the bot's repository link"
    ]
    embed.add_field(
        name="Utility Commands",
        value="\n".join(util_commands),
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

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN')) 