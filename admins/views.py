from core.models import Admin
from django.contrib.auth.hashers import make_password
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.contrib import messages
from django.shortcuts import redirect
from django.shortcuts import render
from .models import Complaint
from core.models import Admin, User
from django.contrib.auth.hashers import check_password
import sweetify

def admin_login(request):
    """
    Admin/staff login page with authentication and security best practices.
    """
 
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        try:
            admin = Admin.objects.filter(username=username).first()
            if not admin:
                sweetify.toast(request, 'Invalid username or password.', timer=3000, icon='error')
                return redirect('admin_login')
            if not check_password(password, admin.password):
                sweetify.toast(request, 'Invalid username or password.', timer=3000, icon='error')
                return redirect('admin_login')
            # Set session for admin
            request.session['admin_id'] = admin.id
            request.session['admin_username'] = admin.username
            request.session['admin_role'] = admin.role
            sweetify.toast(request, f'Welcome, {admin.full_name}!', timer=2000)
            return redirect('admin_dashboard')
        except Exception as e:
            sweetify.toast(request, 'An error occurred during login. Please try again.', timer=3000, icon='error')
            return redirect('admin_login')
    return render(request, 'admin_login.html')

# Create your views here.
def admin_dashboard(request):

    # Get all complaints
    complaints = Complaint.objects.select_related('user').all().order_by('-created_at')

    # Metrics
    total_complaints = complaints.count()
    pending_complaints = complaints.filter(status='pending').count()
    in_progress_complaints = complaints.filter(status='in_progress').count()
    resolved_complaints = complaints.filter(status='resolved').count()

    # For recent complaints table (limit to 10 for dashboard)
    recent_complaints = complaints[:10]

    context = {
        'complaints': complaints,
        'recent_complaints': recent_complaints,
        'total_complaints': total_complaints,
        'pending_complaints': pending_complaints,
        'in_progress_complaints': in_progress_complaints,
        'resolved_complaints': resolved_complaints,
    }
    return render(request, 'admin_dashboard.html', context)

def admin_analytics(request):


    return render(request, 'admin_analytics.html')


def admin_complaints(request):

    complaints = Complaint.objects.all().order_by('-created_at')

    data = {
        'complaints': complaints
    }

    return render(request, 'admin_complaints.html', data)


def admin_resident(request):
    """
    Display all residents for admin management, with complaint count and stats for dashboard cards.
    """
    try:
        # Annotate each resident with their complaint count
        residents = User.objects.annotate(complaint_count=Count('complaint')).order_by('-created_at')

        # Card metrics
        total_residents = residents.count()
        active_users = residents.filter(is_verified=True).count()
        pending_verification = residents.filter(is_verified=False).count()
        # New this month: created in the last 30 days
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        new_this_month = residents.filter(created_at__gte=now - timedelta(days=30)).count()
    except Exception:
        residents = []
        total_residents = 0
        active_users = 0
        pending_verification = 0
        new_this_month = 0

    context = {
        'residents': residents,
        'total_residents': total_residents,
        'active_users': active_users,
        'pending_verification': pending_verification,
        'new_this_month': new_this_month,
    }
    return render(request, 'admin_resident.html', context)


def admin_notification(request):


    return render(request, 'admin_notification.html')


# Accounts management view
def accounts(request):
    """
    List all staff and admin accounts for management.
    """
    admins = Admin.objects.all().order_by('-role', 'username')
    admin_count = Admin.objects.filter(role='admin').count()
    context = {
        'admins': admins,
        'admin_count': admin_count,
    }
    return render(request, 'accounts.html', context)

# Register new staff/admin
@require_POST
def add_account(request):
    try:
        username = request.POST.get('username', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'staff').strip()
        department = request.POST.get('department', '').strip()
        password = request.POST.get('password', '').strip()
        if not all([username, full_name, email, password, role]):
            sweetify.error(request, 'All fields except department are required.', timer=3000)
            return redirect('accounts')
        if Admin.objects.filter(username=username).exists():
            sweetify.error(request, 'Username already exists.', timer=3000)
            return redirect('accounts')
        if Admin.objects.filter(email=email).exists():
            sweetify.error(request, 'Email already exists.', timer=3000)
            return redirect('accounts')
        Admin.objects.create(
            username=username,
            full_name=full_name,
            email=email,
            role=role,
            department=department,
            password=make_password(password)
        )
        sweetify.toast(request, 'Account registered successfully!', timer=2000)
    except Exception:
        sweetify.error(request, 'Failed to register account.', timer=3000)
    return redirect('accounts')

# Change password for staff/admin
@require_POST
def change_account_password(request):
    try:
        admin_id = request.POST.get('admin_id')
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        admin = Admin.objects.filter(id=admin_id).first()
        if not admin:
            sweetify.error(request, 'Account not found.', timer=3000)
            return redirect('accounts')
        if not new_password or new_password != confirm_password:
            sweetify.error(request, 'Passwords do not match.', timer=3000)
            return redirect('accounts')
        if len(new_password) < 6:
            sweetify.error(request, 'Password must be at least 6 characters.', timer=3000)
            return redirect('accounts')
        admin.password = make_password(new_password)
        admin.save()
        sweetify.toast(request, 'Password updated successfully.', timer=2000)
    except Exception:
        sweetify.error(request, 'Failed to update password.', timer=3000)
    return redirect('accounts')

# Delete staff/admin account
@require_POST
def delete_account(request):
    try:
        admin_id = request.POST.get('admin_id')
        admin = Admin.objects.filter(id=admin_id).first()
        if not admin:
            sweetify.error(request, 'Account not found.', timer=3000)
            return redirect('accounts')
        if admin.role == 'admin':
            admin_count = Admin.objects.filter(role='admin').count()
            if admin_count <= 1:
                sweetify.error(request, 'Cannot delete the only remaining admin.', timer=3000)
                return redirect('accounts')
        admin.delete()
        sweetify.toast(request, 'Account deleted successfully.', timer=2000)
    except Exception:
        sweetify.error(request, 'Failed to delete account.', timer=3000)
    return redirect('accounts')


def admin_logout(request):
    """
    Admin logout view.
    """
    request.session.flush()  # Clear all session data
    sweetify.toast(request, 'You have been logged out successfully.', timer=2000)
    return redirect('admin_login')