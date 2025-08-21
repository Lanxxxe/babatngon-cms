from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect
from django.db import IntegrityError
from .models import User
import sweetify



def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        address = request.POST.get('address', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Basic validation
        if not all([first_name, last_name, email, phone, address, password1, password2]):
            sweetify.error(request, 'All required fields must be filled.', timer=3000)
            return render(request, 'registration.html')
        if password1 != password2:
            sweetify.error(request, 'Passwords do not match.', timer=3000)
            return render(request, 'registration.html')
        if len(password1) < 8:
            sweetify.error(request, 'Password must be at least 8 characters.', timer=3000)
            return render(request, 'registration.html')
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            sweetify.error(request, 'Email already registered.', timer=3000)
            return render(request, 'registration.html')
        # Save user securely
        try:
            hashed_password = make_password(password1)
            user = User.objects.create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=email,
                phone=phone,
                address=address,
                password=hashed_password
            )
            sweetify.success(request, 'Account created successfully! Please wait for the admin to verify your account.', timer=3000)
            return redirect('login')
        except IntegrityError:
            sweetify.error(request, 'An account with this email already exists.', timer=3000)
            return render(request, 'registration.html')
        except Exception as e:
            sweetify.error(request, f'Error: {str(e)}', timer=3000)
            return render(request, 'registration.html')
    return render(request, 'registration.html')

def login(request):
    if request.method == 'POST':
        username_or_email = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = None

        # Use ORM filtering to prevent SQL injection
        try:
            user = User.objects.filter(email=username_or_email).first()
            if not user:
                user = User.objects.filter(first_name=username_or_email).first()  # fallback, adjust if you have username field
        except Exception:
            user = None

        if user and check_password(password, user.password):
            # Set session securely
            request.session['id'] = user.id
            request.session['role'] = 'resident'
            request.session['first_name'] = user.first_name
            request.session['middle_name'] = user.middle_name
            request.session['last_name'] = user.last_name
            request.session['full_name'] = f"{user.first_name} {user.middle_name} {user.last_name}".strip()
            request.session['address'] = user.address
            request.session['phone'] = user.phone
            request.session['email'] = user.email
            sweetify.toast(request, f'Welcome, {user.first_name}!', timer=3000)

            return redirect('resident_dashboard')
        else:
            sweetify.error(request, 'Invalid credentials. Please try again.', timer=3000)
            return render(request, 'login.html')

    return render(request, 'login.html')


def index(request):
    return render(request, 'index.html')

def about(request):


    return render(request, 'about.html')
def features(request):


    return render(request, 'features.html')
def contact(request):


    return render(request, 'contact.html')









