from django.test import TestCase
from django.contrib.auth import get_user_model
from locations.models import Location
from locations.services import LocationMatchingService
from accounts.models import Recipient

User = get_user_model()


class LocationMatchingServiceTests(TestCase):
    def setUp(self):
        self.loc1 = Location.objects.create(address="10 Road", area="Banani", city="Dhaka")
        self.loc2 = Location.objects.create(address="20 Road", area="Mirpur", city="Dhaka")
        self.loc3 = Location.objects.create(address="30 Road", area="GEC", city="Chittagong")

        # Create 2 verified recipients in Banani, Dhaka
        for i in range(2):
            u = User.objects.create_user(username=f"banani_rec_{i}", email=f"b_{i}@t.com", password="pwd", role="recipient")
            Recipient.objects.create(user=u, recipient_type="ngo", location=self.loc1, is_verified=True)

        # Create 1 unverified recipient in Banani (should not be matched)
        unv_user = User.objects.create_user(username="banani_unv", email="unv@t.com", password="pwd", role="recipient")
        Recipient.objects.create(user=unv_user, recipient_type="individual", location=self.loc1, is_verified=False)

        # Create 4 verified recipients in Mirpur, Dhaka (same city, different area)
        for i in range(4):
            u = User.objects.create_user(username=f"mirpur_rec_{i}", email=f"m_{i}@t.com", password="pwd", role="recipient")
            Recipient.objects.create(user=u, recipient_type="shelter", location=self.loc2, is_verified=True)

        # Create 1 verified in Chittagong
        u_ctg = User.objects.create_user(username="ctg_rec", email="c@t.com", password="pwd", role="recipient")
        Recipient.objects.create(user=u_ctg, recipient_type="ngo", location=self.loc3, is_verified=True)

    def test_matching_fallback_to_same_city_when_area_count_under_five(self):
        # In Banani we have 2 verified recipients (< 5).
        # LocationMatchingService should fall back to entire city (Dhaka), finding 2 (Banani) + 4 (Mirpur) = 6 verified recipients.
        matches = LocationMatchingService.find_matching_recipients(self.loc1)
        self.assertEqual(matches.count(), 6)
        # Chittagong recipient must NOT be included
        self.assertFalse(matches.filter(location__city="Chittagong").exists())
