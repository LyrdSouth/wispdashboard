from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime
import discord
from discord.ext import commands
import json
import os
from functools import wraps
import requests
from urllib.parse import urlencode

dashboard = Blueprint('dashboard', __name__)

# Discord OAuth2 settings from environment variables
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI')
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'

# Settings storage
SETTINGS_FILE = 'guild_settings.json'

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

def get_guild_settings(guild_id):
    settings = load_settings()
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {
            'prefix': '?',
            'cogs': [],
            'security_log_channel': None,
            'activity': []
        }
        save_settings(settings)
    return settings[str(guild_id)]

def update_guild_settings(guild_id, new_settings):
    settings = load_settings()
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {}
    
    # Update only provided settings
    for key, value in new_settings.items():
        settings[str(guild_id)][key] = value
    
    save_settings(settings)
    return settings[str(guild_id)]

def log_activity(guild_id, action, data):
    settings = get_guild_settings(guild_id)
    if 'activity' not in settings:
        settings['activity'] = []
    
    activity = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'data': data
    }
    
    settings['activity'].append(activity)
    # Keep only last 50 activities
    settings['activity'] = settings['activity'][-50:]
    save_settings(settings)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'access_token' not in session:
            return redirect(url_for('dashboard.login'))
        return f(*args, **kwargs)
    return decorated_function

@dashboard.route('/login')
def login():
    params = {
        'client_id': DISCORD_CLIENT_ID,
        'redirect_uri': DISCORD_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify guilds'
    }
    return redirect(f'https://discord.com/api/oauth2/authorize?{urlencode(params)}')

@dashboard.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return 'No code provided', 400
    
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    response = requests.post('https://discord.com/api/oauth2/token', data=data)
    if response.status_code != 200:
        return 'Failed to get access token', 400
    
    token_data = response.json()
    session['access_token'] = token_data['access_token']
    session['refresh_token'] = token_data['refresh_token']
    session['expires_at'] = datetime.utcnow().timestamp() + token_data['expires_in']
    
    return redirect(url_for('dashboard.select_server'))

def refresh_token():
    if 'refresh_token' not in session:
        return False
    
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': session['refresh_token']
    }
    
    response = requests.post('https://discord.com/api/oauth2/token', data=data)
    if response.status_code != 200:
        return False
    
    token_data = response.json()
    session['access_token'] = token_data['access_token']
    session['refresh_token'] = token_data['refresh_token']
    session['expires_at'] = datetime.utcnow().timestamp() + token_data['expires_in']
    return True

@dashboard.route('/')
@login_required
def select_server():
    if datetime.utcnow().timestamp() >= session.get('expires_at', 0):
        if not refresh_token():
            return redirect(url_for('dashboard.login'))
    
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
    
    if response.status_code != 200:
        return 'Failed to fetch servers', 400
    
    guilds = response.json()
    return render_template('select_server.html', guilds=guilds)

@dashboard.route('/dashboard/<guild_id>')
@login_required
def guild_dashboard(guild_id):
    if datetime.utcnow().timestamp() >= session.get('expires_at', 0):
        if not refresh_token():
            return redirect(url_for('dashboard.login'))
    
    headers = {'Authorization': f'Bearer {session["access_token"]}'}
    response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
    
    if response.status_code != 200:
        return 'Failed to fetch guild data', 400
    
    guild_data = response.json()
    settings = get_guild_settings(guild_id)
    
    # Fetch channels
    channels_response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}/channels', headers=headers)
    channels = channels_response.json() if channels_response.status_code == 200 else []
    
    return render_template('dashboard.html',
                         guild_id=guild_id,
                         guild_name=guild_data['name'],
                         guild_icon_url=f"https://cdn.discordapp.com/icons/{guild_id}/{guild_data['icon']}.png" if guild_data.get('icon') else None,
                         settings=settings,
                         channels=channels)

@dashboard.route('/api/guild/<guild_id>/prefix', methods=['POST'])
@login_required
def update_prefix(guild_id):
    if datetime.utcnow().timestamp() >= session.get('expires_at', 0):
        if not refresh_token():
            return jsonify({'success': False, 'error': 'Session expired'}), 401
    
    data = request.get_json()
    prefix = data.get('prefix', '?')
    
    if len(prefix) > 3:
        return jsonify({'success': False, 'error': 'Prefix must be 3 characters or less'}), 400
    
    settings = get_guild_settings(guild_id)
    settings['prefix'] = prefix
    update_guild_settings(guild_id, settings)
    
    log_activity(guild_id, 'prefix_update', {'prefix': prefix})
    
    return jsonify({'success': True})

@dashboard.route('/api/guild/<guild_id>/cogs', methods=['POST'])
@login_required
def update_cogs(guild_id):
    if datetime.utcnow().timestamp() >= session.get('expires_at', 0):
        if not refresh_token():
            return jsonify({'success': False, 'error': 'Session expired'}), 401
    
    data = request.get_json()
    cogs = data.get('cogs', [])
    
    settings = get_guild_settings(guild_id)
    settings['cogs'] = cogs
    update_guild_settings(guild_id, settings)
    
    log_activity(guild_id, 'features_update', {'cogs': cogs})
    
    return jsonify({'success': True})

@dashboard.route('/api/guild/<guild_id>/log-channel', methods=['POST'])
@login_required
def update_log_channel(guild_id):
    if datetime.utcnow().timestamp() >= session.get('expires_at', 0):
        if not refresh_token():
            return jsonify({'success': False, 'error': 'Session expired'}), 401
    
    data = request.get_json()
    channel_id = data.get('channel_id')
    
    settings = get_guild_settings(guild_id)
    settings['security_log_channel'] = channel_id
    update_guild_settings(guild_id, settings)
    
    log_activity(guild_id, 'log_channel_update', {'channel_id': channel_id})
    
    return jsonify({'success': True})

@dashboard.route('/api/guild/<guild_id>/activity')
@login_required
def get_activity(guild_id):
    if datetime.utcnow().timestamp() >= session.get('expires_at', 0):
        if not refresh_token():
            return jsonify({'success': False, 'error': 'Session expired'}), 401
    
    settings = get_guild_settings(guild_id)
    return jsonify(settings.get('activity', [])) 