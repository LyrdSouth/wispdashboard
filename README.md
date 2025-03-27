# Discord Moderation Bot Template

A feature-rich Discord bot template with moderation commands, message snipe functionality, and image conversion capabilities.

## Features

### Moderation Commands
- `?ban` - Ban a user from the server
- `?kick` - Kick a user from the server
- `?timeout` - Timeout a user for a specified duration
- `?untimeout` - Remove timeout from a user
- `?unban` - Unban a user from the server

All moderation commands:
- Support user mentions and IDs
- Include reason logging
- Send DM notifications to affected users
- Check role hierarchy
- Include error handling

### Utility Commands
- `?snipe` - Show the last deleted message in the channel
- `?prefix` - Show the current command prefix
- `?setprefix` - Change the command prefix (Admin only)
- `?gif` - Convert an image to GIF format (reply to an image)

## Setup

1. Clone this repository
2. Install required packages:
```bash
pip install discord.py python-dotenv Pillow aiohttp
```

3. Create a `.env` file in the root directory with your bot token:
```
DISCORD_TOKEN=your_bot_token_here
```

4. Run the bot:
```bash
python main.py
```

## Configuration

### Required Intents
- Message Content
- Members

### Custom Prefixes
The bot supports custom prefixes per server, stored in `prefixes.json`. The default prefix is `?`.

## Features in Detail

### Moderation System
- Role hierarchy checks to prevent abuse
- Comprehensive error handling
- DM notifications for affected users
- Reason logging for all actions
- Support for both member mentions and user IDs

### Message Snipe
- Stores the last deleted message per server
- Shows message content, author, and timestamp
- Includes attachment links if present

### Image Conversion
- Converts images to GIF format
- Handles various image formats
- Preserves transparency
- Supports image attachments

## Contributing

Feel free to fork this repository and submit pull requests. This template is designed to be easily customizable and extensible.

## License

This project is open source and available under the MIT License. Feel free to use this code in your own projects. 