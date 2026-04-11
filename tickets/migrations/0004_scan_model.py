# Generated migration for Scan model
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tickets', '0003_auto_20260216_1408'),
    ]

    operations = [
        migrations.CreateModel(
            name='scan',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scanner_id', models.CharField(max_length=50, help_text="Identifiant unique du scanner")),
                ('scanned_at', models.DateTimeField(auto_now_add=True, help_text="Date et heure du scan")),
                ('location', models.CharField(max_length=100, help_text="Lieu du scan")),
                ('is_valid', models.BooleanField(default=True, help_text="Le scan est-il valide ?")),
                ('notes', models.TextField(blank=True, null=True, help_text="Notes supplémentaires")),
                ('ticket', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='scans', to='tickets.ticket')),
            ],
            options={
                'verbose_name': 'Scan',
                'verbose_name_plural': 'Scans',
                'permissions': [
                    ('can_scan_tickets', 'Peut scanner des tickets'),
                    ('can_view_scan_history', 'Peut voir l\'historique des scans'),
                ],
                'ordering': ['-scanned_at'],
            },
        ),
    ]
