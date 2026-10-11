/**
 * FoodFlow - Expiry Countdown Script
 * Calculates and updates live remaining expiry times across food listings.
 * Note: JavaScript is strictly for presentation. Server remains authoritative.
 */

document.addEventListener('DOMContentLoaded', () => {
    function updateCountdowns() {
        const countdownElements = document.querySelectorAll('.countdown[data-expires]');

        countdownElements.forEach(el => {
            const expiresStr = el.getAttribute('data-expires');
            if (!expiresStr) return;

            const expiresTime = new Date(expiresStr).getTime();
            const now = new Date().getTime();
            const distance = expiresTime - now;

            const card = el.closest('.card, .detail-card');

            if (distance <= 0) {
                el.textContent = 'EXPIRED';
                el.classList.add('text-danger');
                
                if (card) {
                    card.classList.add('card-expired');
                    const claimBtn = card.querySelector('.btn-claim');
                    if (claimBtn) {
                        claimBtn.setAttribute('disabled', 'true');
                        claimBtn.textContent = 'Expired';
                    }
                }
                return;
            }

            // Time calculations
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            let displayText = '';
            if (days > 0) {
                displayText = `${days}d ${hours}h ${minutes}m ${seconds}s remaining`;
            } else if (hours > 0) {
                displayText = `${hours}h ${minutes}m ${seconds}s remaining`;
            } else {
                displayText = `${minutes}m ${seconds}s remaining`;
            }

            el.textContent = displayText;
        });
    }

    // Initial update and 1-second interval
    updateCountdowns();
    setInterval(updateCountdowns, 1000);
});
