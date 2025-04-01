# WISP Dashboard

A modern web dashboard for managing your WISP Discord bot settings.

## Features

- Discord OAuth2 authentication
- Server selection and management
- Command prefix configuration
- Cog management (enable/disable)
- Security log channel configuration
- Server statistics tracking

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the `webpage` directory with the following variables:
   ```
   SECRET_KEY=your-secret-key-here
   DISCORD_CLIENT_ID=your-discord-client-id
   DISCORD_CLIENT_SECRET=your-discord-client-secret
   DISCORD_REDIRECT_URI=http://localhost:5000/callback
   DISCORD_BOT_TOKEN=your-bot-token
   ```

4. Set up your Discord application:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Add a bot to your application
   - Get your client ID and client secret
   - Add the redirect URI to your OAuth2 settings

5. Run the application:
   ```bash
   python app.py
   ```

6. Visit `http://localhost:5000` in your browser

## Development

The project structure is organized as follows:

```
webpage/
├── app.py              # Flask application
├── dashboard.html      # Dashboard template
├── dashboard.css       # Dashboard styles
├── dashboard.js        # Dashboard functionality
├── index.html         # Landing page
├── styles.css         # Global styles
└── requirements.txt   # Python dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 