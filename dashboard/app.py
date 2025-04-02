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
    # Additional OAuth scopes to get better access to guilds and their data
    oauth_scopes = [
        'identify',      # Get user info
        'guilds',        # List user's guilds
        'guilds.members.read'  # Read guild members
    ]
    
    scopes_param = '%20'.join(oauth_scopes)
    redirect_uri = DISCORD_REDIRECT_URI
    
    # Build the full OAuth URL with all required scopes
    oauth_url = f'https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope={scopes_param}'
    
    logger.info(f"Redirecting to Discord OAuth: {oauth_url}")
    return redirect(oauth_url)

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
    if 'access_token' not in session:
        logger.warning("No access token in session, redirecting to login")
        return redirect(url_for('login'))
    
    discord_guilds = []
    
    # Try getting guilds from Discord first
    try:
        headers = {
            'Authorization': f'Bearer {session["access_token"]}'
        }
        
        response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
        if response.status_code == 401:
            logger.warning("Access token expired, redirecting to login")
            session.clear()
            return redirect(url_for('login'))
            
        if response.status_code == 200:
            discord_guilds = response.json()
            logger.info(f"Got {len(discord_guilds)} guilds from Discord API")
        else:
            logger.error(f"Failed to fetch guilds from Discord API: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching Discord guilds: {e}")
    
    # Get bot guilds as a backup (or to merge with Discord guilds)
    bot_guilds = []
    try:
        bot_headers = {
            'Authorization': f'Bearer {os.getenv("DISCORD_TOKEN")}'
        }
        
        bot_response = requests.get('http://45.90.13.151:6150/api/guilds', 
                                 headers=bot_headers, 
                                 timeout=10)
        
        if bot_response.status_code == 200:
            bot_guilds = bot_response.json()
            logger.info(f"Got {len(bot_guilds)} guilds from bot API")
        else:
            logger.error(f"Failed to fetch guilds from bot API: {bot_response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching bot guilds: {e}")
    
    # If we failed to get Discord guilds but have bot guilds
    if not discord_guilds and bot_guilds:
        guilds = bot_guilds
        logger.info("Using bot guilds only")
    # If we have guilds from both sources, merge them
    elif discord_guilds and bot_guilds:
        # Create a map of guild IDs from Discord for quick lookups
        discord_guild_map = {g['id']: g for g in discord_guilds}
        
        # Add bot guilds if they're not already in Discord guilds
        for bot_guild in bot_guilds:
            if bot_guild['id'] not in discord_guild_map:
                discord_guilds.append(bot_guild)
                logger.info(f"Added guild from bot API: {bot_guild.get('name', 'Unknown')}")
        
        guilds = discord_guilds
        logger.info(f"Using merged guilds: {len(guilds)} total")
    else:
        # Just use whatever we got from Discord
        guilds = discord_guilds
        logger.info("Using Discord guilds only")
    
    # Pass bot token and guild list to the template
    bot_token = os.getenv('DISCORD_TOKEN')
    
    return render_template('select_server.html', guilds=guilds, bot_token=bot_token)

@app.route('/dashboard')
@login_required
def dashboard():
    guild_id = request.args.get('guild_id')
    if not guild_id:
        return redirect(url_for('select_server'))
    
    # Check if we have a valid access token
    if 'access_token' not in session:
        logger.warning("No access token in session, redirecting to login")
        return redirect(url_for('login'))
    
    # Verify user has access to this guild
    try:
        headers = {
            'Authorization': f'Bearer {session["access_token"]}'
        }
        
        response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
        if response.status_code == 401:
            logger.warning("Access token expired, redirecting to login")
            # Clear the session and redirect to login
            session.clear()
            return redirect(url_for('login'))
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch user guilds: {response.status_code}")
            guilds = []
        else:
            guilds = response.json()
    except Exception as e:
        logger.error(f"Error verifying user guild access: {e}")
        guilds = []
    
    # Check if user has access to this guild - first from Discord, then from bot if Discord fails
    has_access = any(g['id'] == guild_id for g in guilds)
    
    # If user doesn't have access according to Discord, check if the bot has the guild
    if not has_access and guilds:  # Only if Discord returned results but guild not found
        logger.warning(f"User doesn't appear to have access to guild {guild_id} via Discord API")
        try:
            # Try to get guild info from bot API
            bot_headers = {
                'Authorization': f'Bearer {os.getenv("DISCORD_TOKEN")}'
            }
            
            # Check if the bot has this guild
            bot_response = requests.get(f'http://45.90.13.151:6150/api/settings/{guild_id}', 
                                      headers=bot_headers, 
                                      timeout=10)
            
            if bot_response.status_code == 200:
                logger.info(f"Bot has access to guild {guild_id}, allowing access")
                has_access = True
        except Exception as bot_error:
            logger.error(f"Error checking bot access to guild: {bot_error}")
    
    # If user still doesn't have access after all checks, redirect
    if not has_access and guilds:  # Only enforce if we got guild data from somewhere
        logger.warning(f"User doesn't have access to guild {guild_id}, redirecting")
        return redirect(url_for('select_server'))
    
    # Try to get guild data from bot first
    try:
        # Make a direct request to the bot API for this guild
        bot_headers = {
            'Authorization': f'Bearer {os.getenv("DISCORD_TOKEN")}'
        }
        
        bot_response = requests.get(f'http://45.90.13.151:6150/api/settings/{guild_id}', 
                                   headers=bot_headers, 
                                   timeout=10)
        
        if bot_response.status_code == 200:
            bot_settings = bot_response.json()
            logger.info(f"Got settings from bot API for guild {guild_id}")
            
            # Try to get guild data from bot API too
            bot_guilds_response = requests.get('http://45.90.13.151:6150/api/guilds', 
                                             headers=bot_headers, 
                                             timeout=10)
            
            if bot_guilds_response.status_code == 200:
                bot_guilds = bot_guilds_response.json()
                matching_guild = next((g for g in bot_guilds if g['id'] == guild_id), None)
                
                if matching_guild:
                    guild_name = matching_guild.get('name', 'Unknown Server')
                    guild_icon = matching_guild.get('icon')
                    guild_icon_url = f'https://cdn.discordapp.com/icons/{guild_id}/{guild_icon}.png' if guild_icon else '/static/img/default-server.png'
                    
                    logger.info(f"Using bot guild data for {guild_id}: {guild_name}")
                    return render_template('dashboard.html', 
                                         guild_id=guild_id,
                                         guild_name=guild_name,
                                         guild_icon_url=guild_icon_url,
                                         settings=bot_settings)
    except Exception as bot_error:
        logger.error(f"Error getting guild data from bot: {bot_error}")
        logger.error(traceback.format_exc())
    
    # Fall back to Discord API if bot is unavailable
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
            logger.warning(f"Failed to fetch guild from Discord API: {guild_response.status_code}")
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
        # Try to get guild information from Discord API first with extended permissions
        headers = {
            'Authorization': f'Bearer {session["access_token"]}'
        }
        
        # Try different Discord API endpoints to get the most data
        logger.debug(f"Fetching guild data from Discord API")
        
        guild_data = None
        
        # Try the /users/@me/guilds endpoint first
        try:
            guilds_response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
            if guilds_response.status_code == 200:
                user_guilds = guilds_response.json()
                # Find the specific guild in the user's guilds
                matching_guild = next((g for g in user_guilds if g['id'] == guild_id), None)
                if matching_guild:
                    logger.info(f"Found guild in user's guilds: {matching_guild['name']}")
                    guild_data = matching_guild
                    # Store this info for future use
                    store_guild_info(guild_id, matching_guild)
        except Exception as e:
            logger.error(f"Error getting user guilds: {e}")
        
        # If we couldn't get it from /users/@me/guilds, try direct guild endpoint
        if not guild_data:
            try:
                direct_response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
                if direct_response.status_code == 200:
                    guild_data = direct_response.json()
                    logger.info(f"Got guild data directly: {guild_data['name']}")
                    # Store this info for future use
                    store_guild_info(guild_id, guild_data)
            except Exception as e:
                logger.error(f"Error getting guild directly: {e}")
        
        # Get combined data with any info we've stored plus settings
        result = get_combined_guild_data(guild_id)
        
        logger.info(f"Returning guild data: {result['name']}")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Unhandled error in get_guild: {e}")
        logger.error(traceback.format_exc())
        return jsonify(get_combined_guild_data(guild_id))

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

@app.route('/api/bot-guilds')
@login_required
def get_bot_guilds():
    """Get guilds directly from the bot API"""
    try:
        # Make a direct request to the bot API
        headers = {
            'Authorization': f'Bearer {os.getenv("DISCORD_TOKEN")}'
        }
        
        response = requests.get('http://45.90.13.151:6150/api/guilds', headers=headers, timeout=5)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            logger.error(f"Failed to get guilds from bot API: {response.status_code}")
            return jsonify([])
    except Exception as e:
        logger.error(f"Error getting bot guilds: {e}")
        logger.error(traceback.format_exc())
        return jsonify([])

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 