# payments/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid


class PaymentMethodType(models.TextChoices):
    CARD = 'card', _('Carte bancaire')
    MOBILE_MONEY = 'mobile_money', _('Mobile Money')
    CASH = 'cash', _('Espèces')
    BANK_TRANSFER = 'bank_transfer', _('Virement bancaire')
    WALLET = 'wallet', _('Portefeuille')


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', _('En attente')
    PROCESSING = 'processing', _('En traitement')
    COMPLETED = 'completed', _('Terminé')
    FAILED = 'failed', _('Échoué')
    CANCELLED = 'cancelled', _('Annulé')
    REFUNDED = 'refunded', _('Remboursé')
    SIMULATED = 'simulated', _('Simulé')


class PaymentSubmissionStatus(models.TextChoices):
    SUBMITTED = 'submitted', _('Soumis')
    UNDER_REVIEW = 'under_review', _('En cours de validation')
    VALIDATED = 'validated', _('Validé')
    REJECTED = 'rejected', _('Rejeté')


class PaymentMethod(models.Model):
    """Moyens de paiement des utilisateurs"""
    class Meta:
        verbose_name = _('moyen de paiement')
        verbose_name_plural = _('moyens de paiement')
        ordering = ['-is_default', 'created_at']

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name=_('utilisateur')
    )
    method_type = models.CharField(
        _('type de moyen'),
        max_length=20,
        choices=PaymentMethodType.choices
    )
    provider = models.CharField(
        _('fournisseur'),
        max_length=50,
        help_text=_('Orange, Wave, MTN, etc.')
    )
    identifier = models.CharField(
        _('identifiant'),
        max_length=100,
        help_text=_('Numéro de carte, téléphone, etc.')
    )
    display_name = models.CharField(
        _('nom d\'affichage'),
        max_length=100,
        help_text=_('Carte ****1234, Orange ****5678')
    )
    is_default = models.BooleanField(_('par défaut'), default=False)
    is_active = models.BooleanField(_('actif'), default=True)
    is_verified = models.BooleanField(_('vérifié'), default=False)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.display_name}"


class PaymentSubmission(models.Model):
    """Soumissions de paiement en attente de validation manuelle"""
    class Meta:
        verbose_name = _('soumission de paiement')
        verbose_name_plural = _('soumissions de paiement')
        ordering = ['-created_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='payment_submission',
        verbose_name=_('réservation')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_submissions',
        verbose_name=_('utilisateur')
    )
    amount = models.DecimalField(
        _('montant'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(_('devise'), max_length=3, default='XOF')
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=PaymentSubmissionStatus.choices,
        default=PaymentSubmissionStatus.SUBMITTED
    )
    payment_method_type = models.CharField(
        _('type de paiement'),
        max_length=20,
        choices=PaymentMethodType.choices
    )
    payment_details = models.JSONField(
        _('détails du paiement'),
        default=dict,
        blank=True,
        help_text=_('Informations de paiement cryptées')
    )
    card_last_four = models.CharField(
        _('4 derniers chiffres'),
        max_length=4,
        blank=True,
        help_text=_('4 derniers chiffres de la carte')
    )
    card_holder_name = models.CharField(
        _('nom du porteur'),
        max_length=100,
        blank=True
    )
    mobile_number = models.CharField(
        _('numéro mobile'),
        max_length=20,
        blank=True
    )
    mobile_provider = models.CharField(
        _('opérateur mobile'),
        max_length=50,
        blank=True,
        help_text=_('Orange, MTN, Moov, etc.')
    )
    submission_ip = models.GenericIPAddressField(
        _('IP de soumission'),
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        _('user agent'),
        blank=True
    )
    notes = models.TextField(_('notes'), blank=True)
    rejection_reason = models.TextField(
        _('raison du rejet'),
        blank=True
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_payment_submissions',
        verbose_name=_('validé par')
    )
    validated_at = models.DateTimeField(
        _('date de validation'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Soumission {self.id} - {self.reservation} - {self.amount} {self.currency}"

    @property
    def is_pending_validation(self):
        """Vérifie si la soumission est en attente de validation"""
        return self.status in [PaymentSubmissionStatus.SUBMITTED, PaymentSubmissionStatus.UNDER_REVIEW]

    @property
    def is_validated(self):
        """Vérifie si la soumission a été validée"""
        return self.status == PaymentSubmissionStatus.VALIDATED

    @property
    def is_rejected(self):
        """Vérifie si la soumission a été rejetée"""
        return self.status == PaymentSubmissionStatus.REJECTED

    @property
    def payment_method_display(self):
        """Retourne l'affichage du moyen de paiement"""
        if self.payment_method_type == PaymentMethodType.CARD:
            return f"Carte ****{self.card_last_four}" if self.card_last_four else "Carte bancaire"
        elif self.payment_method_type == PaymentMethodType.MOBILE_MONEY:
            return f"{self.mobile_provider} ****{self.mobile_number[-4:]}" if self.mobile_number else "Mobile Money"
        else:
            return self.get_payment_method_type_display()

    def validate_submission(self, admin_user, notes=""):
        """Valide la soumission de paiement"""
        from django.utils import timezone
        self.status = PaymentSubmissionStatus.VALIDATED
        self.validated_by = admin_user
        self.validated_at = timezone.now()
        self.notes = notes
        self.save()

        # Créer le paiement validé
        payment = Payment.objects.create(
            reservation=self.reservation,
            user=self.user,
            amount=self.amount,
            currency=self.currency,
            status=PaymentStatus.SIMULATED,
            is_simulated=True,
            simulation_data={
                'submission_id': str(self.id),
                'validated_by': admin_user.get_full_name(),
                'validated_at': self.validated_at.isoformat()
            },
            notes=f"Paiement validé manuellement par {admin_user.get_full_name()}. {notes}"
        )

        return payment

    def reject_submission(self, admin_user, reason=""):
        """Rejette la soumission de paiement"""
        from django.utils import timezone
        self.status = PaymentSubmissionStatus.REJECTED
        self.validated_by = admin_user
        self.validated_at = timezone.now()
        self.rejection_reason = reason
        self.save()

        return self


class Transaction(models.Model):
    """Transactions individuelles"""
    class Meta:
        verbose_name = _('transaction')
        verbose_name_plural = _('transactions')
        ordering = ['-created_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(
        _('ID transaction externe'),
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )
    amount = models.DecimalField(
        _('montant'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(_('devise'), max_length=3, default='XOF')
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('moyen de paiement')
    )
    gateway_response = models.JSONField(
        _('réponse passerelle'),
        default=dict,
        blank=True
    )
    failure_reason = models.TextField(
        _('raison d\'échec'),
        blank=True
    )
    processed_at = models.DateTimeField(
        _('date de traitement'),
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Transaction {self.id} - {self.amount} {self.currency}"


class Payment(models.Model):
    """Paiements liés aux réservations"""
    class Meta:
        verbose_name = _('paiement')
        verbose_name_plural = _('paiements')
        ordering = ['-created_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='payment',
        verbose_name=_('réservation')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('utilisateur')
    )
    amount = models.DecimalField(
        _('montant'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(_('devise'), max_length=3, default='XOF')
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('moyen de paiement')
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment',
        verbose_name=_('transaction')
    )
    is_simulated = models.BooleanField(_('simulé'), default=False)
    simulation_data = models.JSONField(
        _('données de simulation'),
        default=dict,
        blank=True
    )
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)
    paid_at = models.DateTimeField(_('date de paiement'), null=True, blank=True)

    def __str__(self):
        return f"Paiement {self.id} - {self.reservation} - {self.amount} {self.currency}"

    @property
    def is_paid(self):
        return self.status in [PaymentStatus.COMPLETED, PaymentStatus.SIMULATED, 'paid']

    @property
    def can_be_refunded(self):
        return self.is_paid and self.status != PaymentStatus.REFUNDED


class Refund(models.Model):
    """Remboursements"""
    class Meta:
        verbose_name = _('remboursement')
        verbose_name_plural = _('remboursements')
        ordering = ['-created_at']

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds',
        verbose_name=_('paiement')
    )
    amount = models.DecimalField(
        _('montant'),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reason = models.TextField(_('raison du remboursement'))
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    refund_transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='refund',
        verbose_name=_('transaction de remboursement')
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processed_refunds',
        verbose_name=_('traité par')
    )
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Remboursement {self.id} - {self.amount} {self.payment.currency}"


class PaymentSettings(models.Model):
    """Configuration des paiements"""
    class Meta:
        verbose_name = _('configuration de paiement')
        verbose_name_plural = _('configurations de paiement')

    key = models.CharField(_('clé'), max_length=100, unique=True)
    value = models.JSONField(_('valeur'))
    description = models.TextField(_('description'), blank=True)
    is_active = models.BooleanField(_('actif'), default=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"{self.key}: {self.value}"


class InvoiceStatus(models.TextChoices):
    """Statuts des factures"""
    DRAFT = 'draft', _('Brouillon')
    SENT = 'sent', _('Envoyée')
    PAID = 'paid', _('Payée')
    OVERDUE = 'overdue', _('En retard')
    CANCELLED = 'cancelled', _('Annulée')


class Invoice(models.Model):
    """Factures pour les paiements"""
    class Meta:
        verbose_name = _('facture')
        verbose_name_plural = _('factures')
        ordering = ['-created_at']

    # Numérotation automatique
    invoice_number = models.CharField(
        _('numéro de facture'),
        max_length=50,
        unique=True,
        editable=False
    )
    
    # Relations
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name=_('réservation')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name=_('utilisateur')
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='invoice',
        verbose_name=_('paiement'),
        null=True,
        blank=True
    )
    
    # Montants
    amount_ht = models.DecimalField(
        _('montant HT'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Montant hors taxes')
    )
    vat_rate = models.DecimalField(
        _('taux TVA'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('20.00'),
        help_text=_('Taux de TVA en pourcentage')
    )
    vat_amount = models.DecimalField(
        _('montant TVA'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Montant de la TVA')
    )
    amount_ttc = models.DecimalField(
        _('montant TTC'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Montant toutes taxes comprises')
    )
    
    # Dates
    invoice_date = models.DateField(
        _('date de facture'),
        auto_now_add=True
    )
    due_date = models.DateField(
        _('date d\'échéance'),
        help_text=_('Date limite de paiement')
    )
    paid_date = models.DateField(
        _('date de paiement'),
        null=True,
        blank=True
    )
    
    # Statut et documents
    status = models.CharField(
        _('statut'),
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT
    )
    pdf_file = models.FileField(
        _('fichier PDF'),
        upload_to='invoices/%Y/%m/',
        null=True,
        blank=True
    )
    
    # Envoi
    sent_by_email = models.BooleanField(
        _('envoyée par email'),
        default=False
    )
    sent_at = models.DateTimeField(
        _('date d\'envoi'),
        null=True,
        blank=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de mise à jour'), auto_now=True)

    def __str__(self):
        return f"Facture {self.invoice_number} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Génération automatique du numéro de facture
        if not self.invoice_number:
            current_year = timezone.now().year
            last_invoice = Invoice.objects.filter(
                created_at__year=current_year
            ).order_by('-invoice_number').first()
            
            if last_invoice:
                try:
                    last_number = int(last_invoice.invoice_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            
            self.invoice_number = f"FAC-{current_year}-{new_number:05d}"
        
        # Calcul automatique des montants si non spécifiés
        if self.amount_ht and not self.vat_amount:
            self.vat_amount = self.amount_ht * (self.vat_rate / 100)
        
        if self.amount_ht and self.vat_amount and not self.amount_ttc:
            self.amount_ttc = self.amount_ht + self.vat_amount
        
        super().save(*args, **kwargs)

    @property
    def is_paid(self):
        """Vérifie si la facture est payée"""
        return self.status == InvoiceStatus.PAID

    @property
    def is_overdue(self):
        """Vérifie si la facture est en retard"""
        from django.utils import timezone
        return (
            self.status != InvoiceStatus.PAID and 
            self.due_date and 
            self.due_date < timezone.now().date()
        )

    @property
    def can_be_sent(self):
        """Vérifie si la facture peut être envoyée"""
        return self.status in [InvoiceStatus.DRAFT, InvoiceStatus.SENT]

    def mark_as_sent(self):
        """Marque la facture comme envoyée"""
        from django.utils import timezone
        self.status = InvoiceStatus.SENT
        self.sent_by_email = True
        self.sent_at = timezone.now()
        self.save()

    def mark_as_paid(self):
        """Marque la facture comme payée"""
        from django.utils import timezone
        self.status = InvoiceStatus.PAID
        self.paid_date = timezone.now().date()
        self.save()

    def get_absolute_url(self):
        """URL absolue de la facture"""
        from django.urls import reverse
        return reverse('payments:invoice_detail', kwargs={'invoice_number': self.invoice_number})
