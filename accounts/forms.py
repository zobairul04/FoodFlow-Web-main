from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from locations.models import Location
from .models import Donor, Recipient

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    """
    Unified registration form handling User account creation, Role assignment,
    Location creation/reuse, and Donor/Recipient profile initialization.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Enter strong password'}),
        label="Password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm your password'}),
        label="Confirm Password"
    )

    # Donor specific
    donor_type = forms.ChoiceField(
        choices=Donor.DONOR_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    organization_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Green Bakery / Mom\'s Kitchen'})
    )

    # Recipient specific
    recipient_type = forms.ChoiceField(
        choices=Recipient.RECIPIENT_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # Location fields
    address = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'House #, Road #, Street name'})
    )
    area = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Dhanmondi / Downtown / Brooklyn'})
    )
    city = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Dhaka / New York'})
    )
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Postal code (optional)'})
    )

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'phone',
            'role',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your first name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter your last name',
            }),
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose a username'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. +1234567890'}),
            'role': forms.Select(attrs={'class': 'form-select', 'id': 'id_role_select'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise forms.ValidationError("Email is required.")
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', "Passwords do not match.")
            else:
                # Validate password against Django's configured password validators
                try:
                    dummy_user = User(
                        username=cleaned_data.get('username', ''),
                        email=cleaned_data.get('email', '')
                    )
                    validate_password(password, user=dummy_user)
                except forms.ValidationError as error:
                    self.add_error('password', error)

        role = cleaned_data.get("role")
        if role == User.ROLE_DONOR:
            if not cleaned_data.get("donor_type"):
                self.add_error('donor_type', "Please select a donor type.")
        elif role == User.ROLE_RECIPIENT:
            if not cleaned_data.get("recipient_type"):
                self.add_error('recipient_type', "Please select a recipient category.")

        return cleaned_data


class UserLoginForm(AuthenticationForm):
    """
    Standard clean login form supporting login with either username or registered email.
    """
    username = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username or Email', 'autocomplete': 'username'})
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Password', 'autocomplete': 'current-password'})
    )

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username is not None and password:
            clean_username = username.strip()
            # If input is an email, look up the corresponding user's username
            matched_user = User.objects.filter(email__iexact=clean_username).first()
            lookup_username = matched_user.username if matched_user else clean_username

            self.user_cache = authenticate(
                self.request,
                username=lookup_username,
                password=password
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user contact details and location.
    """
    organization_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    address = forms.CharField(max_length=255, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    area = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    city = forms.CharField(max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-input'}))
    postal_code = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'phone']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
        }
