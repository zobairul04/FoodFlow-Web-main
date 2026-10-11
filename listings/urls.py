from django.urls import path
from . import views

app_name = 'listings'

urlpatterns = [
    # Donor Listing Routes
    path('donor/listings/', views.donor_listings_list_view, name='donor_listings'),
    path('donor/listings/create/', views.donor_listing_create_view, name='donor_listing_create'),
    path('donor/listings/<int:pk>/', views.donor_listing_detail_view, name='donor_listing_detail'),
    path('donor/listings/<int:pk>/edit/', views.donor_listing_edit_view, name='donor_listing_edit'),
    path('donor/listings/<int:pk>/delete/', views.donor_listing_delete_view, name='donor_listing_delete'),

    # Recipient Browse Routes
    path('recipient/food/', views.recipient_browse_view, name='browse_food'),
    path('recipient/food/<int:pk>/', views.recipient_food_detail_view, name='food_detail'),
]
