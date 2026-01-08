from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='registration'),
    path('login/', views.login, name='login'),
    path('', views.index, name='homepage'),
    path('about/', views.about, name='about'),
    path('features/', views.features, name='features'),
    path('contact/', views.contact, name='contact'),
    path('feedback/', views.feedback, name='feedback'),
    path('help-center/', views.help_center, name='help_center'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('faq/', views.faq, name='faq'),
]
