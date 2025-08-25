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

    # Assistance Requests
    path('my-assistance/', views.my_assistance, name='my_assistance'),
    path('update-assistance/<int:pk>/', views.update_assistance, name='update_assistance'),
    path('delete-assistance/<int:pk>/', views.delete_assistance, name='delete_assistance'),

    # Logout
    path('logout/', views.resident_logout, name='resident_logout'),

    # Profile
    path('profile/', views.profile, name='profile'),
]
