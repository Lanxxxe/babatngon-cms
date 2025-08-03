from django.urls import include, path
from .views import *

urlpatterns = [
    path('home/', admin_dashboard, name='admin_dashboard'),
    path('analytics/', admin_analytics, name='admin_analytics'),
    path('complaints/', admin_complaints, name='admin_complaints'),
    path('residents/', admin_resident, name='admin_residents'),
    path('notifications/', admin_notification, name='admin_notifications'),
]