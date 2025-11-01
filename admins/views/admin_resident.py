from django.shortcuts import render, redirect
from django.db.models import Count
from core.models import User
import sweetify



def admin_resident(request):
    """
    Display all residents for admin management, with complaint count and stats for dashboard cards.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')

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
