from decimal import Decimal
from django import forms
from django.core.validators import MinValueValidator
from .models import Claim
from listings.quantities import DECIMAL_UNITS, normalize_unit, validate_quantity


class ClaimForm(forms.Form):
    """
    Form used by verified Recipients to claim a quantity of food.
    """
    claimed_quantity = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '1',
            'min': '1',
            'id': 'id_claimed_quantity',
            'placeholder': 'Enter quantity to claim'
        }),
        label="Quantity to Claim"
    )

    def __init__(self, *args, max_available=None, unit="units", **kwargs):
        super().__init__(*args, **kwargs)
        self.max_available = max_available
        self.unit = normalize_unit(unit)
        step = "0.01" if self.unit in DECIMAL_UNITS else "1"
        self.fields["claimed_quantity"].widget.attrs.update({"min": step, "step": step})
        if max_available is not None:
            self.fields['claimed_quantity'].widget.attrs['max'] = str(max_available)
            self.fields['claimed_quantity'].help_text = f"Available to claim: up to {max_available} {unit}"

    def clean_claimed_quantity(self):
        qty = validate_quantity(self.cleaned_data.get('claimed_quantity'), self.unit)
        if qty is None or qty <= Decimal('0.00'):
            raise forms.ValidationError("Please enter a valid quantity greater than zero.")
        if self.max_available is not None and qty > self.max_available:
            raise forms.ValidationError(f"Cannot claim more than the available quantity ({self.max_available}).")
        return qty


class PickupVerificationForm(forms.Form):
    """
    Form used by Donors to verify the 8-character pickup code presented by the recipient.
    """
    pickup_code = forms.CharField(
        max_length=8,
        min_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-input code-input',
            'placeholder': '8-CHAR CODE (e.g. 4F9B2C1A)',
            'style': 'text-transform: uppercase; letter-spacing: 0.15em; font-family: monospace; font-size: 1.25rem; text-align: center;'
        }),
        label="Enter Recipient's Pickup Code"
    )

    def clean_pickup_code(self):
        code = self.cleaned_data.get('pickup_code', '').strip().upper()
        if len(code) != 8:
            raise forms.ValidationError("Pickup code must be exactly 8 characters long.")
        return code
