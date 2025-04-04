import os
import sys
import threading
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Check for required environment variables
required_vars = ['DISCORD_TOKEN', 'DISCORD_CLIENT_ID', 'DISCORD_CLIENT_SECRET']
missing_vars = [var for var in required_vars if not os.getenv(var)]

if missing_vars:
    print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please set these in your .env file or environment")
    sys.exit(1)

# Import after setting up path
from main import bot
from dashboard.app import app

def run_bot():
    """Run the Discord bot"""
    try:
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            print("Error: DISCORD_TOKEN not found in environment variables")
            return
        print("Starting bot with token...")
        bot.run(token)
    except Exception as e:
        print(f"Error starting bot: {e}")
        print("Bot thread will exit")

def run_dashboard():
    """Run the Flask dashboard"""
    try:
        # Get port from environment variable or default to 5000
        port = int(os.getenv('PORT', 5000))
        print(f"Starting dashboard on port {port}...")
        app.run(host='0.0.0.0', port=port, debug=False)
    except Exception as e:
        print(f"Error starting dashboard: {e}")

if __name__ == "__main__":
    print("Starting services...")
    
    # Start the bot in a separate thread
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    # Run the dashboard in the main thread
    run_dashboard() 