import discord
from discord.ext import commands
import json
from datetime import datetime, timedelta
import os

class SecurityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.EMBED_COLOR = discord.Color.from_rgb(187, 144, 252)  # Soft purple color
        self.log_channels = self.load_log_channels()
        
    def load_log_channels(self):
        try:
            with open('security_logs.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_log_channels(self):
        with open('security_logs.json', 'w') as f:
            json.dump(self.log_channels, f)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def setsecuritylog(self, ctx, channel: discord.TextChannel):
        """Set the channel for security alerts"""
        self.log_channels[str(ctx.guild.id)] = channel.id
        self.save_log_channels()
        await ctx.send(f"Security log channel set to {channel.mention}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Check for suspicious accounts when they join"""
        if str(member.guild.id) not in self.log_channels:
            return

        channel = self.bot.get_channel(self.log_channels[str(member.guild.id)])
        if not channel:
            return

        # Check for default avatar
        if member.avatar is None:
            embed = discord.Embed(
                title="⚠️ Suspicious Account Detected",
                description=f"User {member.mention} joined with a default avatar",
                color=discord.Color.yellow(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
            embed.add_field(name="Account Age", value=self.get_account_age(member.created_at))
            await channel.send(embed=embed)

        # Check for new accounts (less than 7 days old)
        if (datetime.now(member.created_at.tzinfo) - member.created_at).days < 7:
            embed = discord.Embed(
                title="⚠️ New Account Detected",
                description=f"User {member.mention} joined with a new account",
                color=discord.Color.orange(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
            embed.add_field(name="Account Age", value=self.get_account_age(member.created_at))
            await channel.send(embed=embed)

        # Check for suspicious usernames (contains common spam characters)
        suspicious_chars = ['#', '@', '!', '$', '%', '^', '&', '*', '(', ')', '_', '+', '=', '{', '}', '[', ']', '|', '\\', ':', ';', '"', "'", '<', '>', ',', '.', '?', '/']
        if any(char in member.name for char in suspicious_chars):
            embed = discord.Embed(
                title="⚠️ Suspicious Username Detected",
                description=f"User {member.mention} joined with a suspicious username",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Username", value=member.name)
            embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"))
            embed.add_field(name="Account Age", value=self.get_account_age(member.created_at))
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check for spam in messages"""
        if message.author.bot or str(message.guild.id) not in self.log_channels:
            return

        channel = self.bot.get_channel(self.log_channels[str(message.guild.id)])
        if not channel:
            return

        # Check for message spam (same message repeated)
        if len(message.content) > 10:  # Only check messages longer than 10 characters
            async for msg in message.channel.history(limit=5):
                if msg.author == message.author and msg.content == message.content and msg.id != message.id:
                    embed = discord.Embed(
                        title="⚠️ Spam Detected",
                        description=f"User {message.author.mention} is spamming the same message",
                        color=discord.Color.red(),
                        timestamp=datetime.utcnow()
                    )
                    embed.add_field(name="Message Content", value=message.content)
                    embed.add_field(name="Channel", value=message.channel.mention)
                    await channel.send(embed=embed)
                    break

        # Check for excessive mentions
        if len(message.mentions) > 5:
            embed = discord.Embed(
                title="⚠️ Excessive Mentions Detected",
                description=f"User {message.author.mention} is using excessive mentions",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Number of Mentions", value=len(message.mentions))
            embed.add_field(name="Channel", value=message.channel.mention)
            await channel.send(embed=embed)

    def get_account_age(self, created_at):
        """Get a human-readable account age"""
        age = datetime.now(created_at.tzinfo) - created_at
        days = age.days
        hours = age.seconds // 3600
        minutes = (age.seconds % 3600) // 60
        
        if days > 0:
            return f"{days} days, {hours} hours"
        elif hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes"

    #### SLASH COMMANDS ####

    @commands.hybrid_command(name="setsecuritylog", description="Set the channel for security alerts")
    @commands.has_permissions(administrator=True)
    async def slash_setsecuritylog(self, ctx, channel: discord.TextChannel):
        """Set the channel for security alerts"""
        self.log_channels[str(ctx.guild.id)] = channel.id
        self.save_log_channels()
        await ctx.send(f"Security log channel set to {channel.mention}")

async def setup(bot):
    await bot.add_cog(SecurityCog(bot)) 