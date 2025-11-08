from core.models import User
from django.shortcuts import render
from django.core.paginator import Paginator
from django.shortcuts import redirect, get_object_or_404
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from resident.models import ForumPost, PostReaction, PostComment
import sweetify



# Community Forum Views
def community_forum(request):
    """Display the community forum with posts and filtering options."""
    if not request.session.get('resident_id'):
        sweetify.error(request, 'You must be logged in to access the community forum.', timer=3000)
        return redirect('homepage')
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    
    # Get filter parameters
    category = request.GET.get('category', '')
    search = request.GET.get('search', '')
    
    # Base query for active posts
    posts = ForumPost.objects.filter(is_active=True).select_related('author').prefetch_related('reactions', 'comments')
    
    # Apply filters
    if category:
        posts = posts.filter(category=category)
    
    if search:
        posts = posts.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search) |
            Q(author__first_name__icontains=search) |
            Q(author__last_name__icontains=search)
        )
    
    # Paginate posts
    paginator = Paginator(posts, 10)  # 10 posts per page
    page_number = request.GET.get('page')
    posts_page = paginator.get_page(page_number)
    
    # Get categories for filter dropdown
    categories = ForumPost.CATEGORY_CHOICES
    
    # Get stats for sidebar
    total_posts = ForumPost.objects.filter(is_active=True).count()
    my_posts = ForumPost.objects.filter(author=user, is_active=True).count()
    
    context = {
        'posts': posts_page,
        'categories': categories,
        'current_category': category,
        'search_query': search,
        'total_posts': total_posts,
        'my_posts': my_posts,
        'current_user': user,
    }
    
    return render(request, 'community_forum.html', context)


def create_post(request):
    """Create a new forum post."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    if request.method == 'POST':
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', 'discussions')
        image = request.FILES.get('image')
        
        if not all([title, content]):
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Title and content are required.'})
            sweetify.error(request, 'Title and content are required.', timer=3000)
            return redirect('community_forum')
        
        try:
            post = ForumPost.objects.create(
                author=user,
                title=title,
                content=content,
                category=category,
                image=image if image else None
            )
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Post created successfully!'})
            
            sweetify.success(request, 'Post created successfully!', timer=3000)
            return redirect('community_forum')
            
        except Exception as e:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'message': 'Error creating post. Please try again.'})
            
            sweetify.error(request, 'Error creating post. Please try again.', timer=3000)
            return redirect('community_forum')
    
    return redirect('community_forum')


def toggle_reaction(request, post_id):
    """Toggle reaction on a post (like, love, support)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    if request.method == 'POST':
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        post = get_object_or_404(ForumPost, id=post_id, is_active=True)
        reaction_type = request.POST.get('reaction_type', 'like')
        
        try:
            # Check if user already reacted to this post
            existing_reaction = PostReaction.objects.filter(user=user, post=post).first()
            
            if existing_reaction:
                if existing_reaction.reaction_type == reaction_type:
                    # Same reaction - remove it
                    existing_reaction.delete()
                    action = 'removed'
                else:
                    # Different reaction - update it
                    existing_reaction.reaction_type = reaction_type
                    existing_reaction.save()
                    action = 'updated'
            else:
                # No existing reaction - create new one
                PostReaction.objects.create(user=user, post=post, reaction_type=reaction_type)
                action = 'added'
            
            # Get updated counts
            like_count = post.get_like_count()
            love_count = post.get_love_count()
            support_count = post.get_support_count()
            total_reactions = post.get_total_reactions()
            
            return JsonResponse({
                'success': True,
                'action': action,
                'like_count': like_count,
                'love_count': love_count,
                'support_count': support_count,
                'total_reactions': total_reactions,
                'user_reaction': existing_reaction.reaction_type if existing_reaction and action != 'removed' else None
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error processing reaction.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def add_comment(request, post_id):
    """Add a comment to a post."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    if request.method == 'POST':
        user_id = request.session.get('resident_id')
        user = User.objects.filter(id=user_id).first()
        post = get_object_or_404(ForumPost, id=post_id, is_active=True)
        content = request.POST.get('content', '').strip()
        
        if not content:
            return JsonResponse({'success': False, 'message': 'Comment content is required.'})
        
        try:
            comment = PostComment.objects.create(
                post=post,
                author=user,
                content=content
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Comment added successfully!',
                'comment': {
                    'id': comment.id,
                    'content': comment.content,
                    'author_name': comment.author.get_full_name(),
                    'author_initials': comment.author.first_name[0].upper() + (comment.author.last_name[0].upper() if comment.author.last_name else ''),
                    'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
                },
                'total_comments': post.get_total_comments()
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error adding comment.'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method.'})


def delete_post(request, post_id):
    """Delete a forum post (only by author)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    post = get_object_or_404(ForumPost, id=post_id, author=user)
    
    try:
        post.is_active = False
        post.save()
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Post deleted successfully!'})
        
        sweetify.success(request, 'Post deleted successfully!', timer=3000)
        return redirect('community_forum')
        
    except Exception as e:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Error deleting post.'})
        
        sweetify.error(request, 'Error deleting post.', timer=3000)
        return redirect('community_forum')


def edit_post(request, post_id):
    """Edit a forum post (only by author)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    post = get_object_or_404(ForumPost, id=post_id, author=user, is_active=True)
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        category = request.POST.get('category', post.category)
        
        if not all([title, content]):
            return JsonResponse({'success': False, 'message': 'Title and content are required.'})
        
        try:
            post.title = title
            post.content = content
            post.category = category
            
            # Handle image update
            if request.FILES.get('image'):
                post.image = request.FILES['image']
            
            post.save()
            
            return JsonResponse({'success': True, 'message': 'Post updated successfully!'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error updating post.'})
    
    # Return post data for editing
    return JsonResponse({
        'success': True,
        'post': {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'category': post.category,
        }
    })


def get_post_comments(request, post_id):
    """Get comments for a specific post."""
    post = get_object_or_404(ForumPost, id=post_id, is_active=True)
    comments = post.comments.filter(is_active=True).select_related('author').order_by('created_at')
    
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'content': comment.content,
            'author_name': comment.author.get_full_name(),
            'author_initials': comment.author.first_name[0].upper() + (comment.author.last_name[0].upper() if comment.author.last_name else ''),
            'created_at': comment.created_at.strftime('%b %d, %Y at %I:%M %p'),
            'can_delete': request.session.get('resident_id') == comment.author.id,
        })
    
    return JsonResponse({
        'success': True,
        'comments': comments_data,
        'total_comments': len(comments_data)
    })


def delete_comment(request, comment_id):
    """Delete a comment (only by author)."""
    if not request.session.get('resident_id'):
        return JsonResponse({'success': False, 'message': 'You must be logged in.'})
    
    user_id = request.session.get('resident_id')
    user = User.objects.filter(id=user_id).first()
    comment = get_object_or_404(PostComment, id=comment_id, author=user)
    
    try:
        comment.is_active = False
        comment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Comment deleted successfully!',
            'total_comments': comment.post.get_total_comments()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': 'Error deleting comment.'})
