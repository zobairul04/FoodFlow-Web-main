from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='notification_list'),
    path('unread-count/', views.unread_notification_count_json, name='unread_count_json'),
]
