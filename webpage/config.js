const config = {
    // Discord OAuth2 Settings
    discord: {
        clientId: process.env.DISCORD_CLIENT_ID,
        clientSecret: process.env.DISCORD_CLIENT_SECRET,
        redirectUri: process.env.DISCORD_REDIRECT_URI || 'http://localhost:8888/auth/discord/callback',
        botToken: process.env.DISCORD_BOT_TOKEN,
        scope: ['identify', 'guilds', 'guilds.members.read', 'bot'],
        permissions: '8' // Administrator permissions, adjust as needed
    },

    // API Endpoints
    api: {
        baseUrl: process.env.NODE_ENV === 'production' 
            ? 'https://wispbot.site/api'
            : 'http://localhost:8888/.netlify/functions',
        endpoints: {
            auth: '/auth/discord',
            callback: '/auth/discord/callback',
            servers: '/api/servers',
            serverSettings: (serverId) => `/api/servers/${serverId}/settings`,
            updatePrefix: (serverId) => `/api/servers/${serverId}/prefix`,
            updateCogs: (serverId) => `/api/servers/${serverId}/cogs`,
            updateSecurityLog: (serverId) => `/api/servers/${serverId}/security-log`
        }
    },

    // Discord API URLs
    discordApi: {
        baseUrl: 'https://discord.com/api/v10',
        cdn: 'https://cdn.discordapp.com'
    }
};

// Helper function to validate environment variables
function validateConfig() {
    const requiredVars = [
        'DISCORD_CLIENT_ID',
        'DISCORD_CLIENT_SECRET',
        'DISCORD_BOT_TOKEN'
    ];

    const missingVars = requiredVars.filter(varName => !process.env[varName]);

    if (missingVars.length > 0) {
        console.error('Missing required environment variables:', missingVars.join(', '));
        throw new Error('Missing required environment variables');
    }
}

// Export configuration
export default config;

// Export validation function
export { validateConfig }; 