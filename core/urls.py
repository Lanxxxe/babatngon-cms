from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='registration'),
    path('login/', views.login, name='login'),
    path('', views.index, name='homepage'),
    path('about/', views.about, name='about'),
    path('features/', views.features, name='features'),
    path('contact/', views.contact, name='contact'),
]
