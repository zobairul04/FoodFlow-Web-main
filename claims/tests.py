from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from locations.models import Location
from accounts.models import Donor, Recipient
from listings.models import FoodListing
from listings.services import SafetyService, ExpiryService
from claims.models import Claim
from claims.services import ClaimService

User = get_user_model()


class ClaimsServiceAndWorkflowTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(address="100 Park Ave", area="Dhanmondi", city="Dhaka")

        # Donor
        self.donor_user = User.objects.create_user(username="bistro", email="bistro@test.com", password="pwd", role="donor")
        self.donor = Donor.objects.create(user=self.donor_user, donor_type="restaurant", location=self.location, is_verified=True)

        # Verified Recipient
        self.recipient_user = User.objects.create_user(username="shelter_org", email="shelter@test.com", password="pwd", role="recipient")
        self.recipient = Recipient.objects.create(user=self.recipient_user, recipient_type="shelter", location=self.location, is_verified=True)

        # Unverified Recipient
        self.unverified_user = User.objects.create_user(username="unverified_rec", email="unv@test.com", password="pwd", role="recipient")
        self.unverified_rec = Recipient.objects.create(user=self.unverified_user, recipient_type="individual", location=self.location, is_verified=False)

        # Food Listing (20 portions)
        self.listing = FoodListing.objects.create(
            donor=self.donor,
            location=self.location,
            food_name="Vegetable Khichuri",
            description="Freshly cooked warm meal",
            quantity=Decimal("20.00"),
            unit="portions",
            expires_at=timezone.now() + timedelta(hours=4),
            status=FoodListing.STATUS_AVAILABLE
        )
        SafetyService.check_food_safety(self.listing)
        ExpiryService.update_expiry_tracker(self.listing)

    def test_successful_claim_and_pickup_workflow(self):
        # 1. Verified recipient claims 12 portions
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("12.00")
        )
        self.assertIsNotNone(claim)
        self.assertEqual(claim.status, Claim.STATUS_PENDING)
        self.assertEqual(len(claim.pickup_code), 8)

        # Check remaining listing availability
        self.assertEqual(self.listing.quantity_available, Decimal("8.00"))
        self.assertEqual(self.listing.status, FoodListing.STATUS_AVAILABLE)

        # 2. Donor verifies pickup code
        completed_claim = ClaimService.verify_and_complete_pickup(
            pickup_code=claim.pickup_code,
            donor_user=self.donor_user
        )
        self.assertEqual(completed_claim.status, Claim.STATUS_COMPLETED)

    def test_unverified_recipient_cannot_claim(self):
        with self.assertRaises(ValidationError):
            ClaimService.create_claim(
                listing_id=self.listing.id,
                recipient=self.unverified_rec,
                quantity=Decimal("5.00")
            )

    def test_cannot_claim_more_than_available_quantity(self):
        with self.assertRaises(ValidationError):
            ClaimService.create_claim(
                listing_id=self.listing.id,
                recipient=self.recipient,
                quantity=Decimal("50.00")  # exceeds 20
            )

    def test_unauthorized_user_cannot_verify_pickup(self):
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("5.00")
        )

        other_user = User.objects.create_user(username="other_donor", email="other@test.com", password="pwd", role="donor")
        Donor.objects.create(user=other_user, donor_type="household", location=self.location, is_verified=True)

        with self.assertRaises(ValidationError):
            ClaimService.verify_and_complete_pickup(
                pickup_code=claim.pickup_code,
                donor_user=other_user  # Wrong donor
            )

    def test_invalid_pickup_code_rejected(self):
        """Test that invalid, malformed or non-existent pickup codes are rejected."""
        with self.assertRaises(ValidationError):
            ClaimService.verify_and_complete_pickup(pickup_code="SHORT", donor_user=self.donor_user)

        with self.assertRaises(ValidationError):
            ClaimService.verify_and_complete_pickup(pickup_code="XXXXXXXX", donor_user=self.donor_user)

    def test_completed_pickup_cannot_be_completed_again(self):
        """Test that a completed claim cannot be verified a second time."""
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("5.00")
        )
        ClaimService.verify_and_complete_pickup(pickup_code=claim.pickup_code, donor_user=self.donor_user)

        with self.assertRaises(ValidationError):
            ClaimService.verify_and_complete_pickup(pickup_code=claim.pickup_code, donor_user=self.donor_user)

    def test_cancelled_claim_cannot_be_completed(self):
        """Test that cancelled claim cannot be verified."""
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("5.00")
        )
        ClaimService.cancel_claim(claim_id=claim.id, user=self.recipient_user)

        with self.assertRaises(ValidationError):
            ClaimService.verify_and_complete_pickup(pickup_code=claim.pickup_code, donor_user=self.donor_user)

    def test_unverified_recipient_blocked_at_view_level(self):
        """Test that unverified recipients attempting to POST a claim are blocked."""
        self.client.force_login(self.unverified_user)
        from django.urls import reverse
        response = self.client.post(reverse('claims:claim_create', kwargs={'listing_id': self.listing.id}), {
            'claimed_quantity': '5.00'
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Claim.objects.filter(recipient=self.unverified_rec).count(), 0)

    def test_anonymous_user_can_access_claims_page_without_login_redirect(self):
        """Test that anyone can access /claims/ without being forcefully redirected to login."""
        from django.urls import reverse
        response = self.client.get(reverse('claims:my_claims'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Track Claim by 8-Character Pickup Code")
        self.assertContains(response, "Log In to View Claims")

    def test_anonymous_user_can_lookup_claim_by_pickup_code(self):
        """Test that an unauthenticated user can look up a valid claim by pickup code."""
        from django.urls import reverse
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("5.00")
        )
        response = self.client.get(reverse('claims:my_claims'), {'pickup_code': claim.pickup_code})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.listing.food_name)
        self.assertContains(response, "Reserved Quantity:")

    def test_donor_can_access_claims_page_and_view_incoming_claims(self):
        """Test that a Donor can access /claims/ and see incoming claims on their listings."""
        from django.urls import reverse
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("6.00")
        )
        self.client.force_login(self.donor_user)
        response = self.client.get(reverse('claims:my_claims'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Incoming Food Claims")
        self.assertContains(response, self.listing.food_name)
        self.assertContains(response, self.recipient_user.username)
        self.assertContains(response, "Verify Pickup")

    def test_recipient_can_access_claims_page_and_view_own_claims(self):
        """Test that a Recipient can access /claims/ and see their pickup code and claim."""
        from django.urls import reverse
        claim = ClaimService.create_claim(
            listing_id=self.listing.id,
            recipient=self.recipient,
            quantity=Decimal("4.00")
        )
        self.client.force_login(self.recipient_user)
        response = self.client.get(reverse('claims:my_claims'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Food Claims")
        self.assertContains(response, claim.pickup_code)
