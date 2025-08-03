from django.shortcuts import render
from django.contrib.auth import logout


# Create your views here.

def register(request):

    return render(request, 'registration.html')

def login(request):

    return render(request, 'login.html')


def index(request):
    return render(request, 'index.html')

def about(request):


    return render(request, 'about.html')
def features(request):


    return render(request, 'features.html')
def contact(request):


    return render(request, 'contact.html')







