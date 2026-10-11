/**
 * FoodFlow - Claims Handling Script
 * Provides user feedback, confirmation dialogs, and double-submit prevention.
 */

document.addEventListener('DOMContentLoaded', () => {
    const claimForm = document.getElementById('claim-food-form');
    if (claimForm) {
        claimForm.addEventListener('submit', (e) => {
            const qtyInput = document.getElementById('id_claimed_quantity');
            const qty = qtyInput ? parseFloat(qtyInput.value) : 0;
            const max = qtyInput ? parseFloat(qtyInput.getAttribute('max')) : Infinity;

            if (!qty || qty <= 0) {
                e.preventDefault();
                alert('Please enter a valid quantity greater than zero.');
                return;
            }

            if (qty > max) {
                e.preventDefault();
                alert(`Requested quantity (${qty}) exceeds the available amount (${max}).`);
                return;
            }

            const confirmed = confirm(`Are you sure you want to reserve ${qty} of this donation? You will receive a unique 8-character pickup code.`);
            if (!confirmed) {
                e.preventDefault();
                return;
            }

            // Disable submit button to prevent accidental double clicks
            const submitBtn = claimForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = 'Reserving...';
            }
        });
    }

    // Confirmation for cancelling a claim
    const cancelForms = document.querySelectorAll('.cancel-claim-form');
    cancelForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const confirmed = confirm('Are you sure you want to cancel this claim? This will return the quantity to the donation pool.');
            if (!confirmed) {
                e.preventDefault();
            }
        });
    });
});
