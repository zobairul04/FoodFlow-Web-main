from decimal import Decimal, InvalidOperation
from django.core.exceptions import ValidationError

UNIT_CHOICES = [
    ("", "Select a unit"),
    ("pcs", "Pieces (pcs)"),
    ("packets", "Packets"),
    ("boxes", "Boxes"),
    ("meals", "Meals"),
    ("portions", "Portions"),
    ("bottles", "Bottles"),
    ("cans", "Cans"),
    ("bowls", "Bowls"),
    ("platters", "Platters"),
    ("g", "Grams (g)"),
    ("mL", "Millilitres (mL)"),
    ("kg", "Kilograms (kg)"),
    ("L", "Litres (L)"),
]
DECIMAL_UNITS = {"kg", "L"}
ALIASES = {
    "piece": "pcs", "pieces": "pcs", "pc": "pcs",
    "kilogram": "kg", "kilograms": "kg", "kgs": "kg",
    "litre": "L", "litres": "L", "liter": "L", "liters": "L",
}


def normalize_unit(unit):
    key = str(unit or "").strip().lower()
    canonical = {value.lower(): value for value, label in UNIT_CHOICES if value}
    return ALIASES.get(key, canonical.get(key, key))


def validate_quantity(value, unit):
    unit = normalize_unit(unit)
    if unit not in {value for value, label in UNIT_CHOICES if value}:
        raise ValidationError("Please select a supported unit.")
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError("Please enter a valid quantity.")
    if not quantity.is_finite() or not Decimal("0") < quantity <= Decimal("999999.99"):
        raise ValidationError("Quantity must be greater than zero and at most 999999.99.")
    if unit not in DECIMAL_UNITS and quantity != quantity.to_integral_value():
        raise ValidationError(f"{unit} must be a whole number, such as 1, 2 or 10.")
    if quantity.as_tuple().exponent < -2:
        raise ValidationError("Use at most 2 digits after the decimal point.")
    return quantity.quantize(Decimal("0.01"))
