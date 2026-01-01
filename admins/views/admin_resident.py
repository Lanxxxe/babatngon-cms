from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from core.models import User, Admin
import sweetify
from admins.user_activity_utils import log_activity



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

        # Annotate each resident with their complaint count (using distinct to avoid inflated counts)
        residents = User.objects.annotate(
            complaint_count=Count('complaint', distinct=True), 
            assistance_count=Count('assistancerequest', distinct=True)
        )

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

        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            filter_info = []
            if query:
                filter_info.append(f"search: '{query}'")
            if barangay:
                filter_info.append(f"barangay: {barangay}")
            if status:
                filter_info.append(f"status: {status}")
            
            filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
            
            log_activity(
                user=admin_user,
                activity_type='user_viewed',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} accessed residents management page{filter_desc}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={
                    'total_residents': total_residents,
                    'active_users': active_users,
                    'pending_verification': pending_verification,
                    'new_this_month': new_this_month,
                    'filters': {'query': query, 'barangay': barangay, 'status': status}
                }
            )

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
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_activated',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} approved/verified resident account: {resident.get_full_name()} ({resident.email})',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'resident_id': resident.id, 'resident_email': resident.email, 'resident_name': resident.get_full_name()}
            )
        
        sweetify.success(request, 'Resident account approved successfully.', icon='success', timer=3000, persistent='Okay')

    except User.DoesNotExist:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_activated',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to approve resident: resident not found',
                is_successful=False,
                error_message=f'Resident with ID {resident_id} not found',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Resident account not found.', icon='error', timer=3000, persistent='Okay')

    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_activated',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to approve resident account',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
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
            action = 'unarchived'
            activity_type = 'user_activated'
        else:
            resident.is_archived = True
            message = 'Resident account archived successfully.'
            action = 'archived'
            activity_type = 'user_deactivated'

        resident.updated_at = timezone.now()
        resident.save()
        
        # Log activity
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type=activity_type,
                activity_category='administration',
                description=f'{admin_user.get_full_name()} {action} resident account: {resident.get_full_name()} ({resident.email})',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={
                    'resident_id': resident.id,
                    'resident_email': resident.email,
                    'resident_name': resident.get_full_name(),
                    'action': action,
                    'is_archived': resident.is_archived
                }
            )
        
        sweetify.success(request, message, icon='success', timer=3000, persistent='Okay')

    except User.DoesNotExist:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_deactivated',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to archive resident: resident not found',
                is_successful=False,
                error_message=f'Resident with ID {resident_id} not found',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'Resident account not found.', icon='error', timer=3000, persistent='Okay')
    
    except Exception as e:
        # Log failed attempt
        admin_user = Admin.objects.filter(id=request.session.get('admin_id')).first()
        if admin_user:
            log_activity(
                user=admin_user,
                activity_type='user_deactivated',
                activity_category='administration',
                description=f'{admin_user.get_full_name()} failed to archive resident account',
                is_successful=False,
                error_message=str(e),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT')
            )
        sweetify.error(request, 'An error occurred while archiving the resident.', icon='error', timer=3000, persistent='Okay')

    return redirect('admin_residents')





