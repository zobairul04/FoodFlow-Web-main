import logging
from typing import List
from django.db.models import QuerySet

logger = logging.getLogger(__name__)


class LocationMatchingService:
    """
    Service responsible for matching available food listings to nearby verified recipients.
    First looks in the exact area; if fewer than 5 matches, falls back to the entire city.
    """

    @classmethod
    def find_matching_recipients(cls, location) -> QuerySet:
        """
        Find verified recipients matching the given location (area/city).
        Returns a Django QuerySet of Recipient objects.
        """
        from accounts.models import Recipient

        if not location:
            return Recipient.objects.none()

        # Step 1: Query verified recipients in the exact area and city
        area_recipients = Recipient.objects.filter(
            is_verified=True,
            location__area__iexact=location.area,
            location__city__iexact=location.city
        ).select_related('user', 'location')

        count = area_recipients.count()

        # Step 2: Fall back to entire city if fewer than 5 recipients in specific area
        if count < 5:
            city_recipients = Recipient.objects.filter(
                is_verified=True,
                location__city__iexact=location.city
            ).select_related('user', 'location')
            return city_recipients

        return area_recipients
