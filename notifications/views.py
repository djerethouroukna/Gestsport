from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Notification, NotificationType
from django.utils import timezone

@login_required
def notification_list(request):
    """Liste des notifications de l'utilisateur utilisant le modèle Django"""
    user = request.user
    
    # Filtrer les notifications selon le rôle de l'utilisateur
    if user.role == 'admin':
        # L'admin voit toutes les notifications
        notifications = Notification.objects.all().order_by('-created_at')
    else:
        # Les autres utilisateurs (coach, player) voient UNIQUEMENT leurs notifications
        notifications = Notification.objects.filter(recipient=user).order_by('-created_at')
    
    # Appliquer les filtres
    notification_type = request.GET.get('type')
    status = request.GET.get('status')
    period = request.GET.get('period')
    
    if notification_type:
        type_mapping = {
            'payment': [NotificationType.PAYMENT_SUBMISSION, NotificationType.PAYMENT_VALIDATED, 
                      NotificationType.PAYMENT_REJECTED, NotificationType.COACH_PAYMENT],
            'confirmation': [NotificationType.RESERVATION_CONFIRMED],
            'rejection': [NotificationType.RESERVATION_REJECTED],
            'activity': [NotificationType.ACTIVITY_REMINDER, NotificationType.ACTIVITY_CANCELLED, 
                       NotificationType.ACTIVITY_MODIFIED]
        }
        if notification_type in type_mapping:
            notifications = notifications.filter(notification_type__in=type_mapping[notification_type])
    
    if status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif status == 'read':
        notifications = notifications.filter(is_read=True)
    
    if period == 'today':
        notifications = notifications.filter(created_at__date=timezone.now().date())
    elif period == 'week':
        week_ago = timezone.now() - timezone.timedelta(days=7)
        notifications = notifications.filter(created_at__gte=week_ago)
    elif period == 'month':
        month_ago = timezone.now() - timezone.timedelta(days=30)
        notifications = notifications.filter(created_at__gte=month_ago)
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculer les statistiques
    total_notifications = paginator.count
    unread_count = Notification.objects.filter(recipient=user, is_read=False).count() if user.role != 'admin' else notifications.filter(is_read=False).count()
    
    # Compter par type
    payment_notifications = notifications.filter(
        notification_type__in=[NotificationType.PAYMENT_SUBMISSION, NotificationType.PAYMENT_VALIDATED, 
                              NotificationType.PAYMENT_REJECTED, NotificationType.COACH_PAYMENT]
    ).count()
    
    confirmation_notifications = notifications.filter(
        notification_type=NotificationType.RESERVATION_CONFIRMED
    ).count()
    
    # Pourcentages
    if total_notifications > 0:
        unread_percentage = (unread_count / total_notifications) * 100
        payment_percentage = (payment_notifications / total_notifications) * 100
        confirmation_percentage = (confirmation_notifications / total_notifications) * 100
    else:
        unread_percentage = payment_percentage = confirmation_percentage = 0
    
    context = {
        'notifications': page_obj,
        'total_notifications': total_notifications,
        'unread_count': unread_count,
        'payment_notifications': payment_notifications,
        'confirmation_notifications': confirmation_notifications,
        'unread_percentage': unread_percentage,
        'payment_percentage': payment_percentage,
        'confirmation_percentage': confirmation_percentage,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    }
    return render(request, 'notifications/notification_list_dashboard.html', context)

@login_required
def notification_count_view(request):
    """API pour obtenir le nombre de notifications non lues"""
    user = request.user
    
    if user.role == 'admin':
        # L'admin voit toutes les notifications non lues
        count = Notification.objects.filter(is_read=False).count()
    else:
        # Les autres utilisateurs (coach, player) voient UNIQUEMENT leurs notifications non lues
        count = Notification.objects.filter(recipient=user, is_read=False).count()
    
    return JsonResponse({'count': count})

@login_required
def mark_all_read(request):
    """Marquer toutes les notifications comme lues"""
    user = request.user
    
    if user.role == 'admin':
        # L'admin peut marquer toutes les notifications comme lues
        notifications = Notification.objects.filter(is_read=False)
    else:
        # Les autres utilisateurs (coach, player) marquent UNIQUEMENT leurs notifications
        notifications = Notification.objects.filter(recipient=user, is_read=False)
    
    count = notifications.count()
    notifications.update(is_read=True, read_at=timezone.now())
    
    return JsonResponse({'success': True, 'count': count})

@login_required
def mark_notification_read(request, notification_id):
    """Marquer une notification spécifique comme lue"""
    notification = get_object_or_404(Notification, id=notification_id)
    
    # Vérifier les permissions
    if request.user.role != 'admin' and notification.recipient != request.user:
        return JsonResponse({'success': False, 'error': 'Permission refusée'}, status=403)
    
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
    
    return JsonResponse({'success': True})

@login_required
def delete_notification(request, notification_id):
    """Supprimer une notification spécifique"""
    if request.method == 'DELETE':
        notification = get_object_or_404(Notification, id=notification_id)
        
        # Vérifier les permissions
        if request.user.role != 'admin' and notification.recipient != request.user:
            return JsonResponse({'success': False, 'error': 'Permission refusée'}, status=403)
        
        notification.delete()
        
        return JsonResponse({'success': True, 'deleted': 1})
    
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'}, status=405)
