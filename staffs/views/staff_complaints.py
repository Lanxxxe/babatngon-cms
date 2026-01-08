from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from admins.models import Complaint, AssistanceRequest
from core.models import Admin
from staffs.notification_views import create_notes_notification, create_status_update_notification
from core.sms_util import send_sms, format_resolved_case
import sweetify
from admins.user_activity_utils import log_activity, log_case_activity

# Staff Complaints
def staff_complaints(request):
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get all complaints assigned to current staff member
        complaints = Complaint.objects.filter(
            assigned_to=current_staff,
        ).select_related('user').order_by('-created_at')
        
        # Apply filters if provided
        status_filter = request.GET.get('status')
        priority_filter = request.GET.get('priority')
        
        if status_filter:
            complaints = complaints.filter(status=status_filter)
        else:
            complaints = complaints.filter(status__in=['pending', 'in_progress', 'assigned'])

        if priority_filter:
            complaints = complaints.filter(priority=priority_filter)
        

        # Log activity
        filter_info = []
        if status_filter:
            filter_info.append(f"status: {status_filter}")
        if priority_filter:
            filter_info.append(f"priority: {priority_filter}")
        filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
        
        log_activity(
            user=current_staff,
            activity_type='complaint_viewed',
            activity_category='case_management',
            description=f'{current_staff.get_full_name()} accessed assigned complaints{filter_desc}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'total_complaints': complaints.count(), 'filters': {'status': status_filter, 'priority': priority_filter}}
        )

        context = {
            'complaints': complaints,
            'current_staff': current_staff,
            'status_filter': status_filter,
            'priority_filter': priority_filter,
        }
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    
    return render(request, 'staff_complaints.html', context)


# Cases Details and Actions
def staff_view_case(request, case_type, case_id):
    """
    Display detailed view of a specific complaint or assistance request.
    """
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        
        # Get the case based on type
        if case_type == 'complaint':
            case = get_object_or_404(
                Complaint.objects.select_related('user', 'assigned_to', 'assigned_by').prefetch_related('attachments'),
                id=case_id,
                assigned_to=current_staff
            )
        elif case_type == 'assistance':
            case = get_object_or_404(
                AssistanceRequest.objects.select_related('user', 'assigned_to').prefetch_related('attachments'),
                id=case_id,
                assigned_to=current_staff
            )
        else:
            sweetify.error(request, 'Invalid case type.', persistent=True, timer=3000)

        # Log activity
        activity_type = 'complaint_viewed' if case_type == 'complaint' else 'assistance_viewed'
        log_case_activity(
            user=current_staff,
            case=case,
            activity_type=activity_type,
            description=f'{current_staff.get_full_name()} viewed {case_type} #{case.id} details: {case.title}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'status': case.status, 'priority': getattr(case, 'priority', None) or getattr(case, 'urgency', None)}
        )

        context = {
            'case': case,
            'case_type': case_type,
            'current_staff': current_staff,
        }
        
        return render(request, 'staff_view_cases.html', context)
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        sweetify.error(request, f'Error loading case details: {str(e)}', persistent=True, timer=3000)
    
    if case_type == 'complaint':
        return redirect('staff_complaints')
    elif case_type == 'assistance':
        return redirect('staff_assistance')


def staff_update_case_status(request, case_type, case_id):
    """
    Update the status of a complaint or assistance request.
    """
    if request.method == 'POST':
        staff_id = request.session.get('staff_id')
        if not staff_id:
            sweetify.error(request, 'You must be logged in to perform this action.', icon='error', timer=3000, persistent="Okay ")
            return redirect('staff_login')
        
        try:
            current_staff = Admin.objects.get(id=staff_id)
            new_status = request.POST.get('status', '').strip()
            remarks = request.POST.get('remarks', '').strip()
            
            if not new_status:
                sweetify.error(request, 'Status is required.')
                return redirect('staff_view_case', case_type=case_type, case_id=case_id)
            
            # Get the case and store old status for comparison
            if case_type == 'complaint':
                case = get_object_or_404(Complaint, id=case_id, assigned_to=current_staff)
                valid_statuses = ['pending', 'in_progress', 'resolved', 'closed']
                
                if new_status not in valid_statuses:
                    sweetify.error(request, 'Invalid status for complaint.')
                    return redirect('staff_view_case', case_type=case_type, case_id=case_id)
                
                old_status = case.status
                case.status = new_status
                
                # Set resolved_at timestamp if status is resolved
                if new_status == 'resolved':
                    case.resolved_at = timezone.now()

                    message = format_resolved_case(case.id, case.title)
                    if case.user.phone:
                        send_sms(case.user.phone, message)
                
            elif case_type == 'assistance':
                case = get_object_or_404(AssistanceRequest, id=case_id, assigned_to=current_staff)
                valid_statuses = ['pending', 'approved', 'in_progress', 'completed', 'rejected']
                
                if new_status not in valid_statuses:
                    sweetify.error(request, 'Invalid status for assistance request.')
                    return redirect('staff_view_case', case_type=case_type, case_id=case_id)
                
                old_status = case.status
                case.status = new_status
                
                # Set completed_at timestamp if status is completed
                if new_status == 'completed':
                    case.completed_at = timezone.now()

                    message = format_resolved_case(case.id, case.title)
                    if case.user.phone:
                        send_sms(case.user.phone, message)
                        
            timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            new_remark = f"[{timestamp}] {current_staff.first_name}: {remarks}"
            if case.admin_remarks:
                case.admin_remarks += f"\n\n{new_remark}"
            else:
                case.admin_remarks = new_remark
            case.save()
            
            # Create notification for the complainant if status changed
            if old_status != new_status:
                create_status_update_notification(case, case_type, old_status, new_status, new_remark, current_staff)
            
            # Log activity
            activity_type_map = {
                'resolved': 'complaint_resolved' if case_type == 'complaint' else 'assistance_resolved',
                'closed': 'complaint_closed' if case_type == 'complaint' else 'assistance_closed',
                'completed': 'assistance_resolved'
            }
            activity_type = activity_type_map.get(new_status, f"{case_type}_status_changed")
            
            log_case_activity(
                user=current_staff,
                case=case,
                activity_type=activity_type,
                description=f'{current_staff.get_full_name()} updated {case_type} #{case.id} - {case.title} status from {old_status} to {new_status}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                metadata={'old_status': old_status, 'new_status': new_status, 'remarks_added': bool(remarks)}
            )
            
            sweetify.success(request, f'{case_type.title()} status updated to {new_status.replace("_", " ").title()} successfully.', icon='success', timer=3000, persistent="Okay")
            return redirect('staff_view_case', case_type=case_type, case_id=case_id)
            
        except Admin.DoesNotExist:
            return redirect('staff_login')
        except Exception as e:
            # Log failed attempt
            if staff_id:
                try:
                    staff = Admin.objects.get(id=staff_id)
                    log_activity(
                        user=staff,
                        activity_type=f"{case_type}_status_changed",
                        activity_category='case_management',
                        description=f'{staff.get_full_name()} failed to update {case_type} status',
                        is_successful=False,
                        error_message=str(e),
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT')
                    )
                except:
                    pass
            sweetify.error(request, f'Error updating status: {str(e)}')
            return redirect('staff_view_case', case_type=case_type, case_id=case_id)
    
    else:
        sweetify.error(request, 'Invalid request method.', icon='error', timer=3000, persistent="Okay ")
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)


def staff_add_notes(request, case_type, case_id):
    """
    Add resolution/completion notes to a complaint or assistance request.
    """
    if request.method != 'POST':
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
    
    staff_id = request.session.get('staff_id')
    
    if not staff_id:
        return redirect('staff_login')
    
    try:
        current_staff = Admin.objects.get(id=staff_id)
        notes = request.POST.get('notes', '').strip()
        
        if not notes:
            sweetify.error(request, 'Notes cannot be empty.')
            return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
        # Get the case and add notes
        if case_type == 'complaint':
            case = get_object_or_404(Complaint, id=case_id, assigned_to=current_staff)
            case.resolution_notes = notes
            note_type = 'Resolution notes'
        elif case_type == 'assistance':
            case = get_object_or_404(AssistanceRequest, id=case_id, assigned_to=current_staff)
            case.completion_notes = notes
            note_type = 'Completion notes'
        else:
            sweetify.error(request, 'Invalid case type.')
            return redirect('staff_dashboard')
        
        case.save()
        
        # Create notification for the complainant about resolution/completion notes
        create_notes_notification(case, case_type, notes, current_staff)
        
        # Log activity
        activity_type = f"{case_type}_updated"
        log_case_activity(
            user=current_staff,
            case=case,
            activity_type=activity_type,
            description=f'{current_staff.get_full_name()} added {note_type.lower()} to {case_type} #{case.id} - {case.title}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'note_type': note_type, 'notes_length': len(notes)}
        )
        
        sweetify.success(request, f'{note_type} updated successfully.')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)
        
    except Admin.DoesNotExist:
        return redirect('staff_login')
    except Exception as e:
        # Log failed attempt
        if staff_id:
            try:
                staff = Admin.objects.get(id=staff_id)
                log_activity(
                    user=staff,
                    activity_type=f"{case_type}_updated",
                    activity_category='case_management',
                    description=f'{staff.get_full_name()} failed to add notes to {case_type}',
                    is_successful=False,
                    error_message=str(e),
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT')
                )
            except:
                pass
        sweetify.error(request, f'Error updating notes: {str(e)}')
        return redirect('staff_view_case', case_type=case_type, case_id=case_id)














