from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Role Dashboards
    path('donor/dashboard/', views.donor_dashboard_view, name='donor_dashboard'),
    path('recipient/dashboard/', views.recipient_dashboard_view, name='recipient_dashboard'),
]
