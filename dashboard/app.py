from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import os
from dotenv import load_dotenv
import requests
from functools import wraps
import json
from werkzeug.middleware.proxy_fix import ProxyFix
import logging
import traceback
import sys
from bot_connection import get_guild_settings, update_guild_settings, get_bot_settings, get_bot_channels, sync_with_bot
import asyncio
import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('dashboard')

# Load environment variables
load_dotenv()

# Get the full path for a file in the dashboard directory
def get_file_path(filename):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, filename)

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
    
    # Get actual guild data to display in the template
    try:
        guild_response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
        if guild_response.status_code == 200:
            guild_data = guild_response.json()
            guild_name = guild_data.get('name', 'Unknown Server')
            guild_icon = guild_data.get('icon')
            if guild_icon:
                guild_icon_url = f'https://cdn.discordapp.com/icons/{guild_id}/{guild_icon}.png'
            else:
                guild_icon_url = '/static/img/default-server.png'
        else:
            guild_name = 'Unknown Server'
            guild_icon_url = '/static/img/default-server.png'
    except Exception as e:
        logger.error(f"Error fetching guild data: {e}")
        guild_name = 'Error Loading Server'
        guild_icon_url = '/static/img/default-server.png'
    
    # Get current settings for this guild
    settings = get_guild_settings(guild_id)
    
    return render_template('dashboard.html', 
                           guild_id=guild_id,
                           guild_name=guild_name,
                           guild_icon_url=guild_icon_url,
                           settings=settings)

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
    logger.info(f"Getting guild {guild_id}")
    try:
        # Get guild settings from bot first
        try:
            logger.debug(f"Fetching settings for guild {guild_id} from bot")
            settings = get_bot_settings(guild_id)
            if not settings:
                # Fall back to local settings if bot is unavailable
                logger.debug(f"Bot API unavailable, using local settings")
                settings = get_guild_settings(guild_id)
            logger.debug(f"Got settings: {settings}")
        except Exception as settings_error:
            logger.error(f"Error getting guild settings: {settings_error}")
            logger.error(traceback.format_exc())
            settings = {}  # Use empty settings if there's an error
        
        # Get guild info from Discord
        try:
            headers = {
                'Authorization': f'Bearer {session["access_token"]}'
            }
            
            logger.debug(f"Fetching guild data from Discord API")
            response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
            logger.debug(f"Discord API response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch guild from Discord API: {response.status_code}")
                # Try to get guild info from settings if available
                if settings and 'name' in settings:
                    return jsonify({
                        'id': guild_id,
                        'name': settings.get('name', 'Unknown Server'),
                        'icon': settings.get('icon'),
                        'owner_id': settings.get('owner_id'),
                        'member_count': settings.get('member_count', 0),
                        'settings': settings
                    })
                else:
                    return jsonify({
                        'id': guild_id,
                        'name': 'Unknown Server',
                        'icon': None,
                        'settings': settings
                    })
            
            guild_data = response.json()
            logger.debug(f"Got guild data: {guild_data}")
            
            # Merge Discord data with settings
            result = {
                'id': guild_data.get('id', guild_id),
                'name': guild_data.get('name', 'Unknown Server'),
                'icon': guild_data.get('icon'),
                'owner_id': guild_data.get('owner_id'),
                'member_count': guild_data.get('approximate_member_count', 0),
                'settings': settings
            }
            
            logger.info(f"Successfully built guild response for {guild_id}")
            return jsonify(result)
        except Exception as discord_error:
            logger.error(f"Error getting Discord guild data: {discord_error}")
            logger.error(traceback.format_exc())
            return jsonify({
                'id': guild_id,
                'name': 'Error Loading Server',
                'icon': None,
                'settings': settings
            })
    except Exception as e:
        logger.error(f"Unhandled error in get_guild: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'id': guild_id,
            'name': 'Error',
            'icon': None,
            'settings': {
                'prefix': '?',
                'cogs': ['image', 'security'],
                'command_count': 0,
                'mod_actions': 0,
                'activity': []
            }
        })

@app.route('/api/guild/<guild_id>/channels')
@login_required
def get_guild_channels(guild_id):
    try:
        # Try to get channels from bot API first
        try:
            bot_channels = get_bot_channels(guild_id)
            if bot_channels:
                return jsonify(bot_channels)
        except Exception as e:
            logger.error(f"Error getting channels from bot: {e}")
            
        # Fall back to Discord API if bot is unavailable
        headers = {
            'Authorization': f'Bearer {session["access_token"]}'
        }
        
        response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}/channels', headers=headers)
        if response.status_code != 200:
            return jsonify([])
        
        channels = response.json()
        # Filter for text channels only
        text_channels = [
            {
                'id': c['id'],
                'name': c['name'],
                'type': c['type'],
                'position': c['position']
            }
            for c in channels if c['type'] == 0
        ]
        return jsonify(text_channels)
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        return jsonify([])

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
    try:
        data = request.get_json()
        prefix = data.get('prefix', '?')
        
        if len(prefix) > 3:
            return jsonify({'error': 'Prefix must be 3 characters or less'}), 400
        
        # Get current settings
        settings = get_guild_settings(guild_id)
        
        # Update prefix
        settings['prefix'] = prefix
        
        # Add activity entry
        timestamp = datetime.datetime.now().isoformat()
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, {
            'timestamp': timestamp,
            'action': 'prefix_update',
            'data': {'prefix': prefix}
        })
        settings['activity'] = settings['activity'][:50]  # Keep only last 50
        
        # Save settings to bot directly
        success = sync_with_bot(guild_id, settings)
        
        # If bot sync fails, try local update
        if not success:
            success = update_guild_settings(guild_id, settings)
            
        if not success:
            return jsonify({'error': 'Failed to save prefix'}), 500
            
        logger.info(f"Guild {guild_id} prefix updated to: {prefix}")
        return jsonify({'success': True, 'prefix': prefix})
    except Exception as e:
        logger.error(f"Error updating prefix: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/guild/<guild_id>/cogs', methods=['POST'])
@login_required
def update_guild_cogs(guild_id):
    try:
        data = request.get_json()
        cogs = data.get('cogs', [])
        
        # Get current settings
        settings = get_guild_settings(guild_id)
        
        # Update cogs
        settings['cogs'] = cogs
        
        # Add activity entry
        timestamp = datetime.datetime.now().isoformat()
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, {
            'timestamp': timestamp,
            'action': 'features_update',
            'data': {'cogs': cogs}
        })
        settings['activity'] = settings['activity'][:50]  # Keep only last 50
        
        # Save settings to bot directly
        success = sync_with_bot(guild_id, settings)
        
        # If bot sync fails, try local update
        if not success:
            success = update_guild_settings(guild_id, settings)
            
        if not success:
            return jsonify({'error': 'Failed to save features'}), 500
            
        logger.info(f"Guild {guild_id} cogs updated to: {cogs}")
        return jsonify({'success': True, 'cogs': cogs})
    except Exception as e:
        logger.error(f"Error updating cogs: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/guild/<guild_id>/log-channel', methods=['POST'])
@login_required
def update_guild_log_channel(guild_id):
    try:
        data = request.get_json()
        channel_id = data.get('channel_id')
        
        # Get current settings
        settings = get_guild_settings(guild_id)
        
        # Update log channel
        settings['log_channel'] = channel_id
        
        # Add activity entry
        timestamp = datetime.datetime.now().isoformat()
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, {
            'timestamp': timestamp,
            'action': 'log_channel_update',
            'data': {'channel_id': channel_id}
        })
        settings['activity'] = settings['activity'][:50]  # Keep only last 50
        
        # Save settings to bot directly
        success = sync_with_bot(guild_id, settings)
        
        # If bot sync fails, try local update
        if not success:
            success = update_guild_settings(guild_id, settings)
            
        if not success:
            return jsonify({'error': 'Failed to save log channel'}), 500
            
        logger.info(f"Guild {guild_id} log channel updated to: {channel_id}")
        return jsonify({'success': True, 'log_channel': channel_id})
    except Exception as e:
        logger.error(f"Error updating log channel: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_bot_stats():
    # Get stats from all guilds
    try:
        total_servers = 0
        total_commands = 0
        total_mod_actions = 0
        total_users = 0
        
        # Load all settings
        try:
            settings_file = get_file_path('settings.json')
            with open(settings_file, 'r') as f:
                all_settings = json.load(f)
                total_servers = len(all_settings)
                
                for guild_id, settings in all_settings.items():
                    total_commands += settings.get('command_count', 0)
                    total_mod_actions += settings.get('mod_actions', 0)
                    total_users += settings.get('member_count', 0)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading settings file: {e}")
            pass
        
        return jsonify({
            'servers': total_servers,
            'commands': total_commands,
            'modActions': total_mod_actions,
            'users': total_users
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'servers': 0,
            'commands': 0,
            'modActions': 0,
            'users': 0
        })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 