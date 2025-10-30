from django.urls import path
from . import views

urlpatterns = [
    path('', views.staff_login, name='staff_login'),

    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('complaints/', views.staff_complaints, name='staff_complaints'),
    path('assistance/', views.staff_assistance, name='staff_assistance'),
    
    # Case detail views
    path('cases/<str:case_type>/<int:case_id>/', views.staff_view_case, name='staff_view_case'),
    
    # Case action views
    path('cases/<str:case_type>/<int:case_id>/update-status/', views.staff_update_case_status, name='staff_update_case_status'),
    path('cases/<str:case_type>/<int:case_id>/add-remarks/', views.staff_add_remarks, name='staff_add_remarks'),
    path('cases/<str:case_type>/<int:case_id>/add-notes/', views.staff_add_notes, name='staff_add_notes'),
    
    # Notification views
    path('notifications/', views.staff_notifications, name='staff_notifications'),
    path('notifications/<int:notification_id>/details/', views.staff_notification_details, name='staff_notification_details'),
    path('notifications/mark-read/', views.staff_mark_notification_read, name='staff_mark_notification_read'),
    path('notifications/mark-all-read/', views.staff_mark_all_notifications_read, name='staff_mark_all_notifications_read'),
    path('notifications/archive/', views.staff_archive_notification, name='staff_archive_notification'),
    
    # Profile management views
    path('profile/', views.staff_profile, name='staff_profile'),
    path('profile/update/', views.staff_update_profile, name='staff_update_profile'),
    path('profile/change-password/', views.staff_change_password, name='staff_change_password'),
    path('profile/update-username/', views.staff_update_username, name='staff_update_username'),

    # Logout
    path('logout/', views.staff_logout, name='staff_logout'),
]