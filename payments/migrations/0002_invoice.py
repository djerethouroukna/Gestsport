# Generated migration for Invoice model

import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
        ('reservations', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('invoice_number', models.CharField(editable=False, max_length=50, unique=True, verbose_name='numéro de facture')),
                ('amount_ht', models.DecimalField(decimal_places=2, help_text='Montant hors taxes', max_digits=10, verbose_name='montant HT')),
                ('vat_rate', models.DecimalField(decimal_places=2, default=Decimal('20.00'), help_text='Taux de TVA en pourcentage', max_digits=5, verbose_name='taux TVA')),
                ('vat_amount', models.DecimalField(decimal_places=2, help_text='Montant de la TVA', max_digits=10, verbose_name='montant TVA')),
                ('amount_ttc', models.DecimalField(decimal_places=2, help_text='Montant toutes taxes comprises', max_digits=10, verbose_name='montant TTC')),
                ('invoice_date', models.DateField(auto_now_add=True, verbose_name='date de facture')),
                ('due_date', models.DateField(help_text='Date limite de paiement', verbose_name='date d\'échéance')),
                ('paid_date', models.DateField(blank=True, null=True, verbose_name='date de paiement')),
                ('status', models.CharField(choices=[('draft', 'Brouillon'), ('sent', 'Envoyée'), ('paid', 'Payée'), ('overdue', 'En retard'), ('cancelled', 'Annulée')], default='draft', max_length=20, verbose_name='statut')),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to='invoices/%Y/%m/', verbose_name='fichier PDF')),
                ('sent_by_email', models.BooleanField(default=False, verbose_name='envoyée par email')),
                ('sent_at', models.DateTimeField(blank=True, null=True, verbose_name='date d\'envoi')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='date de mise à jour')),
                ('payment', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='invoice', to='payments.payment', verbose_name='paiement')),
                ('reservation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='invoice', to='reservations.reservation', verbose_name='réservation')),
                ('user', models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE, related_name='invoices', verbose_name='utilisateur')),
            ],
            options={
                'verbose_name': 'facture',
                'verbose_name_plural': 'factures',
                'ordering': ['-created_at'],
            },
        ),
    ]
