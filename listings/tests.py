from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from locations.models import Location
from accounts.models import Donor
from listings.models import FoodListing, ExpiryTracker, FoodSafetyCheck
from listings.services import ExpiryService, SafetyService

User = get_user_model()


class ListingsExpiryAndSafetyTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(address="55 Lake Rd", area="Gulshan", city="Dhaka")
        self.donor_user = User.objects.create_user(username="donor_cafe", email="cafe@test.com", password="pwd", role="donor")
        self.donor = Donor.objects.create(
            user=self.donor_user,
            donor_type="restaurant",
            organization_name="Green Cafe",
            location=self.location,
            is_verified=True
        )

    def test_expiry_urgency_classification(self):
        now = timezone.now()

        # > 6 hours -> SAFE
        safe_time = now + timedelta(hours=10)
        self.assertEqual(ExpiryService.classify_urgency(safe_time), 'safe')

        # Between 2 and 6 hours -> WARNING
        warning_time = now + timedelta(hours=4)
        self.assertEqual(ExpiryService.classify_urgency(warning_time), 'warning')

        # < 2 hours -> URGENT
        urgent_time = now + timedelta(hours=1)
        self.assertEqual(ExpiryService.classify_urgency(urgent_time), 'urgent')

        # Past -> EXPIRED
        past_time = now - timedelta(minutes=10)
        self.assertEqual(ExpiryService.classify_urgency(past_time), 'expired')

    def test_safety_check_blocks_unsafe_keywords(self):
        # Listing with blocked keyword 'raw meat'
        unsafe_listing = FoodListing.objects.create(
            donor=self.donor,
            location=self.location,
            food_name="Raw Meat Packages",
            description="Fresh uncooked raw meat packages",
            quantity=Decimal("10.00"),
            unit="kg",
            expires_at=timezone.now() + timedelta(hours=5),
            status=FoodListing.STATUS_AVAILABLE
        )
        safety_check = SafetyService.check_food_safety(unsafe_listing)
        
        self.assertFalse(safety_check.is_safe)
        self.assertEqual(safety_check.risk_level, FoodSafetyCheck.RISK_HIGH)
        
        # Ensure listing status was updated to BLOCKED
        unsafe_listing.refresh_from_db()
        self.assertEqual(unsafe_listing.status, FoodListing.STATUS_BLOCKED)

        # Unsafe listing must NOT appear in visible_to_recipients
        visible = FoodListing.visible_to_recipients()
        self.assertFalse(visible.filter(pk=unsafe_listing.pk).exists())

    def test_visible_to_recipients_filters_expired_listings(self):
        # Listing in the past
        expired_listing = FoodListing.objects.create(
            donor=self.donor,
            location=self.location,
            food_name="Cooked Pasta",
            description="Warm pasta",
            quantity=Decimal("5.00"),
            unit="boxes",
            expires_at=timezone.now() - timedelta(minutes=15),
            status=FoodListing.STATUS_AVAILABLE
        )
        SafetyService.check_food_safety(expired_listing)

        visible = FoodListing.visible_to_recipients()
        self.assertFalse(visible.filter(pk=expired_listing.pk).exists())
