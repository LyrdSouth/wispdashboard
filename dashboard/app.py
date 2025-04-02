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
from bot_connection import (
    get_guild_settings, 
    update_guild_settings, 
    get_combined_guild_data, 
    store_guild_info, 
    get_file_path,
    sync_with_bot,
    get_bot_settings
)
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
            
            # Store discord guild data for future use
            for guild in discord_guilds:
                store_guild_info(guild['id'], guild)
        else:
            logger.error(f"Failed to fetch guilds from Discord API: {response.status_code}")
    except Exception as e:
        logger.error(f"Error fetching Discord guilds: {e}")
    
    # Get any guilds we have stored locally in settings.json
    stored_guilds = []
    try:
        settings_file = get_file_path('settings.json')
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                all_settings = json.load(f)
                
                for guild_id, settings in all_settings.items():
                    if 'name' in settings:  # Only include guilds with names
                        stored_guilds.append({
                            'id': guild_id,
                            'name': settings.get('name', 'Unknown Server'),
                            'icon': settings.get('icon'),
                            'member_count': settings.get('member_count', 0)
                        })
        
        if stored_guilds:
            logger.info(f"Got {len(stored_guilds)} guilds from local storage")
    except Exception as e:
        logger.error(f"Error getting stored guilds: {e}")
    
    # Combine guilds from Discord and stored settings
    if discord_guilds:
        # If we have Discord guilds, use them as the base
        guilds = discord_guilds
        
        # Create a map of guild IDs we already have from Discord
        guild_map = {g['id']: g for g in guilds}
        
        # Add any stored guilds that aren't in our Discord list
        for stored_guild in stored_guilds:
            if stored_guild['id'] not in guild_map:
                guilds.append(stored_guild)
                logger.info(f"Added stored guild: {stored_guild['name']}")
    else:
        # If Discord API failed, just use stored guilds
        guilds = stored_guilds
    
    logger.info(f"Showing {len(guilds)} guilds total")
    
    # Sort guilds by name
    guilds.sort(key=lambda g: g.get('name', 'Unknown').lower())
    
    return render_template('select_server.html', guilds=guilds)

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
    
    # Check if user has access to this guild (if we got guild data from Discord)
    has_access = any(g['id'] == guild_id for g in guilds) if guilds else True
    
    # If user doesn't have access, redirect
    if not has_access:
        logger.warning(f"User doesn't have access to guild {guild_id}, redirecting")
        return redirect(url_for('select_server'))
    
    # Get guild data from our local settings
    guild_data = get_combined_guild_data(guild_id)
    guild_name = guild_data.get('name', 'Unknown Server')
    guild_icon = guild_data.get('icon')
    
    # If we have an access token, try to update our local data from Discord
    if 'access_token' in session:
        try:
            # Try to get guild data from Discord API
            guild_response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
            
            if guild_response.status_code == 200:
                discord_guild_data = guild_response.json()
                # Update our local storage with this fresh data
                store_guild_info(guild_id, discord_guild_data)
                
                # Update our vars for the template
                guild_name = discord_guild_data.get('name', guild_name)
                guild_icon = discord_guild_data.get('icon', guild_icon)
                logger.info(f"Updated guild info from Discord: {guild_name}")
        except Exception as e:
            logger.error(f"Error fetching guild data from Discord: {e}")
            # Continue with local data if Discord API fails
    
    # Build the icon URL
    if guild_icon:
        guild_icon_url = f'https://cdn.discordapp.com/icons/{guild_id}/{guild_icon}.png'
    else:
        guild_icon_url = '/static/img/default-server.png'
    
    # Get settings (already included in guild_data)
    settings = guild_data.get('settings', {})
    
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
        # First try to get data from remote bot
        remote_settings = {}
        try:
            remote_settings = get_bot_settings(guild_id)
            if remote_settings:
                logger.info(f"Got settings from remote bot for guild {guild_id}")
                
                # Save to local storage for future reference
                update_guild_settings(guild_id, remote_settings)
        except Exception as e:
            logger.error(f"Error fetching settings from remote bot: {e}")
        
        # Fall back to local storage if needed
        result = get_combined_guild_data(guild_id)
        
        # Try to get guild information from Discord API to update our local data
        if 'access_token' in session:
            headers = {
                'Authorization': f'Bearer {session["access_token"]}'
            }
            
            # Try different Discord API endpoints to get the most data
            logger.debug(f"Fetching guild data from Discord API")
            
            # Try to get extended guild info with special guilds.members.read scope
            try:
                logger.debug(f"Fetching detailed guild data with members.read scope")
                # First try with special endpoint that returns member count
                detailed_guild_response = requests.get(
                    f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}?with_counts=true', 
                    headers=headers
                )
                
                if detailed_guild_response.status_code == 200:
                    guild_data = detailed_guild_response.json()
                    logger.info(f"Got detailed guild data: {guild_data}")
                    
                    # Log specific fields we're interested in
                    member_count = guild_data.get('approximate_member_count', 0)
                    if member_count:
                        logger.info(f"Found approximate_member_count: {member_count}")
                    presence_count = guild_data.get('approximate_presence_count', 0)
                    if presence_count:
                        logger.info(f"Found approximate_presence_count: {presence_count}")
                    
                    # Store this detailed data
                    store_guild_info(guild_id, guild_data)
                    
                    # Get updated result with the fresh data
                    result = get_combined_guild_data(guild_id)
                    logger.info(f"Updated result has member_count: {result.get('member_count', 0)}")
                else:
                    logger.warning(f"Could not get detailed guild data: {detailed_guild_response.status_code}")
                    logger.debug(f"Response body: {detailed_guild_response.text}")
                    
                    # Fall back to regular guild info endpoint
                    guilds_response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
                    if guilds_response.status_code == 200:
                        user_guilds = guilds_response.json()
                        # Find the specific guild in the user's guilds
                        matching_guild = next((g for g in user_guilds if g['id'] == guild_id), None)
                        if matching_guild:
                            logger.info(f"Found guild in user's guilds: {matching_guild}")
                            # Try to see if we can get member count here
                            if 'approximate_member_count' in matching_guild:
                                logger.info(f"Found member count in guild data: {matching_guild['approximate_member_count']}")
                            
                            store_guild_info(guild_id, matching_guild)
                            result = get_combined_guild_data(guild_id)
            except Exception as e:
                logger.error(f"Error getting detailed guild data: {e}")
                logger.error(traceback.format_exc())
        
        logger.info(f"Returning guild data: {result['name']} (Member count: {result.get('member_count', 0)})")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Unhandled error in get_guild: {e}")
        logger.error(traceback.format_exc())
        # Return a basic fallback response that won't cause errors in the frontend
        return jsonify({
            'id': guild_id,
            'name': 'Unknown Server',
            'icon': None,
            'member_count': 0,  # Include member_count even in error response
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
        # First, check if we have cached channels
        settings = get_guild_settings(guild_id)
        if 'cached_channels' in settings and settings['cached_channels']:
            logger.info(f"Using {len(settings['cached_channels'])} cached channels for guild {guild_id}")
            return jsonify(settings['cached_channels'])
        
        # If no cached data, try Discord API
        if 'access_token' in session:
            headers = {
                'Authorization': f'Bearer {session["access_token"]}'
            }
            
            response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}/channels', headers=headers)
            if response.status_code == 200:
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
                
                # Cache the channels for future use
                settings['cached_channels'] = text_channels
                update_guild_settings(guild_id, settings)
                logger.info(f"Cached {len(text_channels)} channels for guild {guild_id}")
                
                return jsonify(text_channels)
            else:
                logger.warning(f"Failed to get channels from Discord API: {response.status_code}")
        
        # If all else fails, return an empty array
        logger.warning(f"No channels found for guild {guild_id}")
        return jsonify([])
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        logger.error(traceback.format_exc())
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
        
        # Get current settings from our local storage
        settings = get_guild_settings(guild_id)
        
        # Update prefix locally
        settings['prefix'] = prefix
        update_guild_settings(guild_id, settings)
        
        # DIRECT CONNECTION TO BOT API ON SILLYDEV
        bot_api_url = os.getenv('BOT_API_URL', 'http://45.90.13.151:6150/api')
        bot_token = os.getenv('DISCORD_TOKEN')
        
        # Prepare data for bot API
        bot_data = {
            'prefix': prefix
        }
        
        headers = {
            'Authorization': f'Bearer {bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Send API request to SillyDev bot
            bot_response = requests.post(
                f"{bot_api_url}/settings/{guild_id}", 
                headers=headers,
                json=bot_data,
                timeout=10
            )
            
            if bot_response.status_code == 200:
                logger.info(f"Guild {guild_id} prefix updated to: {prefix} (synced with bot on SillyDev)")
            else:
                logger.warning(f"Failed to sync prefix with bot API: {bot_response.status_code} - {bot_response.text}")
                # Still return success since we updated our local copy
        except Exception as bot_error:
            logger.error(f"Error connecting to bot API on SillyDev: {bot_error}")
            # Continue even if bot sync fails - we'll try again next time
            
        # Add activity entry to our local record
        timestamp = datetime.datetime.now().isoformat()
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, {
            'timestamp': timestamp,
            'action': 'prefix_update',
            'data': {'prefix': prefix}
        })
        settings['activity'] = settings['activity'][:50]  # Keep only last 50
        update_guild_settings(guild_id, settings)
            
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
        
        # Get current settings from local storage
        settings = get_guild_settings(guild_id)
        
        # Update cogs locally
        settings['cogs'] = cogs
        update_guild_settings(guild_id, settings)
        
        # DIRECT CONNECTION TO BOT API ON SILLYDEV
        bot_api_url = os.getenv('BOT_API_URL', 'http://45.90.13.151:6150/api')
        bot_token = os.getenv('DISCORD_TOKEN')
        
        # Prepare data for bot API
        bot_data = {
            'cogs': cogs
        }
        
        headers = {
            'Authorization': f'Bearer {bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Send API request to SillyDev bot
            bot_response = requests.post(
                f"{bot_api_url}/settings/{guild_id}", 
                headers=headers,
                json=bot_data,
                timeout=10
            )
            
            if bot_response.status_code == 200:
                logger.info(f"Guild {guild_id} cogs updated to: {cogs} (synced with bot on SillyDev)")
            else:
                logger.warning(f"Failed to sync cogs with bot API: {bot_response.status_code} - {bot_response.text}")
        except Exception as bot_error:
            logger.error(f"Error connecting to bot API on SillyDev: {bot_error}")
        
        # Add activity entry to our local record
        timestamp = datetime.datetime.now().isoformat()
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, {
            'timestamp': timestamp,
            'action': 'features_update',
            'data': {'cogs': cogs}
        })
        settings['activity'] = settings['activity'][:50]  # Keep only last 50
        update_guild_settings(guild_id, settings)
            
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
        
        # Get current settings from local storage
        settings = get_guild_settings(guild_id)
        
        # Update log channel locally
        settings['log_channel'] = channel_id
        update_guild_settings(guild_id, settings)
        
        # DIRECT CONNECTION TO BOT API ON SILLYDEV
        bot_api_url = os.getenv('BOT_API_URL', 'http://45.90.13.151:6150/api')
        bot_token = os.getenv('DISCORD_TOKEN')
        
        # Prepare data for bot API
        bot_data = {
            'log_channel': channel_id
        }
        
        headers = {
            'Authorization': f'Bearer {bot_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Send API request to SillyDev bot
            bot_response = requests.post(
                f"{bot_api_url}/settings/{guild_id}", 
                headers=headers,
                json=bot_data,
                timeout=10
            )
            
            if bot_response.status_code == 200:
                logger.info(f"Guild {guild_id} log channel updated to: {channel_id} (synced with bot on SillyDev)")
            else:
                logger.warning(f"Failed to sync log channel with bot API: {bot_response.status_code} - {bot_response.text}")
        except Exception as bot_error:
            logger.error(f"Error connecting to bot API on SillyDev: {bot_error}")
        
        # Add activity entry to our local record
        timestamp = datetime.datetime.now().isoformat()
        if 'activity' not in settings:
            settings['activity'] = []
        
        settings['activity'].insert(0, {
            'timestamp': timestamp,
            'action': 'log_channel_update',
            'data': {'channel_id': channel_id}
        })
        settings['activity'] = settings['activity'][:50]  # Keep only last 50
        update_guild_settings(guild_id, settings)
            
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