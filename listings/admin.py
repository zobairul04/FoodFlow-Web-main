from django.contrib import admin
from .models import FoodListing, ExpiryTracker, FoodSafetyCheck


@admin.action(description="Block selected Food Listings")
def block_listings(modeladmin, request, queryset):
    queryset.update(status=FoodListing.STATUS_BLOCKED)


@admin.action(description="Mark selected Food Listings as Available")
def make_available_listings(modeladmin, request, queryset):
    queryset.update(status=FoodListing.STATUS_AVAILABLE)


@admin.register(FoodListing)
class FoodListingAdmin(admin.ModelAdmin):
    list_display = ('food_name', 'donor', 'quantity', 'unit', 'status', 'expires_at', 'created_at')
    list_filter = ('status', 'location__city', 'created_at')
    search_fields = ('food_name', 'description', 'donor__organization_name', 'donor__user__username', 'location__area')
    actions = [block_listings, make_available_listings]
    ordering = ('expires_at',)


@admin.register(ExpiryTracker)
class ExpiryTrackerAdmin(admin.ModelAdmin):
    list_display = ('listing', 'urgency_level', 'expires_at', 'alert_sent', 'last_checked_at')
    list_filter = ('urgency_level', 'alert_sent')
    search_fields = ('listing__food_name',)


@admin.register(FoodSafetyCheck)
class FoodSafetyCheckAdmin(admin.ModelAdmin):
    list_display = ('listing', 'risk_level', 'is_safe', 'checked_at')
    list_filter = ('is_safe', 'risk_level')
    search_fields = ('listing__food_name',)
