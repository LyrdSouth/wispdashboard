from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SelectMultipleField
from wtforms.validators import DataRequired, Length
import os
import discord
from discord.ext import commands
import json
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['DISCORD_CLIENT_ID'] = os.environ.get('DISCORD_CLIENT_ID')
app.config['DISCORD_CLIENT_SECRET'] = os.environ.get('DISCORD_CLIENT_SECRET')
app.config['DISCORD_REDIRECT_URI'] = os.environ.get('DISCORD_REDIRECT_URI', 'http://localhost:5000/callback')

# Forms
class PrefixForm(FlaskForm):
    prefix = StringField('Command Prefix', validators=[DataRequired(), Length(min=1, max=5)])

class CogForm(FlaskForm):
    cogs = SelectMultipleField('Enabled Cogs', choices=[
        ('admin', 'Admin'),
        ('moderation', 'Moderation'),
        ('fun', 'Fun'),
        ('utility', 'Utility'),
        ('music', 'Music'),
        ('economy', 'Economy'),
        ('welcome', 'Welcome'),
        ('logging', 'Logging')
    ])

class SecurityForm(FlaskForm):
    security_log = SelectField('Security Log Channel', coerce=str)

# Discord OAuth2
def get_discord_oauth_url():
    return f'https://discord.com/api/oauth2/authorize?client_id={app.config["DISCORD_CLIENT_ID"]}&redirect_uri={app.config["DISCORD_REDIRECT_URI"]}&response_type=code&scope=identify%20guilds'

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/login')
def login():
    return redirect(get_discord_oauth_url())

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    # Exchange code for access token
    data = {
        'client_id': app.config['DISCORD_CLIENT_ID'],
        'client_secret': app.config['DISCORD_CLIENT_SECRET'],
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': app.config['DISCORD_REDIRECT_URI']
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    if response.status_code != 200:
        return redirect(url_for('index'))
    
    token_data = response.json()
    session['user'] = token_data
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# API Routes
@app.route('/api/servers')
@login_required
def get_servers():
    # Fetch user's servers from Discord API
    headers = {'Authorization': f'Bearer {session["user"]["access_token"]}'}
    response = requests.get('https://discord.com/api/users/@me/guilds', headers=headers)
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch servers'}), 500
    
    servers = response.json()
    return jsonify(servers)

@app.route('/api/servers/<server_id>/settings')
@login_required
def get_server_settings(server_id):
    # Load server settings from database
    settings = {
        'prefix': '?',
        'enabledCogs': ['admin', 'moderation', 'fun'],
        'securityLogChannel': None,
        'channels': [],
        'stats': {
            'commandsUsed': 0,
            'activeUsers': 0,
            'avgResponseTime': 0
        }
    }
    
    # Fetch server channels
    headers = {'Authorization': f'Bot {os.environ.get("DISCORD_BOT_TOKEN")}'}
    response = requests.get(f'https://discord.com/api/guilds/{server_id}/channels', headers=headers)
    
    if response.status_code == 200:
        channels = response.json()
        settings['channels'] = [{'id': c['id'], 'name': c['name']} for c in channels if c['type'] == 0]
    
    return jsonify(settings)

@app.route('/api/servers/<server_id>/prefix', methods=['POST'])
@login_required
def update_prefix(server_id):
    data = request.get_json()
    prefix = data.get('prefix')
    
    if not prefix:
        return jsonify({'error': 'Prefix is required'}), 400
    
    # Update prefix in database
    # TODO: Implement database update
    
    return jsonify({'success': True})

@app.route('/api/servers/<server_id>/cogs', methods=['POST'])
@login_required
def update_cogs(server_id):
    data = request.get_json()
    enabled_cogs = data.get('enabledCogs', [])
    
    # Update enabled cogs in database
    # TODO: Implement database update
    
    return jsonify({'success': True})

@app.route('/api/servers/<server_id>/security-log', methods=['POST'])
@login_required
def update_security_log(server_id):
    data = request.get_json()
    channel_id = data.get('channelId')
    
    if not channel_id:
        return jsonify({'error': 'Channel ID is required'}), 400
    
    # Update security log channel in database
    # TODO: Implement database update
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True) 