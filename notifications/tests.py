from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from locations.models import Location
from accounts.models import Recipient
from notifications.models import Notification
from notifications.services import NotificationService

User = get_user_model()


class NotificationTests(TestCase):
    def setUp(self):
        self.location = Location.objects.create(address="12 Central Rd", area="Uttara", city="Dhaka")

        self.user1 = User.objects.create_user(username="rec1", email="rec1@test.com", password="pwd", role="recipient")
        self.recipient1 = Recipient.objects.create(user=self.user1, recipient_type="individual", location=self.location, is_verified=True)

        self.user2 = User.objects.create_user(username="rec2", email="rec2@test.com", password="pwd", role="recipient")
        self.recipient2 = Recipient.objects.create(user=self.user2, recipient_type="ngo", location=self.location, is_verified=True)

    def test_notification_creation_and_isolation(self):
        # Create notification for recipient1
        NotificationService.create_notification(
            recipient=self.recipient1,
            title="Surplus Bread",
            message="10 loafs available nearby",
            notification_type="new_listing"
        )

        self.assertEqual(Notification.objects.filter(recipient=self.recipient1).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.recipient2).count(), 0)

        # Check JSON unread count endpoint with recipient1 logged in
        self.client.login(username="rec1", password="pwd")
        response = self.client.get(reverse('notifications:unread_count_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['unread_count'], 1)

        # Login as recipient2 and verify unread count is 0
        self.client.login(username="rec2", password="pwd")
        response2 = self.client.get(reverse('notifications:unread_count_json'))
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['unread_count'], 0)
