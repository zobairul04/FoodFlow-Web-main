from django.db import models
from django.utils import timezone


class Notification(models.Model):
    """
    In-app notification system for recipients (and platform updates).
    """
    TYPE_NEW_LISTING = 'new_listing'
    TYPE_EXPIRY_ALERT = 'expiry_alert'
    TYPE_CLAIM_UPDATE = 'claim_update'
    TYPE_PICKUP_REMINDER = 'pickup_reminder'
    TYPE_SYSTEM = 'system'

    TYPE_CHOICES = [
        (TYPE_NEW_LISTING, 'New Food Listing'),
        (TYPE_EXPIRY_ALERT, 'Expiry Alert'),
        (TYPE_CLAIM_UPDATE, 'Claim Update'),
        (TYPE_PICKUP_REMINDER, 'Pickup Reminder'),
        (TYPE_SYSTEM, 'System Notification'),
    ]

    recipient = models.ForeignKey(
        'accounts.Recipient',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    listing = models.ForeignKey(
        'listings.FoodListing',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_SYSTEM
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-sent_at']

    def __str__(self):
        return f"[{self.get_notification_type_display()}] {self.title} to {self.recipient.user.username}"
