import config from '../config.js';

export async function handler(event, context) {
    try {
        const { code } = event.queryStringParameters;
        
        if (!code) {
            console.error('No authorization code received');
            return {
                statusCode: 400,
                body: JSON.stringify({ error: 'No authorization code provided' })
            };
        }

        const { clientId, clientSecret, redirectUri } = config.discord;
        
        // Exchange code for access token
        const tokenResponse = await fetch('https://discord.com/api/oauth2/token', {
            method: 'POST',
            body: new URLSearchParams({
                client_id: clientId,
                client_secret: clientSecret,
                code: code,
                grant_type: 'authorization_code',
                redirect_uri: redirectUri
            }),
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });

        if (!tokenResponse.ok) {
            console.error('Token exchange failed:', await tokenResponse.text());
            return {
                statusCode: 500,
                body: JSON.stringify({ error: 'Failed to exchange authorization code' })
            };
        }

        const tokens = await tokenResponse.json();
        
        // Get user data
        const userResponse = await fetch('https://discord.com/api/users/@me', {
            headers: {
                Authorization: `Bearer ${tokens.access_token}`
            }
        });

        if (!userResponse.ok) {
            console.error('Failed to fetch user data:', await userResponse.text());
            return {
                statusCode: 500,
                body: JSON.stringify({ error: 'Failed to fetch user data' })
            };
        }

        const userData = await userResponse.json();
        
        // Set cookies with user data and tokens
        const cookies = [
            `user=${JSON.stringify(userData)}; HttpOnly; Secure; SameSite=Lax`,
            `access_token=${tokens.access_token}; HttpOnly; Secure; SameSite=Lax`,
            `refresh_token=${tokens.refresh_token}; HttpOnly; Secure; SameSite=Lax`
        ];

        // Redirect to dashboard
        return {
            statusCode: 302,
            headers: {
                Location: '/dashboard',
                'Set-Cookie': cookies
            }
        };
    } catch (error) {
        console.error('Callback function error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Internal server error' })
        };
    }
} 