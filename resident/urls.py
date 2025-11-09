from django.urls import include, path
from resident.views import (
    resident_dashboard,
    resident_assistance,
    resident_complaints,
    resident_notifications,
    resident_profile,
    resident_chatbot,
)

urlpatterns = [
    # Resident Dashboard
    path('home/', resident_dashboard.resident_dashboard, name='resident_dashboard'),
    path('file-complaint/', resident_complaints.file_complaint, name='file_complaint'),
    path('file-assistance/', resident_assistance.file_assistance, name='file_assistance'),

    # Complaints
    path('my-complaints/', resident_complaints.my_complaints, name='my_complaints'),
    path('complaint-details/<int:pk>/', resident_complaints.complaint_details, name='resident_complaint_details'),
    path('update-complaint/<int:pk>/', resident_complaints.update_complaint, name='update_complaint'),
    path('delete-complaint/<int:pk>/', resident_complaints.delete_complaint, name='delete_complaint'),
    path('follow-up-complaint/<int:complaint_id>/', resident_complaints.follow_up_complaint, name='follow_up_complaint'),

    # Assistance Requests
    path('my-assistance/', resident_assistance.my_assistance, name='my_assistance'),
    path('assistance-details/<int:pk>/', resident_assistance.assistance_detail, name='resident_assistance_detail'),
    path('update-assistance/<int:pk>/', resident_assistance.update_assistance, name='update_assistance'),
    path('delete-assistance/<int:pk>/', resident_assistance.delete_assistance, name='delete_assistance'),
    path('follow-up-assistance/<int:assistance_id>/', resident_assistance.follow_up_assistance, name='follow_up_assistance'),

    # Community Forum
    # path('community-forum/', views.community_forum, name='community_forum'),
    # path('create-post/', views.create_post, name='create_post'),
    # path('post/<int:post_id>/react/', views.toggle_reaction, name='toggle_reaction'),
    # path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    # path('post/<int:post_id>/comments/', views.get_post_comments, name='get_post_comments'),
    # path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    # path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    # path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Notifications
    path('notifications/', resident_notifications.notifications, name='notifications'),
    path('notifications/details/<int:notification_id>/', resident_notifications.resident_notification_details, name='resident_notification_details'),
    path('notifications/mark-as-read/<int:notification_id>/', resident_notifications.resident_mark_notification_read, name='mark_notification_as_read'),
    path('notifications/archive/<int:notification_id>/', resident_notifications.resident_archive_notification, name='mark_notification_as_archived'),
    # Logout
    path('logout/', resident_dashboard.resident_logout, name='resident_logout'),

    # Profile
    path('profile/', resident_profile.profile, name='profile'),
    path('change-password/', resident_profile.resident_change_password, name='resident_change_password'),
    
    # Chatbot
    path('chatbot/response/', resident_chatbot.chatbot_response, name='chatbot_response'),
]
