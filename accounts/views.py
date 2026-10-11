from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from locations.models import Location
from listings.models import FoodListing
from claims.models import Claim
from notifications.models import Notification
from .models import User, Donor, Recipient
from .forms import UserRegistrationForm, UserLoginForm, ProfileUpdateForm


def get_dashboard_redirect(user):
    """
    Directs authenticated users to their corresponding dashboard or admin panel.
    """
    if user.is_superuser or user.is_staff:
        return redirect('admin:index')
    elif user.is_donor:
        return redirect('accounts:donor_dashboard')
    elif user.is_recipient:
        return redirect('accounts:recipient_dashboard')
    return redirect('home')


def home_view(request):
    """
    Public homepage showcasing FoodFlow concept, platform metrics, and quick actions.
    """
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

    total_listings = FoodListing.objects.count()
    active_available = FoodListing.visible_to_recipients().count()
    completed_rescues = Claim.objects.filter(status=Claim.STATUS_COMPLETED).count()
    verified_donors = Donor.objects.filter(is_verified=True).count()

    # Recent available listings for preview
    recent_listings = FoodListing.visible_to_recipients()[:6]

    context = {
        'total_listings': total_listings,
        'active_available': active_available,
        'completed_rescues': completed_rescues,
        'verified_donors': verified_donors,
        'recent_listings': recent_listings,
    }
    return render(request, 'home.html', context)


def register_view(request):
    """
    Handles registration for both Donors and Recipients with atomic location linking.
    """
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Create Location (reusing identical address records)
                    address = form.cleaned_data['address'].strip()
                    area = form.cleaned_data['area'].strip()
                    city = form.cleaned_data['city'].strip()
                    postal_code = form.cleaned_data.get('postal_code', '').strip() or None

                    location, _ = Location.objects.get_or_create(
                        address=address,
                        area=area,
                        city=city,
                        postal_code=postal_code,
                    )

                    # 2. Create User
                    user = User.objects.create_user(
                        username=form.cleaned_data['username'],
                        first_name=form.cleaned_data.get('first_name', ''),
                        last_name=form.cleaned_data.get('last_name', ''),
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password'],
                        phone=form.cleaned_data.get('phone', ''),
                        role=form.cleaned_data['role'],
                    )

                    # 3. Create Role Profile
                    if user.role == User.ROLE_DONOR:
                        Donor.objects.create(
                            user=user,
                            donor_type=form.cleaned_data['donor_type'],
                            organization_name=form.cleaned_data.get('organization_name', ''),
                            location=location,
                            is_verified=False  # Must be approved by admin
                        )
                    else:
                        Recipient.objects.create(
                            user=user,
                            recipient_type=form.cleaned_data['recipient_type'],
                            location=location,
                            is_verified=False  # Must be approved by admin
                        )

                    login(request, user)
                    messages.success(request, f"Welcome to FoodFlow, {user.username}! Your account has been created successfully.")
                    return get_dashboard_redirect(user)

            except Exception as e:
                messages.error(request, f"Registration failed due to a server error: {e}")
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    """
    Handles user authentication with username or email and directs to role-based dashboards.
    """
    if request.user.is_authenticated:
        return get_dashboard_redirect(request.user)

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")

            # Verify redirect target is safe against open redirect vulnerabilities
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)

            return get_dashboard_redirect(user)
        else:
            messages.error(request, "Invalid username/email or password. Please try again.")
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """
    Logs out the current authenticated user and redirects to home.
    Supports both GET and POST requests.
    """
    if request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been logged out successfully.")
    return redirect('home')


@login_required
def profile_view(request):
    """
    Displays and allows logged-in users to update their profile and address.
    """
    user = request.user
    location = None
    profile = None

    if user.is_donor and hasattr(user, 'donor_profile'):
        profile = user.donor_profile
        location = profile.location
    elif user.is_recipient and hasattr(user, 'recipient_profile'):
        profile = user.recipient_profile
        location = profile.location

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, instance=user)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()

                # Update organization name if donor
                if user.is_donor and profile:
                    profile.organization_name = form.cleaned_data.get('organization_name', '')
                    profile.save()

                # Update or reuse location
                new_loc, _ = Location.objects.get_or_create(
                    address=form.cleaned_data['address'].strip(),
                    area=form.cleaned_data['area'].strip(),
                    city=form.cleaned_data['city'].strip(),
                    postal_code=form.cleaned_data.get('postal_code', '').strip() or None,
                )
                if profile:
                    profile.location = new_loc
                    profile.save()

                messages.success(request, "Your profile details have been updated successfully.")
                return redirect('accounts:profile')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        initial_data = {}
        if location:
            initial_data.update({
                'address': location.address,
                'area': location.area,
                'city': location.city,
                'postal_code': location.postal_code or '',
            })
        if user.is_donor and profile:
            initial_data['organization_name'] = profile.organization_name or ''

        form = ProfileUpdateForm(instance=user, initial=initial_data)

    context = {
        'form': form,
        'profile': profile,
        'location': location,
    }
    return render(request, 'accounts/profile.html', context)


@login_required
def donor_dashboard_view(request):
    """
    Donor Dashboard displaying listing stats, active donations, and pending pickup codes to verify.
    """
    if not request.user.is_donor:
        messages.error(request, "Access restricted: Donor account required.")
        return redirect('accounts:recipient_dashboard')

    donor = getattr(request.user, 'donor_profile', None)
    if not donor:
        messages.error(request, "Donor profile not found. Please complete your registration.")
        return redirect('accounts:profile')

    listings = donor.listings.all().select_related('location', 'expiry_tracker', 'safety_check')

    total_listings = listings.count()
    available_count = listings.filter(status=FoodListing.STATUS_AVAILABLE, expires_at__gt=timezone.now()).count()
    claimed_count = listings.filter(status=FoodListing.STATUS_CLAIMED).count()
    completed_count = listings.filter(status=FoodListing.STATUS_COMPLETED).count()
    expired_count = listings.filter(status=FoodListing.STATUS_EXPIRED).count()

    recent_listings = listings[:5]
    pending_pickups = Claim.objects.filter(
        listing__donor=donor,
        status=Claim.STATUS_PENDING
    ).select_related('listing', 'recipient__user').order_by('pickup_deadline')[:5]

    context = {
        'donor': donor,
        'total_listings': total_listings,
        'available_count': available_count,
        'claimed_count': claimed_count,
        'completed_count': completed_count,
        'expired_count': expired_count,
        'recent_listings': recent_listings,
        'pending_pickups': pending_pickups,
    }
    return render(request, 'accounts/donor_dashboard.html', context)


@login_required
def recipient_dashboard_view(request):
    """
    Recipient Dashboard displaying available surplus food, active claims, and expiry alerts.
    """
    if not request.user.is_recipient:
        messages.error(request, "Access restricted: Recipient account required.")
        return redirect('accounts:donor_dashboard')

    recipient = getattr(request.user, 'recipient_profile', None)
    if not recipient:
        messages.error(request, "Recipient profile not found. Please complete your registration.")
        return redirect('accounts:profile')
    
    # Query visible food in recipient's city/area
    available_food = FoodListing.visible_to_recipients()
    nearby_food_count = available_food.filter(location__city__iexact=recipient.location.city).count()
    total_available_count = available_food.count()

    user_claims = recipient.claims.all().select_related('listing', 'listing__donor')
    pending_claims = user_claims.filter(status=Claim.STATUS_PENDING)
    completed_claims = user_claims.filter(status=Claim.STATUS_COMPLETED)

    recent_available = available_food[:6]

    context = {
        'recipient': recipient,
        'nearby_food_count': nearby_food_count,
        'total_available_count': total_available_count,
        'pending_claims': pending_claims,
        'pending_claims_count': pending_claims.count(),
        'completed_claims_count': completed_claims.count(),
        'recent_available': recent_available,
    }
    return render(request, 'accounts/recipient_dashboard.html', context)
