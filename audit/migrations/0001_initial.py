# Generated migration for audit app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('CREATE', 'Création'), ('UPDATE', 'Modification'), ('DELETE', 'Suppression'), ('LOGIN', 'Connexion'), ('LOGOUT', 'Déconnexion'), ('VIEW', 'Consultation'), ('EXPORT', 'Export'), ('FAILED_LOGIN', 'Connexion échouée'), ('PASSWORD_CHANGE', 'Changement mot de passe'), ('PERMISSION_CHANGE', 'Changement permissions')], max_length=20, verbose_name='Action')),
                ('model_name', models.CharField(db_index=True, max_length=100, verbose_name='Modèle')),
                ('object_id', models.PositiveIntegerField(blank=True, db_index=True, null=True, verbose_name='ID de l\'objet')),
                ('object_repr', models.CharField(max_length=200, verbose_name='Représentation de l\'objet')),
                ('changes', models.JSONField(blank=True, default=dict, verbose_name='Changements')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Date/Heure')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='Adresse IP')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Métadonnées')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.user', verbose_name='Utilisateur')),
            ],
            options={
                'verbose_name': 'Log d\'audit',
                'verbose_name_plural': 'Logs d\'audit',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', 'timestamp'], name='audit_auditlog_user_id'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'timestamp'], name='audit_auditlog_action'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['model_name', 'timestamp'], name='audit_auditlog_model_'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['timestamp'], name='audit_auditlog_timest'),
        ),
    ]
