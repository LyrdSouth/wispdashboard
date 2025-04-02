from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import os
from dotenv import load_dotenv
import requests
from functools import wraps
import json
from werkzeug.middleware.proxy_fix import ProxyFix
from bot_connection import set_bot, get_guild_settings, update_guild_settings, increment_command_count, increment_mod_action
import asyncio
import datetime
import discord

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key')

# Configure Flask for proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Discord OAuth2 settings
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://wispbot.site/callback')
DISCORD_API_ENDPOINT = 'https://discord.com/api/v10'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('select_server'))
    return render_template('index.html')

# Ensure we handle both www and non-www domains
def get_redirect_uri():
    if request.host.startswith('www.'):
        return 'https://www.wispbot.site/callback'
    return 'https://wispbot.site/callback'

@app.route('/login')
def login():
    return redirect(f'https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify%20guilds')

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return redirect(url_for('index'))
    
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post(f'{DISCORD_API_ENDPOINT}/oauth2/token', data=data, headers=headers)
    if response.status_code != 200:
        return redirect(url_for('index'))
    
    tokens = response.json()
    session['access_token'] = tokens['access_token']
    
    # Get user data
    headers = {
        'Authorization': f'Bearer {tokens["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me', headers=headers)
    if response.status_code != 200:
        return redirect(url_for('index'))
    
    user_data = response.json()
    session['user'] = user_data
    
    return redirect(url_for('select_server'))

@app.route('/select-server')
@login_required
def select_server():
    headers = {
        'Authorization': f'Bearer {session["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
    if response.status_code != 200:
        return redirect(url_for('login'))
    
    guilds = response.json()
    return render_template('select_server.html', guilds=guilds)

@app.route('/dashboard')
@login_required
def dashboard():
    guild_id = request.args.get('guild_id')
    if not guild_id:
        return redirect(url_for('select_server'))
    
    # Verify user has access to this guild
    headers = {
        'Authorization': f'Bearer {session["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
    if response.status_code != 200:
        return redirect(url_for('login'))
    
    guilds = response.json()
    if not any(g['id'] == guild_id for g in guilds):
        return redirect(url_for('select_server'))
    
    return render_template('dashboard.html', guild_id=guild_id)

@app.route('/api/guilds')
@login_required
def get_guilds():
    headers = {
        'Authorization': f'Bearer {session["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch guilds'}), 500
    
    return jsonify(response.json())

@app.route('/api/guild/<guild_id>')
@login_required
def get_guild(guild_id):
    try:
        # Get guild settings
        settings = get_guild_settings(guild_id)
        
        # Get guild info from Discord
        headers = {
            'Authorization': f'Bearer {session["access_token"]}'
        }
        
        response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch guild data'}), 500
        
        guild_data = response.json()
        
        # Merge Discord data with settings
        guild_data.update({
            'settings': settings
        })
        
        return jsonify(guild_data)
    except Exception as e:
        print(f"Error getting guild: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/guild/<guild_id>/channels')
@login_required
def get_guild_channels(guild_id):
    try:
        headers = {
            'Authorization': f'Bearer {session["access_token"]}'
        }
        
        response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}/channels', headers=headers)
        if response.status_code != 200:
            return jsonify({'error': 'Failed to fetch channels'}), 500
        
        channels = response.json()
        # Filter for text channels only
        text_channels = [c for c in channels if c['type'] == 0]
        return jsonify(text_channels)
    except Exception as e:
        print(f"Error getting channels: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/guild/<guild_id>/activity')
@login_required
def get_guild_activity(guild_id):
    try:
        # Get recent activity from settings
        settings = get_guild_settings(guild_id)
        activity = settings.get('activity', [])
        return jsonify(activity)
    except Exception as e:
        print(f"Error getting activity: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/guild/<guild_id>/settings', methods=['POST'])
@login_required
def update_settings(guild_id):
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update settings
        success = update_guild_settings(guild_id, data)
        if not success:
            return jsonify({'error': 'Failed to update settings'}), 500
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error updating settings: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/guild/<guild_id>/prefix', methods=['POST'])
@login_required
def update_guild_prefix(guild_id):
    data = request.get_json()
    prefix = data.get('prefix', '?')
    
    if len(prefix) > 3:
        return jsonify({'error': 'Prefix must be 3 characters or less'}), 400
    
    # Update settings through bot connection
    settings = get_guild_settings(guild_id)
    settings['prefix'] = prefix
    update_guild_settings(guild_id, settings)
    
    # Notify bot about the change
    asyncio.run(set_bot.notify_bot(guild_id, 'prefix_update', {'prefix': prefix}))
    
    return jsonify({'success': True})

@app.route('/api/guild/<guild_id>/cogs', methods=['POST'])
@login_required
def update_guild_cogs(guild_id):
    data = request.get_json()
    cogs = data.get('cogs', [])
    
    # Update settings through bot connection
    settings = get_guild_settings(guild_id)
    settings['cogs'] = cogs
    update_guild_settings(guild_id, settings)
    
    # Notify bot about the change
    asyncio.run(set_bot.notify_bot(guild_id, 'cogs_update', {'cogs': cogs}))
    
    return jsonify({'success': True})

@app.route('/api/guild/<guild_id>/log-channel', methods=['POST'])
@login_required
def update_log_channel(guild_id):
    data = request.get_json()
    channel_id = data.get('channel_id')
    
    # Update settings through bot connection
    settings = get_guild_settings(guild_id)
    settings['log_channel'] = channel_id
    update_guild_settings(guild_id, settings)
    
    # Notify bot about the change
    asyncio.run(set_bot.notify_bot(guild_id, 'log_channel_update', {'channel_id': channel_id}))
    
    return jsonify({'success': True})

@app.route('/api/stats')
def get_bot_stats():
    settings = get_guild_settings(None)
    total_servers = len(settings)
    total_users = sum(guild.get('member_count', 0) for guild in settings.values())
    total_commands = sum(guild.get('command_count', 0) for guild in settings.values())
    
    return jsonify({
        'servers': total_servers,
        'users': total_users,
        'commands': total_commands
    })

@app.route('/api/bot/update', methods=['POST'])
def bot_update():
    # Verify bot token
    auth_header = request.headers.get('Authorization')
    if not auth_header or auth_header != f'Bearer {os.getenv("DISCORD_TOKEN")}':
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    guild_id = data.get('guild_id')
    action = data.get('action')
    action_data = data.get('data')
    
    if not all([guild_id, action, action_data]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Add activity entry
    set_bot.add_activity(guild_id, {
        'action': action,
        'data': action_data,
        'timestamp': str(datetime.datetime.utcnow())
    })
    
    return jsonify({'success': True})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 