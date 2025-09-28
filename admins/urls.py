from django.urls import include, path
from .views import *

urlpatterns = [
    path('', admin_login, name='admin_login'),
    path('home/', admin_dashboard, name='admin_dashboard'),
    path('analytics/', admin_analytics, name='admin_analytics'),
    path('complaints/', admin_complaints, name='admin_complaints'),
    path('complaints/<int:complaint_id>/details/', complaint_details, name='complaint_details'),
    path('complaints/assign/', assign_complaint, name='assign_complaint'),
    path('complaints/update-status/', update_complaint_status, name='update_complaint_status'),
    path('assistance/', admin_assistance, name='admin_assistance'),
    path('assistance/<int:assistance_id>/details/', assistance_details, name='assistance_details'),
    path('assistance/assign/', assign_assistance, name='assign_assistance'),
    path('assistance/update-status/', update_assistance_status, name='update_assistance_status'),
    path('residents/', admin_resident, name='admin_residents'),
    path('notifications/', admin_notification, name='admin_notifications'),
    path('notifications/mark-read/', mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/archive/', archive_notification, name='archive_notification'),
    path('notifications/<int:notification_id>/details/', notification_details, name='notification_details'),

    # Accounts Management
    path('accounts/', accounts, name='accounts'),
    path('accounts/add/', add_account, name='add_account'),
    path('accounts/change-password/', change_account_password, name='change_account_password'),
    path('accounts/delete/', delete_account, name='delete_account'),

    # Admin Logout
    path('logout/', admin_logout, name='admin_logout'),
]