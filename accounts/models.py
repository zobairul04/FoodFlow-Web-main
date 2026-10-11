from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for FoodFlow supporting distinct roles: Donor or Recipient.
    Extends Django's AbstractUser to maintain full built-in authentication support.
    """
    ROLE_DONOR = 'donor'
    ROLE_RECIPIENT = 'recipient'

    ROLE_CHOICES = [
        (ROLE_DONOR, 'Donor'),
        (ROLE_RECIPIENT, 'Recipient'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_RECIPIENT,
        help_text="Designates whether this user registers as a food Donor or Recipient."
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Contact telephone number"
    )

    @property
    def is_donor(self):
        return self.role == self.ROLE_DONOR

    @property
    def is_recipient(self):
        return self.role == self.ROLE_RECIPIENT

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Donor(models.Model):
    """
    Profile for Food Donors (Restaurants, Households, Grocers, Event organizers, etc.).
    """
    DONOR_TYPE_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('household', 'Household'),
        ('grocer', 'Grocer / Supermarket'),
        ('event', 'Event / Catering'),
        ('other', 'Other Donor'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='donor_profile'
    )
    donor_type = models.CharField(
        max_length=30,
        choices=DONOR_TYPE_CHOICES,
        default='restaurant'
    )
    organization_name = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Business or organization name (optional for households)"
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='donors'
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Designates if this donor is verified by platform administrators"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Donor Profile"
        verbose_name_plural = "Donor Profiles"

    def __str__(self):
        name = self.organization_name or self.user.get_full_name() or self.user.username
        return f"{name} [{self.get_donor_type_display()}]"


class Recipient(models.Model):
    """
    Profile for Food Recipients (NGOs, Individuals, Shelters, Community Kitchens, etc.).
    """
    RECIPIENT_TYPE_CHOICES = [
        ('ngo', 'NGO / Non-profit'),
        ('individual', 'Individual / Family in need'),
        ('shelter', 'Shelter / Orphanage'),
        ('community_kitchen', 'Community Kitchen / Charity'),
        ('other', 'Other Recipient'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='recipient_profile'
    )
    recipient_type = models.CharField(
        max_length=30,
        choices=RECIPIENT_TYPE_CHOICES,
        default='individual'
    )
    location = models.ForeignKey(
        'locations.Location',
        on_delete=models.PROTECT,
        related_name='recipients'
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Designates if this recipient is verified by platform administrators (required to claim food)"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Recipient Profile"
        verbose_name_plural = "Recipient Profiles"

    def __str__(self):
        return f"{self.user.username} [{self.get_recipient_type_display()}]"
