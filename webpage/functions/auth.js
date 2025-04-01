import config from '../config.js';

export async function handler(event, context) {
    try {
        const { clientId, redirectUri, scope, permissions } = config.discord;
        
        // Validate required configuration
        if (!clientId || !redirectUri) {
            console.error('Missing required Discord configuration');
            return {
                statusCode: 500,
                body: JSON.stringify({ error: 'Server configuration error' })
            };
        }
        
        // Construct Discord OAuth2 URL
        const discordAuthUrl = new URL('https://discord.com/api/oauth2/authorize');
        discordAuthUrl.searchParams.append('client_id', clientId);
        discordAuthUrl.searchParams.append('redirect_uri', redirectUri);
        discordAuthUrl.searchParams.append('response_type', 'code');
        discordAuthUrl.searchParams.append('scope', scope.join(' '));
        discordAuthUrl.searchParams.append('permissions', permissions);
        
        console.log('Redirecting to Discord OAuth2:', discordAuthUrl.toString());
        
        // Redirect to Discord's OAuth2 page
        return {
            statusCode: 302,
            headers: {
                Location: discordAuthUrl.toString(),
                'Cache-Control': 'no-cache'
            }
        };
    } catch (error) {
        console.error('Auth function error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Internal server error' })
        };
    }
} 