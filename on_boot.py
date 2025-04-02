#!/usr/bin/env python3
"""
On-boot script for SillyDev
Run this before starting the bot to fix any possible issues
"""
import os
import json
import re
import shutil
import time

def log(message):
    """Log a message with timestamp"""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def fix_indentation():
    """Fix indentation issues in main.py"""
    try:
        # Make a backup first
        shutil.copy2('main.py', f'main.py.bak-{time.strftime("%Y%m%d%H%M%S")}')
        
        with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Fix indentation for any line with too many spaces before 'return'
        pattern = re.compile(r'\n\s{8,}return')
        fixed_content = pattern.sub('\n        return', content)
        
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        log("✅ Fixed indentation in main.py")
    except Exception as e:
        log(f"❌ Error fixing indentation: {e}")

def sync_dashboard_settings():
    """Sync dashboard settings to prefixes.json"""
    try:
        # Create dashboard directory if it doesn't exist
        if not os.path.exists('dashboard'):
            os.makedirs('dashboard')
            log("✅ Created dashboard directory")
        
        # Create dashboard/settings.json if it doesn't exist
        dashboard_settings_path = os.path.join('dashboard', 'settings.json')
        if not os.path.exists(dashboard_settings_path):
            with open(dashboard_settings_path, 'w') as f:
                json.dump({}, f)
            log("✅ Created empty dashboard settings.json")
        
        # Read dashboard settings
        with open(dashboard_settings_path, 'r') as f:
            dashboard_settings = json.load(f)
        
        # Convert to prefixes format
        prefixes = {}
        for guild_id, settings in dashboard_settings.items():
            if 'prefix' in settings:
                prefixes[guild_id] = settings['prefix']
        
        # Save to prefixes.json
        with open('prefixes.json', 'w') as f:
            json.dump(prefixes, f, indent=4)
        
        log(f"✅ Synced {len(prefixes)} prefixes to prefixes.json")
    except Exception as e:
        log(f"❌ Error syncing settings: {e}")

def fix_bot_prefix_handling():
    """Fix bot's prefix handling to use dashboard/settings.json"""
    try:
        # Check if main.py exists
        if not os.path.exists('main.py'):
            log("❌ main.py not found!")
            return
        
        # Read main.py
        with open('main.py', 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Add code to look in dashboard/settings.json for prefixes
        prefix_pattern = re.compile(r'async def get_prefix\(self, message\):.*?return [^}]+?}', re.DOTALL)
        
        if prefix_pattern.search(content):
            new_get_prefix = """async def get_prefix(self, message):
        \"\"\"Get prefix for a guild\"\"\"
        if not message.guild:
            return '?'
        
        guild_id = str(message.guild.id)
        
        # Try to get prefix from cache first
        if guild_id in self.settings_cache:
            return self.settings_cache[guild_id].get('prefix', '?')
        
        # Try to load from dashboard settings
        try:
            dashboard_settings_path = os.path.join('dashboard', 'settings.json')
            if os.path.exists(dashboard_settings_path):
                with open(dashboard_settings_path, 'r') as f:
                    all_settings = json.load(f)
                    if guild_id in all_settings and 'prefix' in all_settings[guild_id]:
                        prefix = all_settings[guild_id]['prefix']
                        self.settings_cache[guild_id] = {'prefix': prefix}
                        return prefix
        except Exception as e:
            print(f"Error loading prefix from dashboard: {e}")
        
        # Fall back to prefixes.json
        try:
            if guild_id not in self.settings_cache:
                settings = get_guild_settings(guild_id)
                self.settings_cache[guild_id] = settings
            
            return self.settings_cache[guild_id].get('prefix', '?')
        except Exception as e:
            print(f"Error loading prefix: {e}")
            return '?'"""
            
            fixed_content = prefix_pattern.sub(new_get_prefix, content)
            
            with open('main.py', 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            log("✅ Fixed prefix handling in main.py")
        else:
            log("⚠️ Could not find get_prefix method to update")
    except Exception as e:
        log(f"❌ Error fixing prefix handling: {e}")

if __name__ == "__main__":
    log("🔵 Starting bot startup fixes...")
    
    fix_indentation()
    sync_dashboard_settings()
    fix_bot_prefix_handling()
    
    log("✅ All fixes applied. You can now start the bot.")
    log("📝 NOTE: If the bot is already running, please restart it to apply changes.") 