from django.urls import include, path
from .views import *

urlpatterns = [
    # Resident Dashboard
    path('home/', resident_dashboard, name='resident_dashboard'),
    path('file-complaint/', file_complaint, name='file_complaint'),
    path('file-assistance/', file_assistance, name='file_assistance'),
    
    # Complaints
    path('my-complaints/', my_complaints, name='my_complaints'),
    path('update-complaint/<int:pk>/', update_complaint, name='update_complaint'),
    path('delete-complaint/<int:pk>/', delete_complaint, name='delete_complaint'),
    
    # Assistance Requests
    path('my-assistance/', my_assistance, name='my_assistance'),
    path('update-assistance/<int:pk>/', update_assistance, name='update_assistance'),
    path('delete-assistance/<int:pk>/', delete_assistance, name='delete_assistance'),
    
    # Logout
    path('logout/', resident_logout, name='resident_logout'),

    # Profile
    path('profile/', profile, name='profile'),
]
