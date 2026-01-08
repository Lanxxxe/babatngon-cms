from django.urls import include, path
from .views import (
    admin_helpers,
    admin_profile,
    admin_dashboard,
    admin_analytics,
    admin_complaints,
    admin_assistance,
    admin_resident,
    admin_notifications,
    admin_accounts,
    admin_user_activity,
    admin_feedback,
    admin_sms_logs,
    )

urlpatterns = [
    path('', admin_helpers.admin_login, name='admin_login'),
    
    # Dashboard
    path('home/', admin_dashboard.admin_dashboard, name='admin_dashboard'),
    
    # Analytics
    path('analytics/', admin_analytics.admin_analytics, name='admin_analytics'),
    
    # Complaints
    path('complaints/', admin_complaints.admin_complaints, name='admin_complaints'),
    path('complaints/<int:complaint_id>/details/', admin_complaints.complaint_details, name='complaint_details'),
    path('complaints/assign/', admin_complaints.assign_complaint, name='assign_complaint'),
    path('complaints/update-status/', admin_complaints.update_complaint_status, name='update_complaint_status'),
    
    # Assistance
    path('assistance/', admin_assistance.admin_assistance, name='admin_assistance'),
    path('assistance/<int:assistance_id>/details/', admin_assistance.assistance_details, name='assistance_details'),
    path('assistance/assign/', admin_assistance.assign_assistance, name='assign_assistance'),
    path('assistance/update-status/', admin_assistance.update_assistance_status, name='update_assistance_status'),
    
    # Residents
    path('residents/', admin_resident.admin_resident, name='admin_residents'),
    path('residents/approve/<int:resident_id>/', admin_resident.approve_resident, name='approve_resident'),
    path('residents/archive/<int:resident_id>/', admin_resident.archive_resident, name='archive_resident'),

    # Notifications
    path('notifications/', admin_notifications.admin_notification, name='admin_notifications'),
    path('notifications/mark-read/', admin_notifications.mark_notification_read, name='mark_notification_read'),
    path('notifications/mark-all-read/', admin_notifications.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('notifications/archive/', admin_notifications.archive_notification, name='archive_notification'),
    path('notifications/<int:notification_id>/details/', admin_notifications.notification_details, name='notification_details'),

    # Accounts Management
    path('accounts/', admin_accounts.accounts, name='accounts'),
    path('accounts/add/', admin_accounts.add_account, name='add_account'),
    path('accounts/change-password/', admin_accounts.change_account_password, name='change_account_password'),
    path('accounts/delete/', admin_accounts.delete_account, name='delete_account'),

    # User Activity Logs
    path('user-activity/', admin_user_activity.admin_user_activity, name='admin_user_activity'),
    path('user-activity/export/', admin_user_activity.export_user_activity, name='export_user_activity'),

    # User Feedbacks
    path('feedback/', admin_feedback.admin_feedback, name='admin_feedback'),
    path('feedback/<int:feedback_id>/read/', admin_feedback.mark_feedback_read, name='mark_feedback_read'),
    path('feedback/<int:feedback_id>/respond/', admin_feedback.respond_feedback, name='respond_feedback'),
    path('feedback/<int:feedback_id>/delete/', admin_feedback.delete_feedback, name='delete_feedback'),

    # SMS Logs
    path('sms-logs/', admin_sms_logs.admin_sms_logs, name='admin_sms_logs'),

    # Profile
    path('profile/', admin_profile.admin_profile, name='admin_profile'),

    # Admin Logout
    path('logout/', admin_helpers.admin_logout, name='admin_logout'),
]