// API Endpoints
const API_BASE = '/api';

// Utility Functions
const formatNumber = (num) => {
    return new Intl.NumberFormat().format(num);
};

const formatDate = (date) => {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
};

// API Functions
const api = {
    async getGuilds() {
        const response = await fetch(`${API_BASE}/guilds`);
        if (!response.ok) throw new Error('Failed to fetch guilds');
        return response.json();
    },

    async getGuildSettings(guildId) {
        const response = await fetch(`${API_BASE}/guild/${guildId}`);
        if (!response.ok) throw new Error('Failed to fetch guild settings');
        return response.json();
    },

    async getGuildChannels(guildId) {
        const response = await fetch(`${API_BASE}/guild/${guildId}/channels`);
        if (!response.ok) throw new Error('Failed to fetch channels');
        return response.json();
    },

    async getGuildActivity(guildId) {
        const response = await fetch(`${API_BASE}/guild/${guildId}/activity`);
        if (!response.ok) throw new Error('Failed to fetch activity');
        return response.json();
    },

    async updateGuildPrefix(guildId, prefix) {
        const response = await fetch(`${API_BASE}/guild/${guildId}/prefix`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prefix })
        });
        if (!response.ok) throw new Error('Failed to update prefix');
        return response.json();
    },

    async updateGuildCogs(guildId, cogs) {
        const response = await fetch(`${API_BASE}/guild/${guildId}/cogs`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cogs })
        });
        if (!response.ok) throw new Error('Failed to update cogs');
        return response.json();
    },

    async updateLogChannel(guildId, channelId) {
        const response = await fetch(`${API_BASE}/guild/${guildId}/log-channel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ channel_id: channelId })
        });
        if (!response.ok) throw new Error('Failed to update log channel');
        return response.json();
    }
};

// UI Functions
const ui = {
    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.classList.add('show');
            setTimeout(() => {
                notification.classList.remove('show');
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }, 100);
    },

    updateStats(stats) {
        document.getElementById('member-count').textContent = formatNumber(stats.member_count || 0);
        document.getElementById('command-count').textContent = formatNumber(stats.command_count || 0);
        document.getElementById('mod-actions').textContent = formatNumber(stats.mod_actions || 0);
    },

    updateActivityList(activities) {
        const activityList = document.getElementById('activity-list');
        activityList.innerHTML = '';

        if (activities.length === 0) {
            activityList.innerHTML = '<div class="no-activity">No recent activity</div>';
            return;
        }

        activities.forEach(activity => {
            const activityItem = document.createElement('div');
            activityItem.className = 'activity-item';
            activityItem.innerHTML = `
                <div class="activity-icon">
                    <i class="fas ${this.getActivityIcon(activity.type)}"></i>
                </div>
                <div class="activity-details">
                    <span class="activity-text">${activity.description}</span>
                    <span class="activity-time">${formatDate(activity.timestamp)}</span>
                </div>
            `;
            activityList.appendChild(activityItem);
        });
    },

    getActivityIcon(type) {
        const icons = {
            'ban': 'fa-ban',
            'kick': 'fa-boot',
            'timeout': 'fa-clock',
            'prefix': 'fa-terminal',
            'cog': 'fa-cog',
            'welcome': 'fa-user-plus',
            'leave': 'fa-user-minus',
            'message': 'fa-comment',
            'command': 'fa-terminal'
        };
        return icons[type] || 'fa-info-circle';
    }
};

// Event Handlers
const handlers = {
    async handleServerSelect(event) {
        const guildId = event.target.value;
        if (!guildId) return;

        try {
            const [settings, channels, activity] = await Promise.all([
                api.getGuildSettings(guildId),
                api.getGuildChannels(guildId),
                api.getGuildActivity(guildId)
            ]);

            this.updateSettings(settings);
            this.updateChannels(channels);
            ui.updateStats(settings);
            ui.updateActivityList(activity);
        } catch (error) {
            console.error('Error loading server data:', error);
            ui.showNotification('Failed to load server data', 'error');
        }
    },

    updateSettings(settings) {
        // Update prefix
        document.getElementById('prefix-input').value = settings.prefix || '?';

        // Update enabled cogs
        settings.cogs.forEach(cog => {
            const checkbox = document.querySelector(`input[name="cog"][value="${cog}"]`);
            if (checkbox) checkbox.checked = true;
        });

        // Update log channel
        const channelSelect = document.getElementById('channel-select');
        channelSelect.value = settings.log_channel || '';
    },

    updateChannels(channels) {
        const select = document.getElementById('channel-select');
        select.innerHTML = '<option value="">Select a channel</option>';

        channels.forEach(channel => {
            if (channel.type === 0) { // Text channels only
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = channel.name;
                select.appendChild(option);
            }
        });
    },

    async handlePrefixSubmit(event) {
        event.preventDefault();
        const prefix = document.getElementById('prefix-input').value;
        const guildId = document.getElementById('server-select').value;

        if (!guildId) {
            ui.showNotification('Please select a server first', 'error');
            return;
        }

        try {
            await api.updateGuildPrefix(guildId, prefix);
            ui.showNotification('Prefix updated successfully!');
        } catch (error) {
            console.error('Error updating prefix:', error);
            ui.showNotification('Failed to update prefix', 'error');
        }
    },

    async handleCogsSubmit(event) {
        event.preventDefault();
        const guildId = document.getElementById('server-select').value;
        const cogs = Array.from(document.querySelectorAll('input[name="cog"]:checked'))
            .map(checkbox => checkbox.value);

        if (!guildId) {
            ui.showNotification('Please select a server first', 'error');
            return;
        }

        try {
            await api.updateGuildCogs(guildId, cogs);
            ui.showNotification('Features updated successfully!');
        } catch (error) {
            console.error('Error updating cogs:', error);
            ui.showNotification('Failed to update features', 'error');
        }
    },

    async handleLogChannelSubmit(event) {
        event.preventDefault();
        const channelId = document.getElementById('channel-select').value;
        const guildId = document.getElementById('server-select').value;

        if (!guildId) {
            ui.showNotification('Please select a server first', 'error');
            return;
        }

        try {
            await api.updateLogChannel(guildId, channelId);
            ui.showNotification('Log channel updated successfully!');
        } catch (error) {
            console.error('Error updating log channel:', error);
            ui.showNotification('Failed to update log channel', 'error');
        }
    }
};

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Load servers
        const guilds = await api.getGuilds();
        const select = document.getElementById('server-select');
        select.innerHTML = '<option value="">Select a server</option>';
        
        guilds.forEach(guild => {
            const option = document.createElement('option');
            option.value = guild.id;
            option.textContent = guild.name;
            select.appendChild(option);
        });

        // Add event listeners
        select.addEventListener('change', (e) => handlers.handleServerSelect(e));
        document.getElementById('prefix-form').addEventListener('submit', (e) => handlers.handlePrefixSubmit(e));
        document.getElementById('cogs-form').addEventListener('submit', (e) => handlers.handleCogsSubmit(e));
        document.getElementById('log-channel-form').addEventListener('submit', (e) => handlers.handleLogChannelSubmit(e));
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        ui.showNotification('Failed to initialize dashboard', 'error');
    }
}); 