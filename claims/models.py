from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Claim(models.Model):
    """
    Claim model representing a reservation of donated food made by a verified Recipient.
    """
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Pickup'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    listing = models.ForeignKey(
        'listings.FoodListing',
        on_delete=models.CASCADE,
        related_name='claims'
    )
    recipient = models.ForeignKey(
        'accounts.Recipient',
        on_delete=models.CASCADE,
        related_name='claims'
    )
    claimed_quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Quantity reserved by recipient"
    )
    claimed_at = models.DateTimeField(auto_now_add=True)
    pickup_deadline = models.DateTimeField(
        help_text="Time window by which food must be picked up"
    )
    pickup_code = models.CharField(
        max_length=8,
        unique=True,
        db_index=True,
        help_text="Unique 8-character verification token"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )

    class Meta:
        verbose_name = "Claim"
        verbose_name_plural = "Claims"
        ordering = ['-claimed_at']

    def __str__(self):
        return f"Claim #{self.id} - {self.listing.food_name} ({self.claimed_quantity} {self.listing.unit}) by {self.recipient.user.username}"

    @property
    def is_expired(self):
        """
        Returns True if pending claim has surpassed pickup_deadline or listing expiry.
        """
        return self.status == self.STATUS_PENDING and (
            timezone.now() >= self.pickup_deadline or timezone.now() >= self.listing.expires_at
        )

    @property
    def can_be_cancelled(self):
        """
        Claim can be cancelled by recipient only if pending and not expired.
        """
        return self.status == self.STATUS_PENDING and not self.is_expired
