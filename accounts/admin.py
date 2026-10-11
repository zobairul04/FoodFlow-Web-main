from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Donor, Recipient


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'phone', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('FoodFlow Role & Info', {'fields': ('role', 'phone')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('FoodFlow Role & Info', {'fields': ('role', 'phone')}),
    )


@admin.action(description="Mark selected Donors as Verified")
def verify_donors(modeladmin, request, queryset):
    queryset.update(is_verified=True)


@admin.action(description="Mark selected Donors as Unverified")
def unverify_donors(modeladmin, request, queryset):
    queryset.update(is_verified=False)


@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization_name', 'donor_type', 'location', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'donor_type', 'location__city')
    search_fields = ('user__username', 'organization_name', 'user__email', 'location__area', 'location__city')
    actions = [verify_donors, unverify_donors]
    ordering = ('-created_at',)


@admin.action(description="Mark selected Recipients as Verified (Eligible to Claim)")
def verify_recipients(modeladmin, request, queryset):
    queryset.update(is_verified=True)


@admin.action(description="Mark selected Recipients as Unverified")
def unverify_recipients(modeladmin, request, queryset):
    queryset.update(is_verified=False)


@admin.register(Recipient)
class RecipientAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipient_type', 'location', 'is_verified', 'created_at')
    list_filter = ('is_verified', 'recipient_type', 'location__city')
    search_fields = ('user__username', 'user__email', 'location__area', 'location__city')
    actions = [verify_recipients, unverify_recipients]
    ordering = ('-created_at',)
