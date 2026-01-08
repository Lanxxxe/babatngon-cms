from django.shortcuts import render
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import redirect
from django.db import IntegrityError
from django.db.models import Avg, Count
from .models import User, Feedback
from admins.models import Complaint, AssistanceRequest
import sweetify
from admins.user_activity_utils import log_activity, log_login_attempt



def register(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        middle_name = request.POST.get('middle_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        suffix = request.POST.get('suffix', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        barangay = request.POST.get('barangay', '').strip()
        address = request.POST.get('address', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        
        # Basic validation
        if not all([first_name, last_name, username, email, phone, address, password1, password2]):
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
        
        if User.objects.filter(username=username).exists():
            sweetify.error(request, 'Username already taken.', timer=3000)
            return render(request, 'registration.html')
        
        # Save user securely
        try:
            hashed_password = make_password(password1)
            user = User.objects.create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                suffix=suffix,
                username=username,
                email=email,
                phone=phone,
                barangay=barangay,
                address=address,
                password=hashed_password
            )
            
            # Log successful registration
            log_activity(
                user=user,
                activity_type='user_created',
                activity_category='authentication',
                description=f'New resident account registered: {user.get_full_name()} ({email})',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'username': username, 'email': email, 'barangay': barangay}
            )
            
            sweetify.success(request, 'Account created successfully! Please wait for the admin to verify your account.', timer=3000)
            return redirect('login')
        except IntegrityError as e:
            # Log failed registration
            temp_user = type('obj', (object,), {
                'id': None,
                'email': email,
                'get_full_name': lambda: f"{first_name} {last_name}"
            })
            log_activity(
                user=temp_user,
                activity_type='user_created',
                activity_category='authentication',
                description=f'Failed registration attempt for email {email}: Account already exists',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'username': username, 'email': email}
            )
            sweetify.error(request, 'An account with this email already exists.', timer=3000)
            return render(request, 'registration.html')
        except Exception as e:
            # Log failed registration
            temp_user = type('obj', (object,), {
                'id': None,
                'email': email,
                'get_full_name': lambda: f"{first_name} {last_name}"
            })
            log_activity(
                user=temp_user,
                activity_type='user_created',
                activity_category='authentication',
                description=f'Failed registration attempt for email {email}',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'username': username, 'email': email}
            )
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
                user = User.objects.filter(username=username_or_email).first()  # fallback, adjust if you have username field
        except Exception:
            user = None
        
        # Check if user not found
        if not user:
            # Log failed login - user not found
            temp_user = type('obj', (object,), {
                'id': None,
                'email': username_or_email,
                'get_full_name': lambda: username_or_email
            })
            log_login_attempt(
                user=temp_user,
                is_successful=False,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                error_message=f'User not found: {username_or_email}'
            )
            sweetify.error(request, 'Invalid credentials. Please try again.', timer=3000)
            return render(request, 'login.html')
        
        if user and not user.is_verified:
            # Log failed login - account not verified
            log_login_attempt(
                user=user,
                is_successful=False,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                error_message='Account not verified'
            )
            sweetify.warning(request, 'Account not verified. Please wait for admin approval.', timer=3000, persistent="Close")
            
            return render(request, 'login.html')

        if user and check_password(password, user.password):
            # Set session securely
            request.session['resident_id'] = user.id
            request.session['role'] = 'resident'
            request.session['first_name'] = user.first_name
            request.session['middle_name'] = user.middle_name
            request.session['last_name'] = user.last_name
            request.session['full_name'] = f"{user.first_name} {user.middle_name} {user.last_name}".strip()
            request.session['address'] = user.address
            request.session['phone'] = user.phone
            request.session['email'] = user.email
            
            # Log successful login
            log_login_attempt(
                user=user,
                is_successful=True,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
            
            sweetify.toast(request, f'Welcome, {user.first_name}!', timer=3000)

            return redirect('resident_dashboard')
        else:
            # Log failed login - incorrect password
            if user:
                log_login_attempt(
                    user=user,
                    is_successful=False,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    error_message='Incorrect password'
                )
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


def feedback(request):
    """
    Display feedback form and handle feedback submissions.
    No authentication required - anyone can submit feedback.
    """
    if request.method == 'POST':
        # Get form data
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        category = request.POST.get('category', '').strip()
        rating = request.POST.get('rating', '')
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        # Validate required fields
        if not all([name, email, category, rating, subject, message]):
            sweetify.error(request, 'All fields are required. Please fill out the complete form.', timer=3000)
            return render(request, 'feedback.html', {
                'name': name,
                'email': email,
                'category': category,
                'subject': subject,
                'message': message
            })
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            sweetify.error(request, 'Please enter a valid email address.', timer=3000)
            return render(request, 'feedback.html', {
                'name': name,
                'email': email,
                'category': category,
                'subject': subject,
                'message': message
            })
        
        # Validate rating
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (ValueError, TypeError):
            sweetify.error(request, 'Please select a valid rating.', timer=3000)
            return render(request, 'feedback.html', {
                'name': name,
                'email': email,
                'category': category,
                'subject': subject,
                'message': message
            })
        
        try:
            # Check if user is logged in (optional)
            user = None
            if 'user_id' in request.session:
                try:
                    user = User.objects.get(id=request.session['user_id'])
                except User.DoesNotExist:
                    pass
            
            # Create feedback
            feedback_obj = Feedback.objects.create(
                name=name,
                email=email,
                category=category,
                rating=rating,
                subject=subject,
                message=message,
                user=user
            )
            
            # Log activity if user is logged in
            if user:
                log_activity(
                    user=user,
                    activity_type='other',
                    activity_category='communication',
                    description=f'{user.get_full_name()} submitted feedback: {subject}',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT'),
                    metadata={
                        'feedback_id': feedback_obj.id,
                        'category': category,
                        'rating': rating
                    }
                )
            
            sweetify.success(
                request, 
                'Thank you for your feedback! We appreciate your input and will review it carefully.',
                icon='success',
                timer=4000
            )
            return redirect('feedback')
            
        except Exception as e:
            sweetify.error(request, f'An error occurred while submitting your feedback. Please try again.', timer=3000)
            return render(request, 'feedback.html', {
                'name': name,
                'email': email,
                'category': category,
                'subject': subject,
                'message': message
            })
    
    # GET request - display form with statistics
    # Calculate statistics for display
    total_feedback = Feedback.objects.count()
    average_rating = Feedback.objects.aggregate(Avg('rating'))['rating__avg'] or 0
    active_users = User.objects.filter(is_verified=True, is_archived=False).count()
    resolved_cases = Complaint.objects.filter(status='resolved').count() + \
                    AssistanceRequest.objects.filter(status='resolved').count()
    
    context = {
        'total_feedback': total_feedback,
        'average_rating': average_rating,
        'active_users': active_users,
        'resolved_cases': resolved_cases,
    }
    
    return render(request, 'feedback.html', context)


def help_center(request):
    return render(request, 'help_center.html')


def privacy_policy(request):
    return render(request, 'privacy_policy.html')


def terms_of_service(request):
    return render(request, 'terms_of_service.html')


def faq(request):
    return render(request, 'faq.html')





