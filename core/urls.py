from django.urls import include, path
from .views import *

urlpatterns = [
    path('', index, name="homepage"),
    path('login/', login, name="login"),
    path('registration/', register, name="registration"),
    path('contact/', contact, name="contact"),
    path('about/', about, name="about"),
    path('features/', features, name="features"),
]
