import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

BLOCKED_KEYWORDS = [
    'raw meat',
    'raw fish',
    'alcohol',
    'opened',
    'unpasteurized',
    'sashimi',
    'sushi',
]


class ExpiryService:
    """
    Centralized service for computing expiry urgency, updating trackers,
    and handling expiry status transitions.
    """

    @classmethod
    def get_settings(cls):
        return getattr(settings, 'FOODFLOW_SETTINGS', {
            'URGENCY_WARNING_HOURS': 6,
            'URGENCY_URGENT_HOURS': 2,
            'PICKUP_WINDOW_MINUTES': 90,
            'MIN_EXPIRY_MINUTES': 30,
            'MAX_EXPIRY_HOURS': 72,
        })

    @classmethod
    def classify_urgency(cls, expires_at) -> str:
        """
        Classifies urgency level based on configured hour thresholds:
        - EXPIRED: <= 0 hours
        - URGENT: < URGENCY_URGENT_HOURS (default 2 hours)
        - WARNING: <= URGENCY_WARNING_HOURS (default 6 hours)
        - SAFE: > 6 hours
        """
        now = timezone.now()
        if expires_at <= now:
            return 'expired'

        remaining = expires_at - now
        conf = cls.get_settings()
        urgent_delta = timedelta(hours=conf.get('URGENCY_URGENT_HOURS', 2))
        warning_delta = timedelta(hours=conf.get('URGENCY_WARNING_HOURS', 6))

        if remaining < urgent_delta:
            return 'urgent'
        elif remaining <= warning_delta:
            return 'warning'
        else:
            return 'safe'

    @classmethod
    def update_expiry_tracker(cls, listing):
        """
        Creates or updates ExpiryTracker instance for the given FoodListing.
        """
        from listings.models import ExpiryTracker

        urgency = cls.classify_urgency(listing.expires_at)
        tracker, created = ExpiryTracker.objects.get_or_create(
            listing=listing,
            defaults={
                'expires_at': listing.expires_at,
                'urgency_level': urgency,
                'alert_sent': False
            }
        )

        if not created:
            tracker.expires_at = listing.expires_at
            tracker.urgency_level = urgency
            tracker.save()

        return tracker

    @classmethod
    def check_and_update_listing_expiration(cls, listing):
        """
        If a listing has expired, updates its status to 'expired' and urgency level to 'expired'.
        """
        from listings.models import FoodListing

        if listing.expires_at <= timezone.now() and listing.status in [FoodListing.STATUS_AVAILABLE, FoodListing.STATUS_CLAIMED]:
            listing.status = FoodListing.STATUS_EXPIRED
            listing.save(update_fields=['status', 'updated_at'])
            cls.update_expiry_tracker(listing)
            return True
        return False


class SafetyService:
    """
    Automated basic safety keyword screening service.
    Inspects food name and description for forbidden/high-risk items.
    """

    @classmethod
    def check_food_safety(cls, listing):
        """
        Evaluates listing against safety rules and creates/updates FoodSafetyCheck record.
        """
        from listings.models import FoodSafetyCheck, FoodListing

        text_to_check = f"{listing.food_name} {listing.description or ''}".lower()
        has_blocked_keyword = any(keyword in text_to_check for keyword in BLOCKED_KEYWORDS)

        if has_blocked_keyword:
            is_safe = False
            risk_level = FoodSafetyCheck.RISK_HIGH
            # Block listing immediately
            if listing.status != FoodListing.STATUS_BLOCKED:
                listing.status = FoodListing.STATUS_BLOCKED
                listing.save(update_fields=['status', 'updated_at'])
        elif not listing.donor.is_verified:
            # Unverified donor items get medium risk but remain safe for verified recipients
            is_safe = True
            risk_level = FoodSafetyCheck.RISK_MEDIUM
        else:
            is_safe = True
            risk_level = FoodSafetyCheck.RISK_LOW

        safety_check, created = FoodSafetyCheck.objects.get_or_create(
            listing=listing,
            defaults={
                'risk_level': risk_level,
                'safe_until': listing.expires_at,
                'is_safe': is_safe,
            }
        )

        if not created:
            safety_check.risk_level = risk_level
            safety_check.safe_until = listing.expires_at
            safety_check.is_safe = is_safe
            safety_check.save()

        return safety_check
