import os
import sys
import threading
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Import after setting up path
from main import bot
from dashboard.app import app

def run_bot():
    """Run the Discord bot"""
    try:
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        print(f"Error starting bot: {e}")

def run_dashboard():
    """Run the Flask dashboard"""
    try:
        # Get port from environment variable or default to 5000
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error starting dashboard: {e}")

if __name__ == "__main__":
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run the dashboard in the main thread
    run_dashboard() 