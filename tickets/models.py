# tickets/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid


class Ticket(models.Model):
    """Ticket pour réservation confirmée"""
    id = models.AutoField(
        primary_key=True,
        verbose_name=_('ID')
    )
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        verbose_name=_('réservation')
    )
    ticket_number = models.CharField(
        max_length=50, 
        unique=True,
        verbose_name=_('numéro de ticket')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('date de création')
    )
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('date de génération')
    )
    qr_code = models.ImageField(
        upload_to='tickets/qr_codes/',
        blank=True,
        null=True,
        max_length=255,
        verbose_name=_('code QR')
    )
    is_valid = models.BooleanField(
        default=True,
        verbose_name=_('valide')
    )
    is_used = models.BooleanField(
        default=False,
        verbose_name=_('utilisé')
    )
    used_at = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name=_('date d\'utilisation')
    )
    used_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('utilisé par')
    )
    
    class Meta:
        verbose_name = _('ticket')
        verbose_name_plural = _('tickets')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.reservation}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        # NE PAS générer QR code ici - séparation complète
        super().save(*args, **kwargs)
        
        # Générer QR code APRÈS la sauvegarde (transaction séparée)
        if not self.qr_code:
            self.schedule_qr_generation()
    
    def generate_ticket_number(self):
        """Génère un numéro de ticket unique"""
        max_attempts = 10
        for _ in range(max_attempts):
            ticket_number = f"TKT-{uuid.uuid4().hex[:8].upper()}"
            if not Ticket.objects.filter(ticket_number=ticket_number).exists():
                return ticket_number
        # Fallback: utiliser timestamp
        return f"TKT-{timezone.now().strftime('%Y%m%d%H%M%S')}"
    
    def schedule_qr_generation(self):
        """Programme la génération QR code en arrière-plan"""
        import threading
        import time
        
        def generate_qr_background():
            # Petite pause pour s'assurer que la transaction est terminée
            time.sleep(0.5)
            try:
                self.generate_qr_code_separated()
            except Exception as e:
                print(f"Erreur génération QR en arrière-plan: {e}")
        
        thread = threading.Thread(target=generate_qr_background)
        thread.daemon = True
        thread.start()
    
    def generate_qr_code_separated(self):
        """Génère le QR code dans une transaction séparée"""
        from django.db import transaction
        
        try:
            import qrcode
            from io import BytesIO
            from django.core.files import File
            
            # Données du QR code
            qr_data = {
                'ticket_number': self.ticket_number,
                'reservation_id': self.reservation.id,
                'activity': self.reservation.activity.title if self.reservation.activity else 'Réservation standard',
                'terrain': self.reservation.terrain.name,
                'date': self.reservation.start_time.isoformat(),
                'coach': self.reservation.user.get_full_name() or self.reservation.user.username
            }
            
            # Générer QR code en mémoire
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(str(qr_data))
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            
            # Sauvegarder dans une transaction séparée
            with transaction.atomic():
                # Recharger l'objet pour éviter les problèmes de cache
                ticket = Ticket.objects.get(pk=self.pk)
                
                # Utiliser un nom de fichier plus court
                short_number = ticket.ticket_number.replace('TKT-', '')[:12]
                filename = f"qr_{short_number}.png"
                
                # Sauvegarder l'image
                ticket.qr_code.save(filename, File(buffer), save=True)
                buffer.close()
                
            print(f"[OK] QR code généré pour {self.ticket_number}")
            
        except Exception as e:
            print(f"[ERREUR] Erreur génération QR code séparé: {e}")
    
    def generate_qr_code(self):
        """Méthode legacy maintenue pour compatibilité"""
        # Cette méthode ne fait plus rien - tout est géré par schedule_qr_generation
        pass
    
    def is_valid(self):
        """Vérifie si le ticket est valide"""
        return not self.is_used
    
    @property
    def get_qr_data(self):
        """Retourne les données du QR code"""
        return {
            'ticket_number': self.ticket_number,
            'reservation_id': self.reservation.id,
            'activity': self.reservation.activity.title if self.reservation.activity else 'Réservation standard',
            'terrain': self.reservation.terrain.name,
            'date': self.reservation.start_time.isoformat(),
            'coach': self.reservation.user.get_full_name() or self.reservation.user.username
        }


class Scan(models.Model):
    """Modèle pour enregistrer les scans des tickets"""
    scanner_id = models.CharField(max_length=50, help_text="Identifiant unique du scanner")
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='scans')
    scanned_at = models.DateTimeField(auto_now_add=True, help_text="Date et heure du scan")
    location = models.CharField(max_length=100, help_text="Lieu du scan")
    is_valid = models.BooleanField(default=True, help_text="Le scan est-il valide ?")
    notes = models.TextField(blank=True, null=True, help_text="Notes supplémentaires")
    
    class Meta:
        permissions = [
            ("can_scan_tickets", "Peut scanner des tickets"),
            ("can_view_scan_history", "Peut voir l'historique des scans"),
        ]
        ordering = ['-scanned_at']
    
    def __str__(self):
        return f"Scan {self.ticket.ticket_number} par {self.scanner_id} à {self.scanned_at}"
