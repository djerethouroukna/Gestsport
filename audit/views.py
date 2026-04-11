from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.response import Response

from .models import AuditLog


@staff_member_required
def audit_dashboard(request):
    """
    Vue pour le dashboard d'audit avec statistiques
    """
    # Périodes pour les statistiques
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Statistiques générales
    total_logs = AuditLog.objects.count()
    today_logs = AuditLog.objects.filter(timestamp__date=today).count()
    week_logs = AuditLog.objects.filter(timestamp__date__gte=week_ago).count()
    month_logs = AuditLog.objects.filter(timestamp__date__gte=month_ago).count()
    
    # Utilisateurs actifs
    active_users_today = AuditLog.objects.filter(
        timestamp__date=today,
        user__isnull=False
    ).values('user').distinct().count()
    
    # Actions par type
    actions_by_type = AuditLog.objects.values('action').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Modèles les plus actifs
    models_by_activity = AuditLog.objects.values('model_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Actions récentes
    recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:20]
    
    # Connexions échouées récentes
    failed_logins = AuditLog.objects.filter(
        action='FAILED_LOGIN'
    ).order_by('-timestamp')[:10]
    
    # Activité par heure (aujourd'hui)
    activity_by_hour = []
    for hour in range(24):
        count = AuditLog.objects.filter(
            timestamp__date=today,
            timestamp__hour=hour
        ).count()
        activity_by_hour.append({'hour': hour, 'count': count})
    
    context = {
        # Statistiques
        'total_logs': total_logs,
        'today_logs': today_logs,
        'week_logs': week_logs,
        'month_logs': month_logs,
        'active_users_today': active_users_today,
        
        # Données pour graphiques
        'actions_by_type': list(actions_by_type),
        'models_by_activity': list(models_by_activity),
        'activity_by_hour': activity_by_hour,
        
        # Listes
        'recent_logs': recent_logs,
        'failed_logins': failed_logins,
    }
    
    return render(request, 'audit/dashboard.html', context)


@staff_member_required
def audit_api_stats(request):
    """
    API pour les statistiques d'audit (format JSON)
    """
    period = request.GET.get('period', 'today')
    
    if period == 'today':
        since = timezone.now().date()
    elif period == 'week':
        since = timezone.now().date() - timedelta(days=7)
    elif period == 'month':
        since = timezone.now().date() - timedelta(days=30)
    else:
        since = timezone.now().date() - timedelta(days=1)
    
    stats = {
        'total_actions': AuditLog.objects.filter(timestamp__date__gte=since).count(),
        'unique_users': AuditLog.objects.filter(
            timestamp__date__gte=since,
            user__isnull=False
        ).values('user').distinct().count(),
        'failed_logins': AuditLog.objects.filter(
            action='FAILED_LOGIN',
            timestamp__date__gte=since
        ).count(),
        'top_actions': list(AuditLog.objects.filter(
            timestamp__date__gte=since
        ).values('action').annotate(count=Count('id')).order_by('-count')[:5])
    }
    
    return JsonResponse(stats)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def audit_log_action(request):
    """
    API pour enregistrer une action dans l'audit log
    """
    try:
        # Récupérer les données
        action = request.data.get('action', 'VIEW')
        model_name = request.data.get('model_name', 'Unknown')
        object_id = request.data.get('object_id', None)
        object_repr = request.data.get('object_repr', '')
        changes = request.data.get('changes', {})
        metadata = request.data.get('metadata', {})
        
        # Récupérer l'IP et user agent
        ip_address = request.META.get('REMOTE_ADDR', None)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Créer l'audit log
        audit_log = AuditLog.objects.create(
            user=request.user,
            action=action,
            model_name=model_name,
            object_id=object_id,
            object_repr=object_repr,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata
        )
        
        return Response({
            'success': True,
            'audit_id': audit_log.id,
            'message': 'Action enregistrée dans l\'audit log'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': f'Erreur lors de l\'enregistrement: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
