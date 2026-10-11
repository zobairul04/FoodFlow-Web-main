from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('address', 'area', 'city', 'postal_code')
    list_filter = ('city', 'area')
    search_fields = ('address', 'area', 'city', 'postal_code')
    ordering = ('city', 'area')
