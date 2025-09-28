from django.db import models
from core.models import User
from django.utils import timezone

# Create your models here.

class ForumPost(models.Model):
    CATEGORY_CHOICES = [
        ('announcements', 'Announcements'),
        ('discussions', 'General Discussions'),
        ('events', 'Community Events'),
        ('suggestions', 'Suggestions'),
        ('questions', 'Questions & Help'),
        ('safety', 'Safety & Security'),
        ('environment', 'Environment'),
        ('infrastructure', 'Infrastructure'),
        ('other', 'Other'),
    ]
    
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_posts')
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='discussions')
    image = models.ImageField(upload_to='forum_images/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        
    def __str__(self):
        return self.title
        
    def get_total_reactions(self):
        return self.reactions.count()
        
    def get_total_comments(self):
        return self.comments.count()
        
    def get_like_count(self):
        return self.reactions.filter(reaction_type='like').count()
        
    def get_love_count(self):
        return self.reactions.filter(reaction_type='love').count()
        
    def get_support_count(self):
        return self.reactions.filter(reaction_type='support').count()


class PostReaction(models.Model):
    REACTION_CHOICES = [
        ('like', '👍 Like'),
        ('love', '❤️ Love'),
        ('support', '🤝 Support'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'post')
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_reaction_type_display()} on {self.post.title}"


class PostComment(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['created_at']
        
    def __str__(self):
        return f"Comment by {self.author.get_full_name()} on {self.post.title}"


class CommentReaction(models.Model):
    REACTION_CHOICES = [
        ('like', '👍 Like'),
        ('love', '❤️ Love'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.ForeignKey(PostComment, on_delete=models.CASCADE, related_name='reactions')
    reaction_type = models.CharField(max_length=10, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ('user', 'comment')
        
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_reaction_type_display()} on comment"
