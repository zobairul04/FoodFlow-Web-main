import secrets
import logging
from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from listings.quantities import validate_quantity

logger = logging.getLogger(__name__)


class ClaimService:
    """
    Handles race-condition safe food claim creation, cancellation, and donor pickup verification.
    """

    @classmethod
    def generate_unique_pickup_code(cls) -> str:
        """
        Generates an 8-character uppercase hexadecimal token and guarantees database uniqueness.
        """
        from claims.models import Claim

        for _ in range(20):
            code = secrets.token_hex(4).upper()
            if not Claim.objects.filter(pickup_code=code).exists():
                return code
        # Fallback if extremely dense
        return secrets.token_hex(4).upper()

    @classmethod
    def create_claim(cls, listing_id: int, recipient, quantity: Decimal):
        """
        Thread-safe claim creation using transaction.atomic() and select_for_update().
        Validates all server-side rules.
        """
        from listings.models import FoodListing
        from claims.models import Claim
        from notifications.services import NotificationService

        if not recipient.is_verified:
            raise ValidationError("Only verified recipients are eligible to claim food donations.")



        with transaction.atomic():
            try:
                listing = FoodListing.objects.select_for_update().get(pk=listing_id)
            except FoodListing.DoesNotExist:
                raise ValidationError("The requested food listing does not exist.")

            # Rule 1: Check listing status
            if listing.status != FoodListing.STATUS_AVAILABLE:
                raise ValidationError(f"This food listing is currently {listing.get_status_display().lower()} and cannot be claimed.")

            # Rule 2: Check expiration
            if listing.expires_at <= timezone.now():
                listing.status = FoodListing.STATUS_EXPIRED
                listing.save(update_fields=['status', 'updated_at'])
                raise ValidationError("This food listing has already expired.")

            # Rule 3: Check food safety
            if hasattr(listing, 'safety_check') and not listing.safety_check.is_safe:
                raise ValidationError("This listing cannot be claimed as it did not pass the food safety screening.")

            quantity = validate_quantity(quantity, listing.unit)

            # Rule 4: Check available quantity
            available = listing.quantity_available
            if quantity > available:
                raise ValidationError(f"Requested quantity ({quantity} {listing.unit}) exceeds currently available amount ({available} {listing.unit}).")

            # Calculate pickup deadline
            conf = getattr(settings, 'FOODFLOW_SETTINGS', {})
            pickup_window_mins = conf.get('PICKUP_WINDOW_MINUTES', 90)
            window_deadline = timezone.now() + timedelta(minutes=pickup_window_mins)
            pickup_deadline = min(listing.expires_at, window_deadline)

            pickup_code = cls.generate_unique_pickup_code()

            claim = Claim.objects.create(
                listing=listing,
                recipient=recipient,
                claimed_quantity=quantity,
                pickup_deadline=pickup_deadline,
                pickup_code=pickup_code,
                status=Claim.STATUS_PENDING
            )

            # Update listing status if fully claimed
            if listing.quantity_available <= Decimal('0.00'):
                listing.status = FoodListing.STATUS_CLAIMED
                listing.save(update_fields=['status', 'updated_at'])

            # Send in-app and alert notifications
            NotificationService.notify_claim_created(claim)

            return claim

    @classmethod
    def cancel_claim(cls, claim_id: int, user):
        """
        Safely cancels a pending claim and restores available quantity to the listing.
        """
        from claims.models import Claim
        from listings.models import FoodListing
        from notifications.services import NotificationService

        with transaction.atomic():
            try:
                claim = Claim.objects.select_for_update().select_related('listing', 'recipient__user').get(pk=claim_id)
            except Claim.DoesNotExist:
                raise ValidationError("Claim not found.")

            if claim.recipient.user != user and not user.is_staff:
                raise ValidationError("You are not authorized to cancel this claim.")

            if claim.status != Claim.STATUS_PENDING:
                raise ValidationError(f"Cannot cancel a claim with status: {claim.get_status_display()}.")

            claim.status = Claim.STATUS_CANCELLED
            claim.save(update_fields=['status'])

            # If listing was marked claimed, restore it to available if time has not passed
            listing = claim.listing
            if listing.status == FoodListing.STATUS_CLAIMED and listing.expires_at > timezone.now():
                listing.status = FoodListing.STATUS_AVAILABLE
                listing.save(update_fields=['status', 'updated_at'])

            NotificationService.notify_claim_cancelled(claim)
            return claim

    @classmethod
    def verify_and_complete_pickup(cls, pickup_code: str, donor_user):
        """
        Verifies the 8-character pickup code submitted by a Donor and completes the pickup.
        """
        from claims.models import Claim
        from listings.models import FoodListing
        from notifications.services import NotificationService

        cleaned_code = (pickup_code or '').strip().upper()
        if not cleaned_code or len(cleaned_code) != 8:
            raise ValidationError("Please provide a valid 8-character pickup code.")

        with transaction.atomic():
            try:
                claim = Claim.objects.select_for_update().select_related('listing__donor__user', 'recipient__user').get(
                    pickup_code=cleaned_code
                )
            except Claim.DoesNotExist:
                raise ValidationError("Invalid pickup code. No matching claim found.")

            # Check donor ownership
            if claim.listing.donor.user != donor_user and not donor_user.is_staff:
                raise ValidationError("Unauthorized: You are not the donor for this food listing.")

            if claim.status == Claim.STATUS_COMPLETED:
                raise ValidationError("This pickup code has already been verified and completed.")

            if claim.status in [Claim.STATUS_CANCELLED, Claim.STATUS_EXPIRED]:
                raise ValidationError(f"Cannot complete pickup for a claim that is {claim.get_status_display().lower()}.")

            # Mark claim completed
            claim.status = Claim.STATUS_COMPLETED
            claim.save(update_fields=['status'])

            # If all quantity is claimed/completed and no pending items remain, complete listing
            listing = claim.listing
            pending_count = listing.claims.filter(status=Claim.STATUS_PENDING).count()
            if listing.quantity_available <= Decimal('0.00') and pending_count == 0:
                listing.status = FoodListing.STATUS_COMPLETED
                listing.save(update_fields=['status', 'updated_at'])

            NotificationService.notify_pickup_completed(claim)
            return claim
