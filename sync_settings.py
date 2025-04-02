#!/usr/bin/env python3
import os
import json
import sys
import time
import shutil

def log(message):
    """Log a message with timestamp"""
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def sync_dashboard_to_bot():
    """Copy settings from dashboard to bot's prefixes.json"""
    dashboard_settings_path = os.path.join('dashboard', 'settings.json')
    
    if not os.path.exists(dashboard_settings_path):
        log("🔴 Dashboard settings file not found!")
        return False
    
    try:
        # Read dashboard settings
        with open(dashboard_settings_path, 'r', encoding='utf-8') as f:
            dashboard_settings = json.load(f)
        
        # Convert to prefix format
        prefixes = {}
        for guild_id, settings in dashboard_settings.items():
            if 'prefix' in settings:
                prefixes[guild_id] = settings['prefix']
        
        # Write to prefixes.json
        with open('prefixes.json', 'w', encoding='utf-8') as f:
            json.dump(prefixes, f, indent=4)
        
        log(f"🟢 Successfully synced {len(prefixes)} prefixes from dashboard to bot")
        for guild_id, prefix in prefixes.items():
            log(f"  • Guild {guild_id}: prefix = '{prefix}'")
        
        return True
    except Exception as e:
        log(f"🔴 Error syncing settings: {e}")
        return False

def create_backup(file_path):
    """Create a backup of a file"""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup-{time.strftime('%Y%m%d%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        log(f"🟢 Created backup: {backup_path}")
        return True
    return False

def main():
    """Main function"""
    log("🔵 Starting settings synchronization...")
    
    # Create backups
    create_backup('prefixes.json')
    create_backup(os.path.join('dashboard', 'settings.json'))
    
    # Sync settings
    if sync_dashboard_to_bot():
        log("✅ Settings synchronization completed successfully")
    else:
        log("❌ Settings synchronization failed")

if __name__ == "__main__":
    main() 