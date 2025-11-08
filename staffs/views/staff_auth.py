from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password
from core.models import Admin
import sweetify


# Staff Login
def staff_login(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        try:
            staff_member = Admin.objects.get(username=username)
            
            if check_password(password, staff_member.password):
                # Set session variables
                request.session['staff_id'] = staff_member.id
                request.session['staff_username'] = staff_member.username
                request.session['staff_fullname'] = staff_member.get_full_name()
                request.session['role'] = staff_member.role
                request.session['department'] = staff_member.department
                request.session['position'] = staff_member.position
                request.session['first_name'] = staff_member.first_name
                request.session['last_name'] = staff_member.last_name

                sweetify.success(request, 'Login successful!', icon='success', timer=1500, persistent="Okay")
                return redirect('staff_dashboard')
            else:
                sweetify.error(request, 'Invalid username or password.', icon='error', timer=1500, persistent="Okay")
                return redirect('staff_login')
        except Admin.DoesNotExist:
            sweetify.error(request, 'Invalid username or password.', icon='error', timer=1500, persistent="Okay")

    return render(request, 'staff_login.html')


# Staff Logout
def staff_logout(request):

    request.session.flush()
    sweetify.success(request, 'Logged out successfully.', icon='success', timer=1500, persistent="Okay")
    return redirect('staff_login')










