from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class EmailService:
    """Service pour gérer l'envoi d'emails professionnels"""
    
    @staticmethod
    def send_reservation_notification(reservation, notification_type):
        """Envoyer un email de notification de réservation"""
        
        # Déterminer le template et le sujet selon le type
        templates = {
            'confirmed': {
                'template': 'emails/reservation_status.html',
                'subject': '✅ Réservation Confirmée - GestSport'
            },
            'pending': {
                'template': 'emails/reservation_status.html', 
                'subject': '⏳ Réservation en Attente - GestSport'
            },
            'rejected': {
                'template': 'emails/reservation_status.html',
                'subject': '❌ Réservation Rejetée - GestSport'
            },
            'cancelled': {
                'template': 'emails/reservation_status.html',
                'subject': '🚫 Réservation Annulée - GestSport'
            }
        }
        
        config = templates.get(notification_type, templates['pending'])
        
        # Préparer le contexte
        context = {
            'reservation': reservation,
            'user': reservation.user,
            'dashboard_url': 'http://127.0.0.1:8000/users/reservations/',
        }
        
        # Rendre les templates
        html_content = render_to_string(config['template'], context)
        text_content = f"""
        Bonjour {reservation.user.get_full_name()},
        
        Votre réservation du terrain {reservation.terrain.name} 
        le {reservation.start_time.strftime('%d/%m/%Y à %H:%M')} 
        est {reservation.get_status_display()}.
        
        Connectez-vous à votre compte pour plus de détails :
        http://127.0.0.1:8000/users/reservations/
        
        Cordialement,
        L'équipe GestSport
        """
        
        # Créer et envoyer l'email
        subject = settings.EMAIL_SUBJECT_PREFIX + config['subject']
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.user.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            print(f"✅ Email de réservation ({notification_type}) envoyé à {reservation.user.email}")
            return True
        except Exception as e:
            print(f"❌ Erreur envoi email réservation: {e}")
            return False
    
    @staticmethod
    def send_payment_confirmation(payment):
        """Envoyer un email de confirmation de paiement"""
        
        context = {
            'payment': payment,
            'user': payment.reservation.user,
            'receipt_url': f'http://127.0.0.1:8000/payments/receipt/{payment.id}/',
        }
        
        # Rendre les templates
        html_content = render_to_string('emails/payment_confirmation.html', context)
        text_content = f"""
        Bonjour {payment.reservation.user.get_full_name()},
        
        Merci pour votre paiement de {payment.amount} XAF.
        
        Votre réservation du terrain {payment.reservation.terrain.name} 
        le {payment.reservation.start_time.strftime('%d/%m/%Y à %H:%M')} 
        est maintenant confirmée.
        
        Facture disponible : http://127.0.0.1:8000/payments/receipt/{payment.id}/
        
        Cordialement,
        L'équipe GestSport
        """
        
        # Créer et envoyer l'email
        subject = settings.EMAIL_SUBJECT_PREFIX + "✅ Paiement Confirmé - GestSport"
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [payment.reservation.user.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            print(f"✅ Email de paiement envoyé à {payment.reservation.user.email}")
            return True
        except Exception as e:
            print(f"❌ Erreur envoi email paiement: {e}")
            return False
    
    @staticmethod
    def send_password_reset(user, reset_url):
        """Envoyer un email de réinitialisation de mot de passe"""
        
        context = {
            'user': user,
            'reset_url': reset_url,
            'request_ip': '127.0.0.1',  # À améliorer avec l'IP réelle
        }
        
        # Rendre les templates
        html_content = render_to_string('emails/password_reset.html', context)
        text_content = f"""
        Bonjour {user.get_full_name()},
        
        Vous avez demandé la réinitialisation de votre mot de passe.
        
        Cliquez sur ce lien pour réinitialiser : {reset_url}
        
        Ce lien expirera dans 1 heure.
        
        Si vous n'avez pas demandé cette réinitialisation, veuillez nous contacter.
        
        Cordialement,
        L'équipe GestSport
        """
        
        # Créer et envoyer l'email
        subject = settings.EMAIL_SUBJECT_PREFIX + "🔒 Réinitialisation Mot de Passe - GestSport"
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            print(f"✅ Email de réinitialisation envoyé à {user.email}")
            return True
        except Exception as e:
            print(f"❌ Erreur envoi email réinitialisation: {e}")
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """Envoyer un email de bienvenue après validation"""
        
        context = {
            'user': user,
            'dashboard_url': 'http://127.0.0.1:8000/dashboard/',
        }
        
        # Rendre les templates
        html_content = render_to_string('emails/welcome.html', context)
        text_content = f"""
        Bienvenue {user.get_full_name()} !
        
        Votre compte GestSport est maintenant activé.
        
        Connectez-vous pour commencer : http://127.0.0.1:8000/dashboard/
        
        Cordialement,
        L'équipe GestSport
        """
        
        # Créer et envoyer l'email
        subject = settings.EMAIL_SUBJECT_PREFIX + "🎉 Bienvenue sur GestSport !"
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send()
            print(f"✅ Email de bienvenue envoyé à {user.email}")
            return True
        except Exception as e:
            print(f"❌ Erreur envoi email bienvenue: {e}")
            return False
