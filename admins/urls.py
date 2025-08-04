from django.urls import include, path
from .views import *

urlpatterns = [
    path('', admin_login, name='admin_login'),
    path('home/', admin_dashboard, name='admin_dashboard'),
    path('analytics/', admin_analytics, name='admin_analytics'),
    path('complaints/', admin_complaints, name='admin_complaints'),
    path('residents/', admin_resident, name='admin_residents'),
    path('notifications/', admin_notification, name='admin_notifications'),

    # Accounts Management
    path('accounts/', accounts, name='accounts'),
    path('accounts/add/', add_account, name='add_account'),
    path('accounts/change-password/', change_account_password, name='change_account_password'),
    path('accounts/delete/', delete_account, name='delete_account'),

    # Admin Logout
    path('logout/', admin_logout, name='admin_logout'),
]