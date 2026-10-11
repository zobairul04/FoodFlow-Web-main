from django.urls import path
from . import views

app_name = 'locations'

urlpatterns = [
    path('json/', views.location_list_json, name='location_json'),
]
