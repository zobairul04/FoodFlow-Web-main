from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipient', 'notification_type', 'title', 'is_read', 'sent_at')
    list_filter = ('is_read', 'notification_type', 'sent_at')
    search_fields = ('title', 'message', 'recipient__user__username')
    ordering = ('-sent_at',)
