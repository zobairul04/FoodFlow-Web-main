from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from locations.models import Location
from claims.models import Claim
from claims.forms import ClaimForm
from notifications.services import NotificationService
from .models import FoodListing, ExpiryTracker, FoodSafetyCheck
from .forms import FoodListingForm
from .services import ExpiryService, SafetyService


# ==========================================
# DONOR VIEWS
# ==========================================

@login_required
def donor_listings_list_view(request):
    """
    Displays all listings created by the logged-in donor with status filtering.
    """
    if not request.user.is_donor:
        messages.error(request, "Access restricted to food donors.")
        return redirect('accounts:recipient_dashboard')

    donor = request.user.donor_profile
    status_filter = request.GET.get('status', '')
    
    listings = FoodListing.objects.filter(donor=donor).select_related(
        'location', 'expiry_tracker', 'safety_check'
    ).prefetch_related('claims')

    if status_filter:
        listings = listings.filter(status=status_filter)

    context = {
        'listings': listings,
        'status_filter': status_filter,
    }
    return render(request, 'listings/my_listings.html', context)


@login_required
def donor_listing_create_view(request):
    """
    Handles surplus food listing creation, location lookup, safety screening,
    expiry tracker initialization, and recipient matching alerts.
    """
    if not request.user.is_donor:
        messages.error(request, "Access restricted to food donors.")
        return redirect('accounts:recipient_dashboard')

    donor = getattr(request.user, 'donor_profile', None)

    if donor is None:
        messages.error(
            request,
            "Donor profile not found. Please complete your profile."
        )
        return redirect('accounts:profile')

    if not donor.is_verified:
        messages.error(
            request,
            "Your donor account is pending administrator verification. "
            "You can post food donations once an administrator verifies your account."
        )
        return redirect('accounts:donor_dashboard')

    if request.method == 'POST':
        form = FoodListingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # 1. Location reuse / creation
                    location, _ = Location.objects.get_or_create(
                        address=form.cleaned_data['address'].strip(),
                        area=form.cleaned_data['area'].strip(),
                        city=form.cleaned_data['city'].strip(),
                        postal_code=form.cleaned_data.get('postal_code', '').strip() or None,
                    )

                    # 2. Save Listing
                    listing = form.save(commit=False)
                    listing.donor = donor
                    listing.location = location
                    listing.status = FoodListing.STATUS_AVAILABLE
                    listing.save()

                    # 3. Automated Safety Check
                    safety_check = SafetyService.check_food_safety(listing)

                    # 4. Expiry Tracker Initialization
                    ExpiryService.update_expiry_tracker(listing)

                    if not safety_check.is_safe:
                        messages.warning(
                            request,
                            f"Listing created, but automatically BLOCKED due to safety screening ({safety_check.get_risk_level_display()})."
                        )
                    else:
                        # 5. Notify matching verified recipients in same area/city
                        NotificationService.notify_new_listing(listing)
                        messages.success(request, f"Food listing '{listing.food_name}' published successfully!")

                    return redirect('listings:donor_listing_detail', pk=listing.pk)

            except Exception as e:
                messages.error(request, f"Error saving food listing: {e}")
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        # Pre-fill with donor's default location
        initial_data = {}
        if donor.location:
            initial_data = {
                'address': donor.location.address,
                'area': donor.location.area,
                'city': donor.location.city,
                'postal_code': donor.location.postal_code or '',
            }
        form = FoodListingForm(initial=initial_data)

    return render(request, 'listings/listing_form.html', {'form': form, 'is_edit': False})


@login_required
def donor_listing_detail_view(request, pk):
    """
    Detailed view for Donors to inspect their listing, safety report, and active claims.
    """
    if not request.user.is_donor:
        messages.error(request, "Access restricted to food donors.")
        return redirect('home')

    listing = get_object_or_404(
        FoodListing.objects.select_related('donor__user', 'location', 'expiry_tracker', 'safety_check'),
        pk=pk
    )

    # Verify donor ownership
    if listing.donor.user != request.user and not request.user.is_staff:
        messages.error(request, "Unauthorized: You do not own this listing.")
        return redirect('listings:donor_listings')

    claims = listing.claims.all().select_related('recipient__user').order_by('-claimed_at')

    context = {
        'listing': listing,
        'claims': claims,
    }
    return render(request, 'listings/listing_detail_donor.html', context)


@login_required
@transaction.atomic
def donor_listing_edit_view(request, pk):
    """
    Allows donors to edit their own active food listings.
    """
    if not request.user.is_donor:
        messages.error(request, "Access restricted to food donors.")
        return redirect('home')

    listing = get_object_or_404(
        FoodListing.objects.select_for_update(),
        pk=pk
    )

    # Check donor ownership
    if listing.donor.user != request.user and not request.user.is_staff:
        messages.error(request, "Unauthorized: You cannot edit someone else's listing.")
        return redirect('listings:donor_listings')

    if listing.status in [FoodListing.STATUS_COMPLETED, FoodListing.STATUS_EXPIRED]:
        messages.error(request, f"Cannot edit a listing that is {listing.get_status_display().lower()}.")
        return redirect('listings:donor_listing_detail', pk=listing.pk)

    if request.method == 'POST':
        form = FoodListingForm(request.POST, instance=listing)
        if form.is_valid():
            with transaction.atomic():
                location, _ = Location.objects.get_or_create(
                    address=form.cleaned_data['address'].strip(),
                    area=form.cleaned_data['area'].strip(),
                    city=form.cleaned_data['city'].strip(),
                    postal_code=form.cleaned_data.get('postal_code', '').strip() or None,
                )
                listing = form.save(commit=False)
                listing.location = location

                if listing.status in [
                    FoodListing.STATUS_AVAILABLE,
                    FoodListing.STATUS_CLAIMED,
                ]:
                    if listing.quantity_available > Decimal("0.00"):
                        listing.status = FoodListing.STATUS_AVAILABLE
                    elif listing.claims.filter(status="pending").exists():
                        listing.status = FoodListing.STATUS_CLAIMED
                    else:
                        listing.status = FoodListing.STATUS_COMPLETED

                listing.save()

                # Re-run safety and expiry checks
                SafetyService.check_food_safety(listing)
                ExpiryService.update_expiry_tracker(listing)

                messages.success(request, f"Food listing '{listing.food_name}' updated successfully.")
                return redirect('listings:donor_listing_detail', pk=listing.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        initial_data = {
            'address': listing.location.address,
            'area': listing.location.area,
            'city': listing.location.city,
            'postal_code': listing.location.postal_code or '',
            'expires_at': listing.expires_at.strftime('%Y-%m-%dT%H:%M')
        }
        form = FoodListingForm(instance=listing, initial=initial_data)

    return render(request, 'listings/listing_form.html', {'form': form, 'is_edit': True, 'listing': listing})


@login_required
@require_POST
def donor_listing_delete_view(request, pk):
    """
    Allows donors to delete their own food listing if no pending claims exist.
    """
    if not request.user.is_donor:
        messages.error(request, "Access restricted.")
        return redirect('home')

    listing = get_object_or_404(FoodListing, pk=pk)

    if listing.donor.user != request.user and not request.user.is_staff:
        messages.error(request, "Unauthorized: You cannot delete this listing.")
        return redirect('listings:donor_listings')

    # Ensure no pending claims prevent safe deletion
    if listing.claims.filter(status=Claim.STATUS_PENDING).exists():
        messages.error(request, "Cannot delete listing with active pending claims. Complete or wait for claims to conclude.")
        return redirect('listings:donor_listing_detail', pk=listing.pk)

    food_title = listing.food_name
    listing.delete()
    messages.success(request, f"Listing '{food_title}' has been deleted.")
    return redirect('listings:donor_listings')


# ==========================================
# RECIPIENT VIEWS
# ==========================================

def recipient_browse_view(request):
    """
    Recipient Food Browse page:
    Layer 1 Query-time filtering ensures ONLY available, unexpired, and safe food is returned.
    Supports search by keyword, area, city, and urgency level.
    """
    listings = FoodListing.visible_to_recipients()

    # Search query
    q = request.GET.get('q', '').strip()
    if q:
        listings = listings.filter(
            Q(food_name__icontains=q) |
            Q(description__icontains=q) |
            Q(location__area__icontains=q) |
            Q(location__city__icontains=q)
        )

    # City filter
    city = request.GET.get('city', '').strip()
    if city:
        listings = listings.filter(location__city__iexact=city)

    # Area filter
    area = request.GET.get('area', '').strip()
    if area:
        listings = listings.filter(location__area__iexact=area)

    # Urgency filter
    urgency = request.GET.get('urgency', '').strip()
    if urgency:
        listings = listings.filter(expiry_tracker__urgency_level=urgency)

    # Distinct locations for filter dropdowns
    available_cities = Location.objects.filter(listings__in=FoodListing.visible_to_recipients()).values_list('city', flat=True).distinct()
    available_areas = Location.objects.filter(listings__in=FoodListing.visible_to_recipients()).values_list('area', flat=True).distinct()

    context = {
        'listings': listings,
        'q': q,
        'selected_city': city,
        'selected_area': area,
        'selected_urgency': urgency,
        'available_cities': available_cities,
        'available_areas': available_areas,
    }
    return render(request, 'listings/browse.html', context)


def recipient_food_detail_view(request, pk):
    """
    Detailed food view for recipients showing live expiry timer, quantity available,
    safety badge, and embedded ClaimForm for verified recipients.
    """
    listing = get_object_or_404(
        FoodListing.objects.select_related('donor__user', 'location', 'expiry_tracker', 'safety_check'),
        pk=pk
    )

    available_qty = listing.quantity_available
    is_claimable = (
        listing.status == FoodListing.STATUS_AVAILABLE
        and not listing.is_expired
        and (hasattr(listing, 'safety_check') and listing.safety_check.is_safe)
        and available_qty > Decimal('0.00')
    )

    is_recipient = request.user.is_authenticated and request.user.is_recipient
    is_verified_recipient = is_recipient and hasattr(request.user, 'recipient_profile') and request.user.recipient_profile.is_verified

    claim_form = None
    if is_recipient and is_claimable:
        claim_form = ClaimForm(max_available=available_qty, unit=listing.unit)

    context = {
        'listing': listing,
        'available_qty': available_qty,
        'is_claimable': is_claimable,
        'is_recipient': is_recipient,
        'is_verified_recipient': is_verified_recipient,
        'claim_form': claim_form,
    }
    return render(request, 'listings/food_detail_recipient.html', context)
