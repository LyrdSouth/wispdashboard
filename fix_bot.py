#!/usr/bin/env python3
import os
import re
import json

def fix_indentation():
    """Fix the indentation issue in main.py"""
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the indentation issues on lines with "return" that have excess indentation
        # This matches any line with more than 8 spaces followed by "return"
        pattern = re.compile(r'\n\s{8,}return\n')
        fixed_content = pattern.sub('\n        return\n', content)
        
        with open('main.py', 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        
        print("✅ Fixed indentation issues in main.py")
    except Exception as e:
        print(f"❌ Error fixing indentation: {e}")

def ensure_dashboard_settings():
    """Ensure the bot can access dashboard settings"""
    try:
        # Get dashboard settings path
        dashboard_settings_path = os.path.join('dashboard', 'settings.json')
        
        # Check if dashboard settings file exists
        if os.path.exists(dashboard_settings_path):
            # Copy dashboard settings to bot's settings file
            with open(dashboard_settings_path, 'r', encoding='utf-8') as f:
                dashboard_settings = json.load(f)
            
            # Convert dashboard settings to prefix format for the bot
            prefixes = {}
            for guild_id, settings in dashboard_settings.items():
                if 'prefix' in settings:
                    prefixes[guild_id] = settings['prefix']
            
            # Save to prefixes.json
            with open('prefixes.json', 'w', encoding='utf-8') as f:
                json.dump(prefixes, f, indent=4)
            
            print(f"✅ Synchronized {len(prefixes)} prefixes from dashboard to bot")
        else:
            print("⚠️ Dashboard settings file not found")
    except Exception as e:
        print(f"❌ Error ensuring settings: {e}")

def fix_settings_file_path():
    """Ensure the bot uses the correct settings file path"""
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update the settings file path to use dashboard's settings.json
        settings_path_line = "SETTINGS_FILE = 'settings.json'"
        new_settings_path = "SETTINGS_FILE = os.path.join('dashboard', 'settings.json')"
        
        if settings_path_line in content:
            fixed_content = content.replace(settings_path_line, new_settings_path)
            
            with open('main.py', 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            print("✅ Updated settings file path in main.py")
        else:
            print("⚠️ Could not find settings file path to update")
    except Exception as e:
        print(f"❌ Error fixing settings path: {e}")

if __name__ == "__main__":
    print("🔧 Starting bot fixes...")
    fix_indentation()
    fix_settings_file_path()
    ensure_dashboard_settings()
    print("✅ All fixes applied. Restart your bot now.") 