from flask import Flask, render_template, redirect, url_for, request, session, jsonify
import os
from dotenv import load_dotenv
import requests
from functools import wraps
import json
from werkzeug.middleware.proxy_fix import ProxyFix

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Configure Flask for proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Discord OAuth2 settings
DISCORD_CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
DISCORD_CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
DISCORD_REDIRECT_URI = os.getenv('DISCORD_REDIRECT_URI', 'https://www.wispbot.site/callback')
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
        return redirect(url_for('dashboard'))
    return render_template('index.html')

# Ensure we handle both www and non-www domains
def get_redirect_uri():
    if request.host.startswith('www.'):
        return 'https://www.wispbot.site/callback'
    return 'https://wispbot.site/callback'

@app.route('/login')
def login():
    redirect_uri = get_redirect_uri()
    return redirect(f'https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={redirect_uri}&response_type=code&scope=identify%20guilds')

@app.route('/callback')
def callback():
    if 'error' in request.args:
        return redirect(url_for('index'))
    
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    redirect_uri = get_redirect_uri()
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    if response.status_code != 200:
        return redirect(url_for('index'))
    
    tokens = response.json()
    access_token = tokens['access_token']
    
    # Get user data
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me', headers=headers)
    if response.status_code != 200:
        return redirect(url_for('index'))
    
    user_data = response.json()
    session['user'] = user_data
    session['access_token'] = access_token
    
    return redirect(url_for('select_server'))

@app.route('/select-server')
@login_required
def select_server():
    return render_template('select_server.html')

@app.route('/dashboard')
@login_required
def dashboard():
    guild_id = request.args.get('guild_id')
    if not guild_id:
        return redirect(url_for('select_server'))
    
    # Check if user has access to this guild
    headers = {
        'Authorization': f'Bearer {session["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/users/@me/guilds', headers=headers)
    if response.status_code != 200:
        return redirect(url_for('select_server'))
    
    guilds = response.json()
    if not any(guild['id'] == guild_id for guild in guilds):
        return redirect(url_for('select_server'))
    
    return render_template('dashboard.html', user=session['user'], guild_id=guild_id)

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
    headers = {
        'Authorization': f'Bearer {session["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}', headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch guild data'}), 500
    
    guild_data = response.json()
    
    # Load custom settings from JSON file
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
            guild_settings = settings.get(str(guild_id), {})
    except FileNotFoundError:
        guild_settings = {}
    
    # Merge Discord data with custom settings
    guild_data.update({
        'prefix': guild_settings.get('prefix', '?'),
        'cogs': guild_settings.get('cogs', ['moderation', 'utility', 'image']),
        'log_channel': guild_settings.get('log_channel'),
        'member_count': guild_data.get('approximate_member_count', 0),
        'command_count': guild_settings.get('command_count', 0),
        'mod_actions': guild_settings.get('mod_actions', 0)
    })
    
    return jsonify(guild_data)

@app.route('/api/guild/<guild_id>/channels')
@login_required
def get_guild_channels(guild_id):
    headers = {
        'Authorization': f'Bearer {session["access_token"]}'
    }
    
    response = requests.get(f'{DISCORD_API_ENDPOINT}/guilds/{guild_id}/channels', headers=headers)
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch channels'}), 500
    
    return jsonify(response.json())

@app.route('/api/guild/<guild_id>/activity')
@login_required
def get_guild_activity(guild_id):
    try:
        with open('guild_activity.json', 'r') as f:
            activity = json.load(f)
            guild_activity = activity.get(str(guild_id), [])
    except FileNotFoundError:
        guild_activity = []
    
    return jsonify(guild_activity)

@app.route('/api/guild/<guild_id>/prefix', methods=['POST'])
@login_required
def update_guild_prefix(guild_id):
    data = request.get_json()
    prefix = data.get('prefix', '?')
    
    if len(prefix) > 3:
        return jsonify({'error': 'Prefix must be 3 characters or less'}), 400
    
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {}
    
    settings[str(guild_id)]['prefix'] = prefix
    
    with open('guild_settings.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    return jsonify({'success': True})

@app.route('/api/guild/<guild_id>/cogs', methods=['POST'])
@login_required
def update_guild_cogs(guild_id):
    data = request.get_json()
    cogs = data.get('cogs', [])
    
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {}
    
    settings[str(guild_id)]['cogs'] = cogs
    
    with open('guild_settings.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    return jsonify({'success': True})

@app.route('/api/guild/<guild_id>/log-channel', methods=['POST'])
@login_required
def update_log_channel(guild_id):
    data = request.get_json()
    channel_id = data.get('channel_id')
    
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    
    if str(guild_id) not in settings:
        settings[str(guild_id)] = {}
    
    settings[str(guild_id)]['log_channel'] = channel_id
    
    with open('guild_settings.json', 'w') as f:
        json.dump(settings, f, indent=4)
    
    return jsonify({'success': True})

@app.route('/api/stats')
def get_bot_stats():
    try:
        with open('guild_settings.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {}
    
    total_servers = len(settings)
    total_users = sum(guild.get('member_count', 0) for guild in settings.values())
    total_commands = sum(guild.get('command_count', 0) for guild in settings.values())
    
    return jsonify({
        'servers': total_servers,
        'users': total_users,
        'commands': total_commands
    })

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 