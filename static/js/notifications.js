/**
 * FoodFlow - Notifications Polling Script
 * Periodically polls the unread notifications count for authenticated recipients.
 */

document.addEventListener('DOMContentLoaded', () => {
    const badge = document.getElementById('navbar-unread-badge');
    if (!badge) return; // Not on an authenticated page with notifications

    function checkUnreadCount() {
        fetch('/notifications/unread-count/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Network response was not ok');
        })
        .then(data => {
            if (data && typeof data.unread_count !== 'undefined') {
                const count = data.unread_count;
                if (count > 0) {
                    badge.textContent = count;
                    badge.style.display = 'inline-flex';
                } else {
                    badge.style.display = 'none';
                }
            }
        })
        .catch(err => {
            // Silently handle polling errors in console
            console.debug('Notification poll:', err);
        });
    }

    // Check periodically every 60 seconds
    setInterval(checkUnreadCount, 60000);
});
