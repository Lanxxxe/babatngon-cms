from django.urls import include, path
from .views import *

urlpatterns = [
    path('home/', resident_dashboard, name='resident_dashboard')
]
