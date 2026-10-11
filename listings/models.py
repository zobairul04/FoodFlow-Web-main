from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum


class FoodListing(models.Model):
    """
    Core Food Listing model representing food donations posted by Donors.
    """
    STATUS_AVAILABLE = 'available'
    STATUS_CLAIMED = 'claimed'
    STATUS_COMPLETED = 'completed'
    STATUS_EXPIRED = 'expired'
    STATUS_BLOCKED = 'blocked'

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, 'Available'),
        (STATUS_CLAIMED, 'Claimed'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_BLOCKED, 'Blocked'),
    ]

    donor = models.ForeignKey(
        'accounts.Donor',
        on_delete=models.CASCADE,
        related_name='listings'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='listings'
    )
    food_name = models.CharField(max_length=200, help_text="e.g. Cooked Rice & Curry, Fresh Apples, Bread Rolls")
    description = models.TextField(blank=True, null=True, help_text="Preparation details, ingredients, or dietary info")
    quantity = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total initial quantity"
    )
    unit = models.CharField(
        max_length=50,
        help_text="Units: portions, kg, boxes, packets, meals, litres"
    )
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="Exact expiry deadline"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
        db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Food Listing"
        verbose_name_plural = "Food Listings"
        ordering = ['expires_at']

    def __str__(self):
        return f"{self.food_name} ({self.quantity} {self.unit}) - {self.get_status_display()}"

    @classmethod
    def visible_to_recipients(cls):
        """
        Layer 1 Query-time filtering:
        Returns only listings that are available, have not passed expiry, and passed safety check.
        Recipients must ALWAYS use this query method.
        """
        return cls.objects.filter(
            status=cls.STATUS_AVAILABLE,
            expires_at__gt=timezone.now(),
            safety_check__is_safe=True
        ).select_related('donor', 'location', 'safety_check', 'expiry_tracker')

    @property
    def remaining_time(self):
        """
        Calculates remaining duration dynamically (never stored).
        """
        now = timezone.now()
        if self.expires_at > now:
            return self.expires_at - now
        return timezone.timedelta(0)

    @property
    def is_expired(self):
        """
        Returns True if current time has surpassed expires_at.
        """
        return timezone.now() >= self.expires_at

    @property
    def quantity_reserved(self):
        from claims.models import Claim

        quantities = self.claims.filter(
            status__in=[Claim.STATUS_PENDING, Claim.STATUS_COMPLETED]
        ).values_list("claimed_quantity", flat=True)

        return sum(quantities, Decimal("0.00"))

    @property
    def quantity_available(self):
        remaining = self.quantity - self.quantity_reserved

        return max(
            Decimal("0.00"), remaining
        ).quantize(Decimal("0.01"))

    @property
    def urgency_display(self):
        """
        Returns urgency string computed by ExpiryService or ExpiryTracker.
        """
        if hasattr(self, 'expiry_tracker') and self.expiry_tracker:
            return self.expiry_tracker.urgency_level.upper()
        
        from listings.services import ExpiryService
        return ExpiryService.classify_urgency(self.expires_at).upper()


class ExpiryTracker(models.Model):
    """
    Expiry tracker for food listings to track urgency classifications and alerts.
    """
    URGENCY_SAFE = 'safe'
    URGENCY_WARNING = 'warning'
    URGENCY_URGENT = 'urgent'
    URGENCY_EXPIRED = 'expired'

    URGENCY_CHOICES = [
        (URGENCY_SAFE, 'Safe'),
        (URGENCY_WARNING, 'Warning'),
        (URGENCY_URGENT, 'Urgent'),
        (URGENCY_EXPIRED, 'Expired'),
    ]

    listing = models.OneToOneField(
        FoodListing,
        on_delete=models.CASCADE,
        related_name='expiry_tracker'
    )
    expires_at = models.DateTimeField()
    urgency_level = models.CharField(
        max_length=20,
        choices=URGENCY_CHOICES,
        default=URGENCY_SAFE
    )
    alert_sent = models.BooleanField(
        default=False,
        help_text="Prevents duplicate urgent or expiry notifications"
    )
    last_checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Expiry Tracker"
        verbose_name_plural = "Expiry Trackers"

    def __str__(self):
        return f"Tracker for {self.listing.food_name} [{self.get_urgency_level_display()}]"

    @property
    def remaining_time(self):
        now = timezone.now()
        if self.expires_at > now:
            return self.expires_at - now
        return timezone.timedelta(0)


class FoodSafetyCheck(models.Model):
    """
    Safety inspection records generated by SafetyService automated keyword screening.
    """
    RISK_LOW = 'low'
    RISK_MEDIUM = 'medium'
    RISK_HIGH = 'high'

    RISK_CHOICES = [
        (RISK_LOW, 'Low Risk'),
        (RISK_MEDIUM, 'Medium Risk'),
        (RISK_HIGH, 'High Risk'),
    ]

    listing = models.OneToOneField(
        FoodListing,
        on_delete=models.CASCADE,
        related_name='safety_check'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_CHOICES,
        default=RISK_LOW
    )
    safe_until = models.DateTimeField(blank=True, null=True)
    is_safe = models.BooleanField(
        default=True,
        help_text="Whether this listing passed platform safety screening"
    )
    checked_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Food Safety Check"
        verbose_name_plural = "Food Safety Checks"

    def __str__(self):
        status = "Passed" if self.is_safe else "Blocked/Failed"
        return f"Safety: {self.listing.food_name} - {self.get_risk_level_display()} ({status})"
