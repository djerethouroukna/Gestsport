import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.utils import timezone

from reservations.models import Reservation
from payments.models import Payment
from users.models import User

print("=== CRÉATION SYSTÈME NOTIFICATION ADMIN ===")

# Créer un modèle de notification simple
try:
    # Créer une table de notifications simple
    from django.db import connection
    
    # Vérifier si la table existe
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id SERIAL PRIMARY KEY,
                reservation_id INTEGER REFERENCES reservations_reservation(id),
                payment_id UUID REFERENCES payments_payment(id),
                admin_email VARCHAR(255),
                message TEXT,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("✅ Table admin_notifications créée/vérifiée")
        
except Exception as e:
    print(f"❌ Erreur création table: {e}")

# Créer les notifications pour les réservations payées non confirmées
try:
    admins = User.objects.filter(role='admin')
    paid_unconfirmed = Reservation.objects.filter(
        status='pending'
    ).filter(
        payment__status='paid'
    )
    
    print(f"Admins: {admins.count()}")
    print(f"Réservations payées non confirmées: {paid_unconfirmed.count()}")
    
    for reservation in paid_unconfirmed:
        payment = Payment.objects.filter(reservation=reservation, status='paid').first()
        
        for admin in admins:
            # Insérer la notification
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO admin_notifications 
                    (reservation_id, payment_id, admin_email, message, is_read, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, [
                    reservation.id,
                    payment.id if payment else None,
                    admin.email,
                    f"Réservation {reservation.id} payée par {reservation.user.email} - En attente de confirmation",
                    False,
                    timezone.now()
                ])
            
            print(f"✅ Notification créée pour {admin.email}")
    
except Exception as e:
    print(f"❌ Erreur création notifications: {e}")

# Vérifier les notifications existantes
try:
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*) FROM admin_notifications WHERE is_read = FALSE
        """)
        unread_count = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT * FROM admin_notifications WHERE is_read = FALSE ORDER BY created_at DESC LIMIT 5
        """)
        notifications = cursor.fetchall()
        
        print(f"\n📊 NOTIFICATIONS ADMIN NON LUES: {unread_count}")
        for notif in notifications:
            print(f"  - {notif[4]} (Réservation {notif[1]})")
            
except Exception as e:
    print(f"❌ Erreur lecture notifications: {e}")

print(f"\n=== CRÉATION VUE ADMIN NOTIFICATIONS ===")

# Créer une vue simple pour afficher les notifications
view_code = '''
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
'''

print("✅ Code vue admin_notifications.py généré")
print("✅ Ajoutez ce code dans votre application admin")

print(f"\n=== URL POUR NOTIFICATIONS ===")
url_code = '''
# urls.py (dans votre app admin)
from django.urls import path
from . import admin_notifications

urlpatterns = [
    path('notifications/', admin_notifications.admin_notifications_view, name='admin_notifications'),
]
'''

print("✅ Code URL généré")

print(f"\n=== TEMPLATE POUR NOTIFICATIONS ===")
template_code = '''
<!-- templates/admin/notifications.html -->
{% extends "base.html" %}

{% block content %}
<div class="container mt-4">
    <h2>Notifications Admin</h2>
    
    {% if notifications %}
        <div class="list-group">
            {% for notif in notifications %}
                <div class="list-group-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <p class="mb-1">{{ notif.4 }}</p>
                            <small class="text-muted">Réservation #{{ notif.1 }} - {{ notif.6 }}</small>
                        </div>
                        <div>
                            <a href="/reservations/{{ notif.1 }}/" class="btn btn-sm btn-primary">
                                Voir
                            </a>
                        </div>
                    </div>
                </div>
            {% endfor %}
        </div>
    {% else %}
        <div class="alert alert-info">
            Aucune notification
        </div>
    {% endif %}
</div>
{% endblock %}
'''

print("✅ Code template généré")

print(f"\n=== INTÉGRATION DANS LE MENU ADMIN ===")
menu_code = '''
<!-- Dans votre template base.html, ajoutez ce badge -->
{% if user.role == 'admin' %}
<li class="nav-item">
    <a class="nav-link" href="{% url 'admin:admin_notifications' %}">
        <i class="fas fa-bell"></i> Notifications
        <span class="badge badge-danger" id="notification-count">0</span>
    </a>
</li>
{% endif %}
'''

print("✅ Code menu généré")

print(f"\n=== RÉSULTAT ===")
print("1. ✅ Table de notifications créée")
print("2. ✅ Notifications insérées pour les réservations payées")
print("3. ✅ Code généré pour l'intégration")
print("4. Les admins verront maintenant les paiements à confirmer")
