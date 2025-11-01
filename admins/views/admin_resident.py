from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
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

        barangay = request.GET.get('barangay', '')
        status = request.GET.get('status', '')
        query = request.GET.get('query', '')
        per_page = request.GET.get('per_page', '10')
        residents_page = []
        try:
            per_page = int(per_page)
            if per_page not in [10, 25, 50, 100]:
                per_page = 10
        except (ValueError, TypeError):
            per_page = 10

        # Annotate each resident with their complaint count
        residents = User.objects.annotate(complaint_count=Count('complaint'), assistance_count=Count('assistancerequest'))

        if query:
            residents = residents.filter(
                Q(first_name__icontains=query) |
                Q(middle_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(suffix__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        if barangay:
            residents = residents.filter(barangay__iexact=barangay)

        if status == 'verified':
            residents = residents.filter(is_verified=True)
        elif status == 'unverified':
            residents = residents.filter(is_verified=False)
        elif status == 'archived':
            residents = residents.filter(is_archived=True)
        else:
            residents = residents.filter(is_archived=False)

        residents = residents.order_by('-created_at')

        # Card metrics
        total_residents = residents.count()
        active_users = residents.filter(is_verified=True).count()
        pending_verification = residents.filter(is_verified=False).count()

        now = timezone.now()
        new_this_month = residents.filter(created_at__gte=now - timedelta(days=30)).count()

        paginator = Paginator(residents, per_page)
        page_number = request.GET.get('page', 1)

        try: 
            residents_page = paginator.get_page(page_number)
        except (EmptyPage, PageNotAnInteger):
            residents_page = paginator.get_page(1)

        start_index = (residents_page.number - 1) * per_page + 1
        end_index = min(start_index + per_page - 1, paginator.count)

    except Exception as e:
        print(f"Error fetching residents: {e}")
        sweetify.error(request, 'An error occurred while fetching residents.', icon='error', timer=3000, persistent='Okay')
        residents = []
        total_residents = 0
        active_users = 0
        pending_verification = 0
        new_this_month = 0
        start_index = 0
        end_index = 0
        paginator = None

    context = {
        'residents': residents_page,
        'total_residents': total_residents,
        'active_users': active_users,
        'pending_verification': pending_verification,
        'new_this_month': new_this_month,
        'paginator': paginator,
        'page_obj': residents_page,
        'start_index': start_index,
        'end_index': end_index,

        'current_query': query,
        'current_barangay': barangay,
        'current_status': status,
        'current_per_page': per_page,
    }

    return render(request, 'admin_resident.html', context)


def approve_resident(request, resident_id):
    """
    Approve a resident's verification.
    """
    user = request.session.get('admin_role', '')

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')

    try:
        resident = User.objects.get(id=resident_id)
        if resident.is_verified:
            sweetify.info(request, 'Resident account is already verified.', icon='info', timer=3000, persistent='Okay')
            return redirect('admin_residents')
        resident.is_verified = True
        resident.save()
        sweetify.success(request, 'Resident account approved successfully.', icon='success', timer=3000, persistent='Okay')

    except User.DoesNotExist:
        sweetify.error(request, 'Resident account not found.', icon='error', timer=3000, persistent='Okay')

    except Exception:
        sweetify.error(request, 'An error occurred while approving the resident.', icon='error', timer=3000, persistent='Okay')

    return redirect('admin_residents')


def archive_resident(request, resident_id):
    """
    Archive a resident's account.
    """
    user = request.session.get('admin_role', '')
    message = ''

    if user != 'admin' and user != 'staff' or not user:
        sweetify.error(request, 'Access denied.', icon='error', timer=3000, persistent='Okay')
        return redirect('homepage')

    try:
        resident = User.objects.get(id=resident_id)
        
        if resident.is_archived:
            resident.is_archived = False
            message = 'Resident account unarchived successfully.'
        else:
            resident.is_archived = True
            message = 'Resident account archived successfully.'

        resident.updated_at = timezone.now()
        resident.save()
        sweetify.success(request, message, icon='success', timer=3000, persistent='Okay')

    except User.DoesNotExist:
        sweetify.error(request, 'Resident account not found.', icon='error', timer=3000, persistent='Okay')
    
    except Exception:
        sweetify.error(request, 'An error occurred while archiving the resident.', icon='error', timer=3000, persistent='Okay')

    return redirect('admin_residents')





