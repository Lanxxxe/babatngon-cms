from django.urls import path
from staffs.views import (
    staff_auth,
    staff_dashboard,
    staff_assistance, 
    staff_complaints,
    staff_notifications,
    staff_profile
)

urlpatterns = [
    path('', staff_auth.staff_login, name='staff_login'),

    path('dashboard/', staff_dashboard.staff_dashboard, name='staff_dashboard'),
    path('complaints/', staff_complaints.staff_complaints, name='staff_complaints'),
    path('assistance/', staff_assistance.staff_assistance, name='staff_assistance'),

    # Case detail views
    path('cases/<str:case_type>/<int:case_id>/', staff_complaints.staff_view_case, name='staff_view_case'),

    # Case action views
    path('cases/<str:case_type>/<int:case_id>/update-status/', staff_complaints.staff_update_case_status, name='staff_update_case_status'),
    path('cases/<str:case_type>/<int:case_id>/add-notes/', staff_complaints.staff_add_notes, name='staff_add_notes'),
    
    # Notification views
    path('notifications/', staff_notifications.staff_notifications, name='staff_notifications'),
    path('notifications/<int:notification_id>/details/', staff_notifications.staff_notification_details, name='staff_notification_details'),
    path('notifications/mark-read/', staff_notifications.staff_mark_notification_read, name='staff_mark_notification_read'),
    path('notifications/mark-all-read/', staff_notifications.staff_mark_all_notifications_read, name='staff_mark_all_notifications_read'),
    path('notifications/archive/', staff_notifications.staff_archive_notification, name='staff_archive_notification'),

    # Profile management views
    path('profile/', staff_profile.staff_profile, name='staff_profile'),
    path('profile/update/', staff_profile.staff_update_profile, name='staff_update_profile'),
    path('profile/change-password/', staff_profile.staff_change_password, name='staff_change_password'),
    path('profile/update-username/', staff_profile.staff_update_username, name='staff_update_username'),

    # Logout
    path('logout/', staff_auth.staff_logout, name='staff_logout'),
]