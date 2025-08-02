from django.urls import include, path
from .views import *

urlpatterns = [
    path('', index, name="homepage"),
    path('login/', login, name="login"),
    path('registration/', register, name="registration"),
]
