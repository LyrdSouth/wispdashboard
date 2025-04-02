"""
Dashboard package for the Discord bot.
Contains the Flask web application and bot connection utilities.
"""

# This file makes the dashboard directory a Python package 

from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify
import discord
from discord.ext import commands
import os
from datetime import datetime
import json

dashboard = Blueprint('dashboard', __name__)

# Store activity in memory (in production, use a database)
activity_log = {}

def get_discord_client():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    return discord.Client(intents=intents)

def get_bot():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    return commands.Bot(command_prefix='!', intents=intents)

def log_activity(guild_id, action, data):
    if guild_id not in activity_log:
        activity_log[guild_id] = []
    
    activity_log[guild_id].append({
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'data': data
    })
    
    # Keep only last 50 activities
    activity_log[guild_id] = activity_log[guild_id][-50:]

@dashboard.route('/')
def index():
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))
    return redirect(url_for('dashboard.select_server'))

@dashboard.route('/select-server')
def select_server():
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))
    
    client = get_discord_client()
    
    try:
        client.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        print(f"Error running client: {e}")
        return "Error connecting to Discord", 500
    
    guilds = []
    for guild in client.guilds:
        member = guild.get_member(client.user.id)
        if member and member.guild_permissions.administrator:
            guilds.append({
                'id': str(guild.id),
                'name': guild.name,
                'icon': guild.icon.key if guild.icon else None,
                'owner': str(guild.owner_id) == str(client.user.id),
                'permissions': str(member.guild_permissions.value)
            })
    
    return render_template('select_server.html', 
                         guilds=guilds,
                         client_id=os.getenv('DISCORD_CLIENT_ID'))

@dashboard.route('/dashboard/<guild_id>')
def guild_dashboard(guild_id):
    if 'access_token' not in session:
        return redirect(url_for('auth.login'))
    
    client = get_discord_client()
    
    try:
        client.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        print(f"Error running client: {e}")
        return "Error connecting to Discord", 500
    
    guild = client.get_guild(int(guild_id))
    if not guild:
        return "Guild not found", 404
    
    # Get channels
    channels = []
    for channel in guild.channels:
        if isinstance(channel, discord.TextChannel):
            channels.append({
                'id': str(channel.id),
                'name': channel.name
            })
    
    # Get settings from environment variables
    settings = {
        'prefix': os.getenv(f'PREFIX_{guild_id}', '!'),
        'security_log_channel': os.getenv(f'LOG_CHANNEL_{guild_id}'),
        'cogs': os.getenv(f'COGS_{guild_id}', '').split(',') if os.getenv(f'COGS_{guild_id}') else []
    }
    
    return render_template('dashboard.html',
                         guild_id=guild_id,
                         guild_name=guild.name,
                         guild_icon_url=guild.icon.url if guild.icon else None,
                         channels=channels,
                         settings=settings)

@dashboard.route('/api/guild/<guild_id>/prefix', methods=['POST'])
def update_prefix(guild_id):
    if 'access_token' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    prefix = data.get('prefix', '!')
    
    if len(prefix) > 3:
        return jsonify({'success': False, 'error': 'Prefix must be 3 characters or less'}), 400
    
    # Update prefix in environment variables
    os.environ[f'PREFIX_{guild_id}'] = prefix
    
    # Log activity
    log_activity(guild_id, 'prefix_update', {'prefix': prefix})
    
    return jsonify({'success': True})

@dashboard.route('/api/guild/<guild_id>/log-channel', methods=['POST'])
def update_log_channel(guild_id):
    if 'access_token' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    channel_id = data.get('channel_id')
    
    # Update log channel in environment variables
    if channel_id:
        os.environ[f'LOG_CHANNEL_{guild_id}'] = channel_id
    else:
        os.environ.pop(f'LOG_CHANNEL_{guild_id}', None)
    
    # Log activity
    log_activity(guild_id, 'log_channel_update', {'channel_id': channel_id})
    
    return jsonify({'success': True})

@dashboard.route('/api/guild/<guild_id>/cogs', methods=['POST'])
def update_cogs(guild_id):
    if 'access_token' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    data = request.get_json()
    cogs = data.get('cogs', [])
    
    # Update cogs in environment variables
    os.environ[f'COGS_{guild_id}'] = ','.join(cogs)
    
    # Log activity
    log_activity(guild_id, 'features_update', {'cogs': cogs})
    
    return jsonify({'success': True})

@dashboard.route('/api/guild/<guild_id>/activity')
def get_activity(guild_id):
    if 'access_token' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    return jsonify(activity_log.get(guild_id, [])) 