# admin_notifications.py
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required, user_passes_test

def is_admin(user):
    return user.role == 'admin'

@login_required
@user_passes_test(is_admin)
def admin_notifications_view(request):
    """Vue pour afficher les notifications admin"""
    with connection.cursor() as cursor:
        # Marquer comme lues
        cursor.execute("""
            UPDATE admin_notifications 
            SET is_read = TRUE 
            WHERE admin_email = %s AND is_read = FALSE
        """, [request.user.email])
        
        # Récupérer les notifications récentes
        cursor.execute("""
            SELECT * FROM admin_notifications 
            WHERE admin_email = %s 
            ORDER BY created_at DESC 
            LIMIT 20
        """, [request.user.email])
        
        notifications = cursor.fetchall()
    
    return render(request, 'admin/notifications.html', {
        'notifications': notifications,
        'unread_count': 0
    })

@login_required
@user_passes_test(is_admin)
def get_unread_count(request):
    """API pour obtenir le nombre de notifications non lues"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM admin_notifications 
            WHERE admin_email = %s AND is_read = FALSE
        """, [request.user.email])
        count = cursor.fetchone()[0]
    
    from django.http import JsonResponse
    return JsonResponse({'count': count})
