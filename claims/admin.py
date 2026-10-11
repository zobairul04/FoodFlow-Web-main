from django.contrib import admin
from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ('id', 'listing', 'recipient', 'claimed_quantity', 'pickup_code', 'status', 'claimed_at', 'pickup_deadline')
    list_filter = ('status', 'claimed_at')
    search_fields = ('pickup_code', 'recipient__user__username', 'listing__food_name', 'listing__donor__organization_name')
    readonly_fields = ('claimed_at', 'pickup_code')
    ordering = ('-claimed_at',)
