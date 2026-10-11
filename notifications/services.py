import logging
import secrets
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from locations.services import LocationMatchingService

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Centralized service for managing in-app notifications and email alerts.
    """

    @classmethod
    def create_notification(cls, recipient, title, message, notification_type='system', listing=None):
        """
        Creates an in-app Notification record for a recipient.
        """
        from notifications.models import Notification

        try:
            return Notification.objects.create(
                recipient=recipient,
                listing=listing,
                notification_type=notification_type,
                title=title,
                message=message,
                sent_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"Error creating notification for {recipient}: {e}")
            return None

    @classmethod
    def notify_new_listing(cls, listing):
        """
        Notifies matching verified recipients in the same area or city when a new food listing is posted.
        """
        matching_recipients = LocationMatchingService.find_matching_recipients(listing.location)
        notified_count = 0

        title = f"New Food Available: {listing.food_name}"
        local_time_str = timezone.localtime(listing.expires_at).strftime('%Y-%m-%d %I:%M %p')
        message = (
            f"A donor in {listing.location.area}, {listing.location.city} just listed {listing.quantity} {listing.unit} "
            f"of '{listing.food_name}'. Claim it before it expires at {local_time_str}!"
        )

        for recipient in matching_recipients:
            cls.create_notification(
                recipient=recipient,
                listing=listing,
                notification_type='new_listing',
                title=title,
                message=message
            )
            notified_count += 1

        logger.info(f"Notified {notified_count} recipients for new listing #{listing.id}")
        return notified_count

    @classmethod
    def notify_expiry_alert(cls, listing, urgency):
        """
        Sends expiry alerts. For urgent expiry, also triggers a console email.
        """
        from claims.models import Claim

        # Notify recipients who have pending claims on this listing
        pending_claims = listing.claims.filter(status=Claim.STATUS_PENDING).select_related('recipient__user')
        for claim in pending_claims:
            recipient = claim.recipient
            title = f"Urgent Expiry Alert: {listing.food_name}"
            deadline_str = timezone.localtime(claim.pickup_deadline).strftime('%I:%M %p')
            msg = (
                f"The food listing '{listing.food_name}' you claimed has urgency level '{urgency.upper()}'. "
                f"Please pick it up before deadline: {deadline_str}."
            )
            cls.create_notification(
                recipient=recipient,
                listing=listing,
                notification_type='expiry_alert',
                title=title,
                message=msg
            )

            # Send Email alert if urgent
            if urgency == 'urgent' and recipient.user.email:
                try:
                    send_mail(
                        subject=f"[FoodFlow Alert] Urgent Pickup Needed: {listing.food_name}",
                        message=f"Hello {recipient.user.username},\n\n{msg}\n\nYour Pickup Code: {claim.pickup_code}\n\n- FoodFlow Team",
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@foodflow.local'),
                        recipient_list=[recipient.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Failed to send email alert: {e}")

    @classmethod
    def notify_claim_created(cls, claim):
        """
        Notifies recipient with pickup details.
        """
        title = f"Claim Confirmed: {claim.listing.food_name}"
        deadline_str = timezone.localtime(claim.pickup_deadline).strftime('%Y-%m-%d %I:%M %p')
        message = (
            f"Your claim for {claim.claimed_quantity} {claim.listing.unit} of '{claim.listing.food_name}' is confirmed! "
            f"Your 8-character Pickup Code is: {claim.pickup_code}. Please pick up by {deadline_str}."
        )
        cls.create_notification(
            recipient=claim.recipient,
            listing=claim.listing,
            notification_type='claim_update',
            title=title,
            message=message
        )

    @classmethod
    def notify_claim_cancelled(cls, claim):
        """
        Notifies recipient upon claim cancellation.
        """
        title = f"Claim Cancelled: {claim.listing.food_name}"
        message = f"Your claim for {claim.claimed_quantity} {claim.listing.unit} of '{claim.listing.food_name}' has been cancelled."
        cls.create_notification(
            recipient=claim.recipient,
            listing=claim.listing,
            notification_type='claim_update',
            title=title,
            message=message
        )

    @classmethod
    def notify_pickup_completed(cls, claim):
        """
        Notifies recipient that their pickup verification was successful and completed.
        """
        title = f"Pickup Completed: {claim.listing.food_name}"
        message = (
            f"Thank you! Your pickup of {claim.claimed_quantity} {claim.listing.unit} of '{claim.listing.food_name}' "
            f"has been verified and completed successfully by the donor."
        )
        cls.create_notification(
            recipient=claim.recipient,
            listing=claim.listing,
            notification_type='pickup_reminder',
            title=title,
            message=message
        )

    @classmethod
    def notify_listing_expired(cls, listing):
        """
        Notifies affected claimants if a food listing expires before pickup.
        """
        from claims.models import Claim

        pending_claims = listing.claims.filter(status=Claim.STATUS_PENDING).select_related('recipient')
        for claim in pending_claims:
            title = f"Listing Expired: {listing.food_name}"
            msg = f"The food listing '{listing.food_name}' has expired. The pending pickup window is now closed."
            cls.create_notification(
                recipient=claim.recipient,
                listing=listing,
                notification_type='expiry_alert',
                title=title,
                message=msg
            )
