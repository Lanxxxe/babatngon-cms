from django.urls import include, path
from . import views

urlpatterns = [
    # Resident Dashboard
    path('home/', views.resident_dashboard, name='resident_dashboard'),
    path('file-complaint/', views.file_complaint, name='file_complaint'),
    path('file-assistance/', views.file_assistance, name='file_assistance'),

    # Complaints
    path('my-complaints/', views.my_complaints, name='my_complaints'),
    path('update-complaint/<int:pk>/', views.update_complaint, name='update_complaint'),
    path('delete-complaint/<int:pk>/', views.delete_complaint, name='delete_complaint'),
    path('follow-up-complaint/<int:complaint_id>/', views.follow_up_complaint, name='follow_up_complaint'),

    # Assistance Requests
    path('my-assistance/', views.my_assistance, name='my_assistance'),
    path('update-assistance/<int:pk>/', views.update_assistance, name='update_assistance'),
    path('delete-assistance/<int:pk>/', views.delete_assistance, name='delete_assistance'),
    path('follow-up-assistance/<int:assistance_id>/', views.follow_up_assistance, name='follow_up_assistance'),

    # Community Forum
    path('community-forum/', views.community_forum, name='community_forum'),
    path('create-post/', views.create_post, name='create_post'),
    path('post/<int:post_id>/react/', views.toggle_reaction, name='toggle_reaction'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('post/<int:post_id>/comments/', views.get_post_comments, name='get_post_comments'),
    path('post/<int:post_id>/delete/', views.delete_post, name='delete_post'),
    path('post/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),

    # Logout
    path('logout/', views.resident_logout, name='resident_logout'),

    # Profile
    path('profile/', views.profile, name='profile'),
]
