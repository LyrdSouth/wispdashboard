# WISP Bot Dashboard

A modern web dashboard for managing your Discord bot settings and monitoring its activity.

## Features

- Discord OAuth2 authentication
- Server selection and management
- Command prefix customization
- Feature toggles for different bot cogs
- Log channel configuration
- Activity monitoring
- Responsive design with dark mode support

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env` and fill in your Discord OAuth2 credentials:
   ```bash
   cp .env.example .env
   ```
5. Set up your Discord application:
   - Go to the [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to OAuth2 settings
   - Add your redirect URI (e.g., `http://localhost:5000/callback`)
   - Copy the Client ID and Client Secret to your `.env` file

6. Run the application:
   ```bash
   python app.py
   ```

## Development

The dashboard is built with:
- Flask for the backend
- Vanilla JavaScript for frontend interactivity
- CSS variables for theming
- Font Awesome for icons

## Directory Structure

```
dashboard/
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── dashboard.css
│   └── js/
│       └── dashboard.js
├── templates/
│   ├── base.html
│   ├── index.html
│   └── dashboard.html
├── app.py
├── requirements.txt
└── .env
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 