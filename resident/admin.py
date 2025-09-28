from django.contrib import admin
from .models import ForumPost, PostReaction, PostComment, CommentReaction

# Register your models here.

@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'created_at', 'is_pinned', 'is_active']
    list_filter = ['category', 'is_pinned', 'is_active', 'created_at']
    search_fields = ['title', 'content', 'author__first_name', 'author__last_name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author')


@admin.register(PostReaction)
class PostReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'reaction_type', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'post__title']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'post')


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'post', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['content', 'author__first_name', 'author__last_name', 'post__title']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('author', 'post')


@admin.register(CommentReaction)
class CommentReactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'comment', 'reaction_type', 'created_at']
    list_filter = ['reaction_type', 'created_at']
    search_fields = ['user__first_name', 'user__last_name']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'comment__author', 'comment__post')
