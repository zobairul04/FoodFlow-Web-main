import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from listings.models import FoodListing, ExpiryTracker
from listings.services import ExpiryService
from claims.models import Claim
from notifications.services import NotificationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sweeps database for expired food listings and claims, updating status and triggering alerts."

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(self.style.NOTICE(f"[{now.strftime('%Y-%m-%d %H:%M:%S UTC')}] Starting FoodFlow Expiry Sweep..."))

        expired_listings_count = 0
        urgency_updated_count = 0
        expired_claims_count = 0

        # 1. Sweep expired Food Listings
        expired_listings = FoodListing.objects.filter(
            expires_at__lte=now,
            status__in=[FoodListing.STATUS_AVAILABLE, FoodListing.STATUS_CLAIMED]
        ).select_related('expiry_tracker')

        for listing in expired_listings:
            try:
                with transaction.atomic():
                    listing.status = FoodListing.STATUS_EXPIRED
                    listing.save(update_fields=['status', 'updated_at'])

                    tracker, _ = ExpiryTracker.objects.get_or_create(
                        listing=listing,
                        defaults={'expires_at': listing.expires_at}
                    )
                    tracker.urgency_level = ExpiryTracker.URGENCY_EXPIRED
                    tracker.save(update_fields=['urgency_level', 'last_checked_at'])

                    # Notify recipients with pending claims
                    if not tracker.alert_sent:
                        NotificationService.notify_listing_expired(listing)
                        tracker.alert_sent = True
                        tracker.save(update_fields=['alert_sent'])

                    expired_listings_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing expired listing #{listing.id}: {e}"))

        # 2. Sweep active listings to update urgency levels and send urgent warnings
        active_listings = FoodListing.objects.filter(
            status=FoodListing.STATUS_AVAILABLE,
            expires_at__gt=now
        ).select_related('expiry_tracker')

        for listing in active_listings:
            try:
                new_urgency = ExpiryService.classify_urgency(listing.expires_at)
                tracker, created = ExpiryTracker.objects.get_or_create(
                    listing=listing,
                    defaults={'expires_at': listing.expires_at, 'urgency_level': new_urgency}
                )

                if tracker.urgency_level != new_urgency or created:
                    tracker.urgency_level = new_urgency
                    tracker.save(update_fields=['urgency_level', 'last_checked_at'])
                    urgency_updated_count += 1

                # Send email and in-app alert when urgent and not previously sent
                if new_urgency == ExpiryTracker.URGENCY_URGENT and not tracker.alert_sent:
                    NotificationService.notify_expiry_alert(listing, new_urgency)
                    tracker.alert_sent = True
                    tracker.save(update_fields=['alert_sent'])

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error checking active listing #{listing.id}: {e}"))

        # 3. Sweep pending claims past their pickup deadline
        expired_claims = Claim.objects.filter(
            status=Claim.STATUS_PENDING,
            pickup_deadline__lte=now
        ).select_related('listing')

        for claim in expired_claims:
            try:
                with transaction.atomic():
                    claim.status = Claim.STATUS_EXPIRED
                    claim.save(update_fields=['status'])

                    # If listing was marked claimed but still unexpired, restore to available
                    listing = claim.listing
                    if listing.status == FoodListing.STATUS_CLAIMED and listing.expires_at > now:
                        listing.status = FoodListing.STATUS_AVAILABLE
                        listing.save(update_fields=['status', 'updated_at'])

                    expired_claims_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error expiring claim #{claim.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Expiry sweep completed successfully:\n"
            f"  - Listings marked expired: {expired_listings_count}\n"
            f"  - Listings urgency refreshed: {urgency_updated_count}\n"
            f"  - Pending claims timed out: {expired_claims_count}"
        ))
