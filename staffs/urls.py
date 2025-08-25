from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('complaints/', views.staff_complaints, name='staff_complaints'),
    path('assistance/', views.staff_assistance, name='staff_assistance'),
]