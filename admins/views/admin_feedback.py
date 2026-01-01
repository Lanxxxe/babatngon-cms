from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count
from django.utils import timezone
from core.models import Feedback, Admin
from admins.user_activity_utils import log_activity
import sweetify


def admin_feedback(request):
    """
    Display all user feedbacks with filtering and search capabilities.
    """
    admin_id = request.session.get('admin_id')
    
    if not admin_id:
        return redirect('admin_login')
    
    try:
        current_admin = Admin.objects.get(id=admin_id)
        
        # Base query
        feedbacks = Feedback.objects.all().select_related('user').order_by('-created_at')
        
        # Get filter parameters
        category_filter = request.GET.get('category', '')
        rating_filter = request.GET.get('rating', '')
        status_filter = request.GET.get('status', '')
        search_query = request.GET.get('search', '').strip()
        
        # Apply filters
        if category_filter:
            feedbacks = feedbacks.filter(category=category_filter)
        
        if rating_filter:
            try:
                rating = int(rating_filter)
                feedbacks = feedbacks.filter(rating=rating)
            except ValueError:
                pass
        
        if status_filter:
            if status_filter == 'read':
                feedbacks = feedbacks.filter(is_read=True)
            elif status_filter == 'unread':
                feedbacks = feedbacks.filter(is_read=False)
            elif status_filter == 'responded':
                feedbacks = feedbacks.filter(is_responded=True)
            elif status_filter == 'pending':
                feedbacks = feedbacks.filter(is_responded=False)
        
        # Search functionality
        if search_query:
            feedbacks = feedbacks.filter(
                Q(name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(subject__icontains=search_query) |
                Q(message__icontains=search_query)
            )
        
        # Calculate statistics
        total_feedbacks = feedbacks.count()
        unread_feedbacks = feedbacks.filter(is_read=False).count()
        pending_response = feedbacks.filter(is_responded=False).count()
        average_rating = feedbacks.aggregate(Avg('rating'))['rating__avg'] or 0
        
        # Get rating distribution
        rating_distribution = feedbacks.values('rating').annotate(
            count=Count('id')
        ).order_by('rating')
        
        # Get category distribution
        category_distribution = feedbacks.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Pagination
        paginator = Paginator(feedbacks, 15)  # Show 15 feedbacks per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Log activity
        filter_info = []
        if category_filter:
            filter_info.append(f"category: {category_filter}")
        if rating_filter:
            filter_info.append(f"rating: {rating_filter}")
        if status_filter:
            filter_info.append(f"status: {status_filter}")
        if search_query:
            filter_info.append(f"search: {search_query}")
        filter_desc = f" with filters ({', '.join(filter_info)})" if filter_info else ""
        
        log_activity(
            user=current_admin,
            activity_type='report_generated',
            activity_category='reporting',
            description=f'{current_admin.get_full_name()} viewed user feedbacks{filter_desc}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={
                'total_feedbacks': total_feedbacks,
                'filters_applied': len(filter_info)
            }
        )
        
        context = {
            'current_admin': current_admin,
            'feedbacks': page_obj,
            'page_obj': page_obj,
            
            # Statistics
            'total_feedbacks': total_feedbacks,
            'unread_feedbacks': unread_feedbacks,
            'pending_response': pending_response,
            'average_rating': average_rating,
            'rating_distribution': rating_distribution,
            'category_distribution': category_distribution,
            
            # Current filter values
            'category_filter': category_filter,
            'rating_filter': rating_filter,
            'status_filter': status_filter,
            'search_query': search_query,
        }
        
        return render(request, 'admin_feedback.html', context)
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error loading feedbacks: {str(e)}')
        return redirect('admin_dashboard')


def mark_feedback_read(request, feedback_id):
    """
    Mark a feedback as read.
    """
    admin_id = request.session.get('admin_id')
    
    if not admin_id:
        return redirect('admin_login')
    
    try:
        current_admin = Admin.objects.get(id=admin_id)
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        feedback.is_read = True
        feedback.save()
        
        # Log activity
        log_activity(
            user=current_admin,
            activity_type='other',
            activity_category='communication',
            description=f'{current_admin.get_full_name()} marked feedback #{feedback_id} as read',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'feedback_id': feedback_id}
        )
        
        sweetify.success(request, 'Feedback marked as read.', timer=2000)
        return redirect('admin_feedback')
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error: {str(e)}')
        return redirect('admin_feedback')


def respond_feedback(request, feedback_id):
    """
    Add admin response to a feedback.
    """
    if request.method != 'POST':
        return redirect('admin_feedback')
    
    admin_id = request.session.get('admin_id')
    
    if not admin_id:
        return redirect('admin_login')
    
    try:
        current_admin = Admin.objects.get(id=admin_id)
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        response = request.POST.get('response', '').strip()
        
        if not response:
            sweetify.error(request, 'Response cannot be empty.')
            return redirect('admin_feedback')
        
        # Update feedback with response
        feedback.admin_response = response
        feedback.is_responded = True
        feedback.is_read = True
        feedback.responded_at = timezone.now()
        feedback.save()
        
        # Log activity
        log_activity(
            user=current_admin,
            activity_type='other',
            activity_category='communication',
            description=f'{current_admin.get_full_name()} responded to feedback #{feedback_id} from {feedback.name}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'feedback_id': feedback_id, 'response_length': len(response)}
        )
        
        sweetify.success(request, 'Response submitted successfully.', icon='success', timer=3000)
        return redirect('admin_feedback')
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error: {str(e)}')
        return redirect('admin_feedback')


def delete_feedback(request, feedback_id):
    """
    Delete a feedback.
    """
    admin_id = request.session.get('admin_id')
    
    if not admin_id:
        return redirect('admin_login')
    
    try:
        current_admin = Admin.objects.get(id=admin_id)
        feedback = get_object_or_404(Feedback, id=feedback_id)
        
        feedback_info = f"{feedback.name} - {feedback.subject}"
        feedback.delete()
        
        # Log activity
        log_activity(
            user=current_admin,
            activity_type='other',
            activity_category='administration',
            description=f'{current_admin.get_full_name()} deleted feedback: {feedback_info}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            metadata={'feedback_id': feedback_id}
        )
        
        sweetify.success(request, 'Feedback deleted successfully.', timer=2000)
        return redirect('admin_feedback')
        
    except Admin.DoesNotExist:
        return redirect('admin_login')
    except Exception as e:
        sweetify.error(request, f'Error: {str(e)}')
        return redirect('admin_feedback')
