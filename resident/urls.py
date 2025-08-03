from django.urls import include, path
from .views import *

urlpatterns = [
    path('home/', resident_dashboard, name='resident_dashboard'),
    path('logout/', resident_logout, name='resident_logout'),
    path('file-complaint/', file_complaint, name='file_complaint'),
    path('file-assistance/', file_assistance, name='file_assistance'),
]
