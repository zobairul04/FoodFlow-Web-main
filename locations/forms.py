from django import forms
from .models import Location


class LocationForm(forms.ModelForm):
    """
    Form used for creating or associating addresses.
    Reuses existing locations using get_or_create logic in services/views.
    """
    class Meta:
        model = Location
        fields = ['address', 'area', 'city', 'postal_code', 'latitude', 'longitude']
        widgets = {
            'address': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 123 Main Street, Apt 4B'}),
            'area': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Downtown / Banani / Gulshan'}),
            'city': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Dhaka'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1213'}),
            'latitude': forms.HiddenInput(),
            'longitude': forms.HiddenInput(),
        }

    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if not address:
            raise forms.ValidationError("Address is required.")
        return address

    def clean_area(self):
        area = self.cleaned_data.get('area', '').strip()
        if not area:
            raise forms.ValidationError("Area is required.")
        return area

    def clean_city(self):
        city = self.cleaned_data.get('city', '').strip()
        if not city:
            raise forms.ValidationError("City is required.")
        return city
