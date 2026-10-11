from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    # Claims List & Public Tracking
    path('claims/', views.claims_list_view, name='my_claims'),
    path('claims/<int:pk>/', views.claim_detail_view, name='claim_detail'),
    path('claims/<int:pk>/cancel/', views.claim_cancel_view, name='claim_cancel'),
    path('claims/create/<int:listing_id>/', views.claim_create_view, name='claim_create'),

    # Donor Pickup Verification
    path('donor/pickups/verify/', views.donor_verify_pickup_view, name='verify_pickup'),
]
