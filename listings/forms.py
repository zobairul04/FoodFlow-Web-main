from decimal import Decimal
from datetime import timedelta
from django import forms
from django.conf import settings
from django.utils import timezone
from .models import FoodListing
from .quantities import UNIT_CHOICES, normalize_unit, validate_quantity


class FoodListingForm(forms.ModelForm):
    """
    Form for creating and updating surplus Food Listings by Donors.
    Includes embedded location fields to allow custom pickup spots.
    """
    unit = forms.ChoiceField(choices=UNIT_CHOICES, widget=forms.Select(attrs={"class": "form-input"}))

    address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Street address for pickup'})
    )
    area = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Area / Neighborhood'})
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'City'})
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Postal code'})
    )

    class Meta:
        model = FoodListing
        fields = ['food_name', 'description', 'quantity', 'unit', 'expires_at']
        widgets = {
            'food_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 50 Lunch Boxes (Rice & Chicken)'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3, 'placeholder': 'Food condition, ingredients, allergen info, packaging details...'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-input', 'step': '1', 'min': '1', 'placeholder': 'e.g. 25'}),
            'expires_at': forms.DateTimeInput(
                attrs={'class': 'form-input', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_unit = normalize_unit(self.instance.unit) if self.instance.pk else None
        if self.instance.pk:
            self.initial["unit"] = self.original_unit

    def clean(self):
        cleaned = super().clean()
        quantity = cleaned.get("quantity")
        unit = cleaned.get("unit")
        if quantity is not None and unit:
            try:
                cleaned["quantity"] = validate_quantity(quantity, unit)
            except forms.ValidationError as error:
                self.add_error("quantity", error)
        if self.instance.pk:
            if unit and unit != self.original_unit and self.instance.claims.exists():
                self.add_error("unit", "Unit cannot be changed after a claim has been made.")
            if quantity is not None and quantity < self.instance.quantity_reserved:
                self.add_error("quantity", "Total quantity cannot be less than pending and completed claims.")
        return cleaned

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is None or quantity <= Decimal('0.00'):
            raise forms.ValidationError("Quantity must be greater than zero.")
        return quantity

    def clean_expires_at(self):
        expires_at = self.cleaned_data.get('expires_at')
        if not expires_at:
            raise forms.ValidationError("Expiry date and time is required.")

        now = timezone.now()
        conf = getattr(settings, 'FOODFLOW_SETTINGS', {})
        min_minutes = conf.get('MIN_EXPIRY_MINUTES', 30)
        max_hours = conf.get('MAX_EXPIRY_HOURS', 72)

        min_allowed = now + timedelta(minutes=min_minutes)
        max_allowed = now + timedelta(hours=max_hours)

        if expires_at <= now:
            raise forms.ValidationError("Expiry date/time must be in the future.")

        if expires_at < min_allowed:
            raise forms.ValidationError(f"Expiry must be at least {min_minutes} minutes into the future to allow sufficient time for pickup.")

        if expires_at > max_allowed:
            raise forms.ValidationError(f"Expiry cannot exceed {max_hours} hours ({max_hours // 24} days) from now.")

        return expires_at
