// Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Initialize mobile menu
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    menuToggle.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        overlay.classList.toggle('active');
    });

    // Initialize server selector
    const serverSelect = document.getElementById('server-select');
    loadUserServers();

    // Initialize section navigation
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.dashboard-section');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetSection = link.getAttribute('data-section');
            
            // Update active states
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            
            link.classList.add('active');
            document.getElementById(targetSection).classList.add('active');

            // Close mobile menu if open
            sidebar.classList.remove('active');
            overlay.classList.remove('active');
        });
    });

    // Handle form submissions
    const prefixForm = document.getElementById('prefix-form');
    const cogsForm = document.getElementById('cogs-form');
    const securityLogForm = document.getElementById('security-log-form');

    prefixForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prefix = document.getElementById('command-prefix').value;
        await updateServerPrefix(prefix);
    });

    cogsForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const enabledCogs = Array.from(cogsForm.querySelectorAll('input[type="checkbox"]:checked'))
            .map(checkbox => checkbox.value);
        await updateEnabledCogs(enabledCogs);
    });

    securityLogForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const channelId = document.getElementById('security-log-channel').value;
        await updateSecurityLogChannel(channelId);
    });

    // Load initial server settings
    serverSelect.addEventListener('change', () => {
        const serverId = serverSelect.value;
        if (serverId) {
            loadServerSettings(serverId);
        }
    });
});

async function loadUserServers() {
    try {
        const response = await fetch('/api/servers');
        const servers = await response.json();
        
        const serverSelect = document.getElementById('server-select');
        serverSelect.innerHTML = '<option value="">Select a server</option>';
        
        servers.forEach(server => {
            const option = document.createElement('option');
            option.value = server.id;
            option.textContent = server.name;
            serverSelect.appendChild(option);
        });
    } catch (error) {
        showNotification('Failed to load servers', 'error');
    }
}

async function loadServerSettings(serverId) {
    try {
        const response = await fetch(`/api/servers/${serverId}/settings`);
        const settings = await response.json();
        
        // Update prefix
        document.getElementById('command-prefix').value = settings.prefix || '?';
        
        // Update enabled cogs
        const cogCheckboxes = document.querySelectorAll('#cogs-form input[type="checkbox"]');
        cogCheckboxes.forEach(checkbox => {
            checkbox.checked = settings.enabled_cogs.includes(checkbox.value);
        });
        
        // Update security log channel
        const channelSelect = document.getElementById('security-log-channel');
        channelSelect.value = settings.security_log_channel || '';
        
        // Update stats
        updateStats(settings.stats);
    } catch (error) {
        showNotification('Failed to load server settings', 'error');
    }
}

async function updateServerPrefix(prefix) {
    try {
        const serverId = document.getElementById('server-select').value;
        const response = await fetch(`/api/servers/${serverId}/prefix`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prefix })
        });
        
        if (response.ok) {
            showNotification('Command prefix updated successfully', 'success');
        } else {
            throw new Error('Failed to update prefix');
        }
    } catch (error) {
        showNotification('Failed to update command prefix', 'error');
    }
}

async function updateEnabledCogs(enabledCogs) {
    try {
        const serverId = document.getElementById('server-select').value;
        const response = await fetch(`/api/servers/${serverId}/cogs`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ enabled_cogs: enabledCogs })
        });
        
        if (response.ok) {
            showNotification('Cog settings updated successfully', 'success');
        } else {
            throw new Error('Failed to update cogs');
        }
    } catch (error) {
        showNotification('Failed to update cog settings', 'error');
    }
}

async function updateSecurityLogChannel(channelId) {
    try {
        const serverId = document.getElementById('server-select').value;
        const response = await fetch(`/api/servers/${serverId}/security-log`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ channel_id: channelId })
        });
        
        if (response.ok) {
            showNotification('Security log channel updated successfully', 'success');
        } else {
            throw new Error('Failed to update security log channel');
        }
    } catch (error) {
        showNotification('Failed to update security log channel', 'error');
    }
}

function updateStats(stats) {
    document.querySelector('.stat-value:nth-child(1)').textContent = stats.commands_used || 0;
    document.querySelector('.stat-value:nth-child(2)').textContent = stats.active_users || 0;
    document.querySelector('.stat-value:nth-child(3)').textContent = `${stats.avg_response_time || 0}ms`;
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Trigger reflow
    notification.offsetHeight;
    
    notification.classList.add('show');
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
} 