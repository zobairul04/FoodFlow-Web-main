from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from .models import Notification


def unread_notification_context(request):
    """
    Context processor to inject unread notification count into all templates for the navbar.
    """
    if request.user.is_authenticated and request.user.is_recipient and hasattr(request.user, 'recipient_profile'):
        count = Notification.objects.filter(recipient=request.user.recipient_profile, is_read=False).count()
        return {'unread_notifications_count': count}
    return {'unread_notifications_count': 0}


@login_required
def notification_list_view(request):
    """
    Displays all in-app notifications for the logged-in recipient, ordered latest first.
    Marks unread notifications as read upon visit.
    """
    if not request.user.is_recipient:
        messages.info(request, "In-app notifications are currently active for recipient accounts.")
        return redirect('home')

    recipient = request.user.recipient_profile
    notifications = Notification.objects.filter(recipient=recipient).select_related('listing')

    # Automatically mark unread notifications as read when viewing list
    unread_qs = notifications.filter(is_read=False)
    if unread_qs.exists():
        unread_qs.update(is_read=True)

    context = {
        'notifications': notifications,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def unread_notification_count_json(request):
    """
    Authenticated JSON endpoint for polling unread notification count.
    Strictly isolated to the current user's recipient profile.
    """
    if not request.user.is_recipient or not hasattr(request.user, 'recipient_profile'):
        return JsonResponse({'unread_count': 0})

    count = Notification.objects.filter(
        recipient=request.user.recipient_profile,
        is_read=False
    ).count()

    return JsonResponse({'unread_count': count})
