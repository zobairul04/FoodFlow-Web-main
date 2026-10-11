from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from locations.models import Location
from accounts.models import Donor, Recipient
from listings.models import FoodListing
from listings.services import SafetyService, ExpiryService
from claims.services import ClaimService

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds database with demo users, locations, listings, and claims for university CSE lab demonstration."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding FoodFlow demo dataset..."))

        # 1. Superuser / Admin
        admin_user, _ = User.objects.get_or_create(
            username="admin",
            defaults={'email': 'admin@foodflow.local', 'role': 'donor'}
        )
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password("admin123")
        admin_user.save()
        self.stdout.write(self.style.SUCCESS("Admin user ensured: admin / admin123"))

        # 2. Locations
        loc_dhanmondi, _ = Location.objects.get_or_create(address="House 12, Road 7", area="Dhanmondi", city="Dhaka", postal_code="1209")
        loc_gulshan, _ = Location.objects.get_or_create(address="Plot 44, Avenue 2", area="Gulshan", city="Dhaka", postal_code="1212")
        loc_banani, _ = Location.objects.get_or_create(address="Block C, Road 11", area="Banani", city="Dhaka", postal_code="1213")

        # 3. Verified Donor: Green Garden Bistro
        donor_user, created = User.objects.get_or_create(
            username="greengarden",
            defaults={'email': 'contact@greengarden.local', 'role': 'donor', 'phone': '+8801711111111'}
        )
        if created:
            donor_user.set_password("donor123")
            donor_user.save()
        donor_profile, _ = Donor.objects.get_or_create(
            user=donor_user,
            defaults={
                'donor_type': 'restaurant',
                'organization_name': 'Green Garden Bistro',
                'location': loc_dhanmondi,
                'is_verified': True
            }
        )

        # 4. Recipients: 1 Verified NGO, 1 Unverified Individual
        rec_user1, created = User.objects.get_or_create(
            username="hopefoundation",
            defaults={'email': 'care@hopefoundation.local', 'role': 'recipient', 'phone': '+8801822222222'}
        )
        if created:
            rec_user1.set_password("recipient123")
            rec_user1.save()
        rec_profile1, _ = Recipient.objects.get_or_create(
            user=rec_user1,
            defaults={
                'recipient_type': 'ngo',
                'location': loc_dhanmondi,
                'is_verified': True
            }
        )

        rec_user2, created = User.objects.get_or_create(
            username="john_doe",
            defaults={'email': 'john@example.local', 'role': 'recipient', 'phone': '+8801933333333'}
        )
        if created:
            rec_user2.set_password("recipient123")
            rec_user2.save()
        rec_profile2, _ = Recipient.objects.get_or_create(
            user=rec_user2,
            defaults={
                'recipient_type': 'individual',
                'location': loc_banani,
                'is_verified': False
            }
        )

        # 5. Food Listings across urgencies and scenarios
        now = timezone.now()

        # Listing 1: SAFE (>6h)
        l1, created = FoodListing.objects.get_or_create(
            food_name="Vegetable Biryani & Salad",
            donor=donor_profile,
            defaults={
                'description': 'Freshly prepared vegetarian biryani boxed in hygienic foil containers.',
                'quantity': Decimal('30.00'),
                'unit': 'boxes',
                'expires_at': now + timedelta(hours=12),
                'location': loc_dhanmondi,
                'status': FoodListing.STATUS_AVAILABLE
            }
        )
        SafetyService.check_food_safety(l1)
        ExpiryService.update_expiry_tracker(l1)

        # Listing 2: WARNING (2-6h)
        l2, created = FoodListing.objects.get_or_create(
            food_name="Artisan Sourdough & Croissants",
            donor=donor_profile,
            defaults={
                'description': 'Baked this morning. Includes 15 sourdough loaves and 25 butter croissants.',
                'quantity': Decimal('40.00'),
                'unit': 'pieces',
                'expires_at': now + timedelta(hours=4, minutes=30),
                'location': loc_gulshan,
                'status': FoodListing.STATUS_AVAILABLE
            }
        )
        SafetyService.check_food_safety(l2)
        ExpiryService.update_expiry_tracker(l2)

        # Listing 3: URGENT (<2h)
        l3, created = FoodListing.objects.get_or_create(
            food_name="Hot Chicken Curry & Steamed Rice",
            donor=donor_profile,
            defaults={
                'description': 'Warm dinner surplus from catering event. Ready for immediate pickup.',
                'quantity': Decimal('20.00'),
                'unit': 'portions',
                'expires_at': now + timedelta(hours=1, minutes=15),
                'location': loc_dhanmondi,
                'status': FoodListing.STATUS_AVAILABLE
            }
        )
        SafetyService.check_food_safety(l3)
        ExpiryService.update_expiry_tracker(l3)

        # Listing 4: EXPIRED (Past)
        l4, created = FoodListing.objects.get_or_create(
            food_name="Fruit Salad Bowls",
            donor=donor_profile,
            defaults={
                'description': 'Fresh mixed fruit bowls.',
                'quantity': Decimal('10.00'),
                'unit': 'bowls',
                'expires_at': now - timedelta(hours=2),
                'location': loc_dhanmondi,
                'status': FoodListing.STATUS_EXPIRED
            }
        )
        SafetyService.check_food_safety(l4)
        ExpiryService.update_expiry_tracker(l4)

        # Listing 5: BLOCKED (Unsafe keyword 'sashimi')
        l5, created = FoodListing.objects.get_or_create(
            food_name="Tuna Sashimi Platters",
            donor=donor_profile,
            defaults={
                'description': 'Leftover raw sashimi and sushi rolls.',
                'quantity': Decimal('15.00'),
                'unit': 'platters',
                'expires_at': now + timedelta(hours=5),
                'location': loc_gulshan,
                'status': FoodListing.STATUS_AVAILABLE
            }
        )
        SafetyService.check_food_safety(l5)  # Will automatically block
        ExpiryService.update_expiry_tracker(l5)

        # 6. Sample Claim: Hope Foundation claims 10 portions of Listing 1
        if l1.status == FoodListing.STATUS_AVAILABLE and l1.claims.count() == 0:
            ClaimService.create_claim(
                listing_id=l1.id,
                recipient=rec_profile1,
                quantity=Decimal('10.00')
            )

        self.stdout.write(self.style.SUCCESS(
            "Demo dataset initialized successfully:\n"
            "  - Admin: admin / admin123\n"
            "  - Verified Donor: greengarden / donor123\n"
            "  - Verified Recipient: hopefoundation / recipient123\n"
            "  - Unverified Recipient: john_doe / recipient123\n"
            "  - Demo Listings: Safe, Warning, Urgent, Expired, and Blocked (safety screening demonstration)"
        ))
