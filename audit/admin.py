from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from django.utils.safestring import mark_safe
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
import json
import csv
import xlsxwriter
from io import BytesIO
from datetime import datetime

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Interface admin pour les logs d'audit"""
    
    list_display = [
        'timestamp', 'user_info', 'action_badge', 'model_info', 
        'object_repr', 'ip_address_short'
    ]
    list_filter = [
        'action', 'model_name', 'timestamp', 'user'
    ]
    search_fields = [
        'user__email', 'user__first_name', 'user__last_name',
        'object_repr', 'changes', 'ip_address'
    ]
    readonly_fields = [
        'timestamp', 'user', 'action', 'model_name',
        'object_id', 'object_repr', 'changes_display', 'ip_address',
        'user_agent', 'metadata_display'
    ]
    
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    # Configuration pour la performance
    list_per_page = 50
    show_full_result_count = False
    
    def has_add_permission(self, request):
        """Interdire la création manuelle de logs"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Interdire la modification des logs"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Autoriser la suppression uniquement pour les superadmins"""
        return request.user.is_superuser
    
    def get_actions(self, request):
        """Ajouter des actions personnalisées avec décorateurs"""
        actions = super().get_actions(request)
        
        if request.user.is_superuser:
            # Ajouter les actions d'export
            actions['export_csv_action'] = (
                self.export_csv_action,
                'export_csv_action',
                'Exporter en CSV'
            )
            actions['export_excel_action'] = (
                self.export_excel_action,
                'export_excel_action',
                'Exporter en Excel'
            )
            actions['export_pdf_action'] = (
                self.export_pdf_action,
                'export_pdf_action',
                'Exporter en PDF'
            )
            # Ajouter l'action de nettoyage
            actions['cleanup_old_logs_action'] = (
                self.cleanup_old_logs_action,
                'cleanup_old_logs_action',
                'Nettoyer les anciens logs'
            )
        
        return actions
    
    def user_info(self, obj):
        """Affichage formaté de l'utilisateur"""
        if obj.user:
            if obj.user.first_name:
                name = f"{obj.user.first_name} {obj.user.last_name}".strip()
                email = obj.user.email
                return format_html(
                    '<strong>{}</strong><br><small>{}</small>',
                    name or email,
                    email
                )
            else:
                return format_html('<strong>{}</strong>', obj.user.email)
        return mark_safe('<span class="text-muted">Système</span>')
    user_info.short_description = 'Utilisateur'
    user_info.admin_order_field = 'user'
    
    def action_badge(self, obj):
        """Affiche l'action avec un badge coloré"""
        colors = {
            'CREATE': 'success',
            'UPDATE': 'info', 
            'DELETE': 'danger',
            'LOGIN': 'primary',
            'LOGOUT': 'secondary',
            'VIEW': 'light',
            'EXPORT': 'warning',
            'FAILED_LOGIN': 'danger',
            'PASSWORD_CHANGE': 'warning',
            'PERMISSION_CHANGE': 'warning'
        }
        
        color = colors.get(obj.action, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = 'Action'
    action_badge.admin_order_field = 'action'
    
    def model_info(self, obj):
        """Affiche le modèle avec l'ID si disponible"""
        if obj.object_id:
            return format_html(
                '<strong>{}</strong><br><small>ID: #{}</small>',
                obj.model_name,
                obj.object_id
            )
        return format_html('<strong>{}</strong>', obj.model_name)
    model_info.short_description = 'Modèle'
    model_info.admin_order_field = 'model_name'
    
    def ip_address_short(self, obj):
        """Affiche l'IP de manière concise"""
        if obj.ip_address:
            return format_html(
                '<code>{}</code>',
                obj.ip_address
            )
        return mark_safe('<span class="text-muted">-</span>')
    ip_address_short.short_description = 'IP'
    
    def changes_display(self, obj):
        """Affiche les changements de manière lisible"""
        if not obj.changes:
            return mark_safe('<span class="text-muted">Aucun changement</span>')
        
        html = '<div style="max-width: 400px; overflow-x: auto;">'
        
        # Afficher les changements par clé
        for key, value in obj.changes.items():
            if isinstance(value, dict):
                html += f'<strong>{key}:</strong><br>'
                for sub_key, sub_value in value.items():
                    html += f'&nbsp;&nbsp;{sub_key}: {sub_value}<br>'
            else:
                html += f'<strong>{key}:</strong> {value}<br>'
        
        html += '</div>'
        return mark_safe(html)
    changes_display.short_description = 'Changements détectés'
    
    def metadata_display(self, obj):
        """Affiche les métadonnées de manière lisible"""
        if not obj.metadata:
            return mark_safe('<span class="text-muted">Aucune métadonnée</span>')
        
        html = '<div style="max-width: 400px; overflow-x: auto;">'
        
        # Afficher les métadonnées par clé
        for key, value in obj.metadata.items():
            html += f'<strong>{key}:</strong> {value}<br>'
        
        html += '</div>'
        return mark_safe(html)
    metadata_display.short_description = 'Métadonnées'
    ip_address_short.admin_order_field = 'ip_address'
    
    def get_queryset(self, request):
        """Optimiser les requêtes"""
        return super().get_queryset(request).select_related('user')
    
    def changelist_view(self, request, extra_context=None):
        """Ajouter des statistiques dans la vue liste"""
        # Calculer les statistiques
        total_logs = AuditLog.objects.count()
        today_logs = AuditLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).count()
        active_users = AuditLog.objects.filter(
            timestamp__date=timezone.now().date()
        ).values('user').distinct().count()
        
        # Actions récentes
        recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
        
        extra_context = extra_context or {}
        extra_context.update({
            'total_logs': total_logs,
            'today_logs': today_logs,
            'active_users': active_users,
            'recent_logs': recent_logs
        })
        
        return super().changelist_view(request, extra_context)
    
    def export_csv_action(self, request, queryset, *args, **kwargs):
        """Exporter les logs sélectionnés en CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # En-têtes
        headers = [
            'ID', 'Timestamp', 'Utilisateur', 'Email', 'Action', 
            'Modèle', 'ID Objet', 'Représentation', 'IP Address', 
            'User Agent', 'Changements', 'Métadonnées'
        ]
        writer.writerow(headers)
        
        # Données
        for log in queryset:
            row = [
                log.id,
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.get_full_name() if log.user else 'Système',
                log.user.email if log.user else '',
                log.get_action_display(),
                log.model_name,
                log.object_id or '',
                log.object_repr,
                log.ip_address or '',
                log.user_agent[:100] if log.user_agent else '',
                json.dumps(log.changes, ensure_ascii=False) if log.changes else '',
                json.dumps(log.metadata, ensure_ascii=False) if log.metadata else ''
            ]
            writer.writerow(row)
        
        # Ajouter message si possible
        if hasattr(request, '_messages'):
            messages.success(request, f'{queryset.count()} logs exportés en CSV')
        
        return response
    
    def export_excel_action(self, request, queryset, *args, **kwargs):
        """Exporter les logs sélectionnés en Excel"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('Logs d\'Audit')
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#007cba',
            'font_color': 'white',
            'border': 1
        })
        
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
        
        # En-têtes
        headers = [
            'ID', 'Timestamp', 'Utilisateur', 'Email', 'Action', 
            'Modèle', 'ID Objet', 'Représentation', 'IP Address', 
            'User Agent', 'Changements', 'Métadonnées'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
        
        # Données
        for row, log in enumerate(queryset, start=1):
            worksheet.write(row, 0, log.id)
            worksheet.write(row, 1, log.timestamp, date_format)
            worksheet.write(row, 2, log.user.get_full_name() if log.user else 'Système')
            worksheet.write(row, 3, log.user.email if log.user else '')
            worksheet.write(row, 4, log.get_action_display())
            worksheet.write(row, 5, log.model_name)
            worksheet.write(row, 6, log.object_id or '')
            worksheet.write(row, 7, log.object_repr)
            worksheet.write(row, 8, log.ip_address or '')
            worksheet.write(row, 9, log.user_agent[:100] if log.user_agent else '')
            worksheet.write(row, 10, json.dumps(log.changes, ensure_ascii=False) if log.changes else '')
            worksheet.write(row, 11, json.dumps(log.metadata, ensure_ascii=False) if log.metadata else '')
        
        # Ajuster la largeur des colonnes
        for col in range(len(headers)):
            worksheet.set_column(col, col, 20)
        
        workbook.close()
        output.seek(0)
        
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        # Ajouter message si possible
        if hasattr(request, '_messages'):
            messages.success(request, f'{queryset.count()} logs exportés en Excel')
        
        return response
    
    def export_pdf_action(self, request, queryset, *args, **kwargs):
        """Exporter les logs sélectionnés en PDF (version simplifiée)"""
        try:
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib import colors
            from reportlab.lib.units import inch
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            
            # Limiter à 100 logs pour éviter les PDF trop volumineux
            if queryset.count() > 100:
                messages.warning(request, 'Limité à 100 logs pour l\'export PDF')
                queryset = queryset[:100]
            
            # Créer le buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # center
            )
            
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=20,
                alignment=1
            )
            
            # Contenu
            story = []
            
            # Titre
            story.append(Paragraph("📊 Rapport d'Audit Système", title_style))
            
            # En-tête
            story.append(Paragraph(f"<b>Date d'export:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", header_style))
            story.append(Paragraph(f"<b>Exporté par:</b> {request.user.get_full_name() or request.user.email}", header_style))
            story.append(Paragraph(f"<b>Nombre de logs:</b> {queryset.count()}", header_style))
            story.append(Spacer(1, 20))
            
            # Données du tableau
            data = []
            
            # En-têtes
            headers = ['ID', 'Date/Heure', 'Utilisateur', 'Action', 'Modèle', 'Objet', 'IP']
            data.append(headers)
            
            # Données
            for log in queryset:
                row = [
                    str(log.id),
                    log.timestamp.strftime('%d/%m %H:%M'),
                    (log.user.get_full_name() or log.user.email) if log.user else 'Système',
                    log.get_action_display(),
                    log.model_name,
                    log.object_repr[:30] if log.object_repr else '',
                    log.ip_address or '-'
                ]
                data.append(row)
            
            # Créer le tableau
            table = Table(data, repeatRows=1)
            
            # Style du tableau
            table.setStyle(TableStyle([
                # En-tête
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                
                # Données
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # ID centré
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Date centrée
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),   # Utilisateur à gauche
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Action centrée
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Modèle centré
                ('ALIGN', (5, 1), (5, -1), 'LEFT'),   # Objet à gauche
                ('ALIGN', (6, 1), (6, -1), 'CENTER'),  # IP centrée
                
                # Alternance des lignes
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                
                # Bordures
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('TOPPADDING', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ]))
            
            story.append(table)
            
            # Pied de page
            story.append(Spacer(1, 30))
            story.append(Paragraph("<i>Généré par GestSport - Système d'Audit</i>", styles['Normal']))
            story.append(Paragraph("<small>Ce rapport contient des données sensibles. À traiter avec confidentialité.</small>", styles['Normal']))
            
            # Générer le PDF
            doc.build(story)
            
            # Récupérer le contenu du buffer
            buffer.seek(0)
            pdf_content = buffer.getvalue()
            
            # Créer la réponse HTTP
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
            response['Content-Length'] = len(pdf_content)
            
            # Ajouter message si possible
            if hasattr(request, '_messages'):
                messages.success(request, f'{queryset.count()} logs exportés en PDF')
            
            return response
            
        except ImportError:
            # Fallback si reportlab n'est pas installé
            if hasattr(request, '_messages'):
                messages.error(request, 'ReportLab requis pour l\'export PDF. Installez-le avec: pip install reportlab')
            return HttpResponseRedirect(reverse('admin:audit_auditlog_changelist'))
        except Exception as e:
            if hasattr(request, '_messages'):
                messages.error(request, f'Erreur lors de la génération PDF: {str(e)}')
            return HttpResponseRedirect(reverse('admin:audit_auditlog_changelist'))
    
    def cleanup_old_logs_action(self, request, queryset, *args, **kwargs):
        """Nettoyer les anciens logs (plus de 90 jours)"""
        from django.utils import timezone
        from datetime import timedelta
        
        if not request.user.is_superuser:
            if hasattr(request, '_messages'):
                messages.error(request, 'Action réservée aux superutilisateurs')
            return HttpResponseRedirect(reverse('admin:audit_auditlog_changelist'))
        
        cutoff_date = timezone.now() - timedelta(days=90)
        old_logs = AuditLog.objects.filter(timestamp__lt=cutoff_date)
        
        if old_logs.exists():
            count = old_logs.count()
            old_logs.delete()
            if hasattr(request, '_messages'):
                messages.success(request, f'{count} anciens logs supprimés (plus de 90 jours)')
        else:
            if hasattr(request, '_messages'):
                messages.info(request, 'Aucun ancien log à supprimer')
        
        return HttpResponseRedirect(reverse('admin:audit_auditlog_changelist'))
    
    fieldsets = (
        ('Informations générales', {
            'fields': (
                'timestamp', 'user', 'action', 'model_name'
            )
        }),
        ('Détails de l\'objet', {
            'fields': (
                'object_id', 'object_repr'
            )
        }),
        ('Changements', {
            'fields': ('changes_display',),
            'classes': ('collapse',)
        }),
        ('Contexte technique', {
            'fields': (
                'ip_address', 'user_agent'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        })
    )


# Personnalisation du template de l'admin pour inclure les statistiques
class AuditLogAdminSite(admin.AdminSite):
    """Site admin personnalisé pour les logs d'audit"""
    
    def index(self, request, extra_context=None):
        """Page d'index avec statistiques d'audit"""
        extra_context = extra_context or {}
        
        # Statistiques globales
        stats = {
            'total_logs': AuditLog.objects.count(),
            'today_logs': AuditLog.objects.filter(
                timestamp__date=timezone.now().date()
            ).count(),
            'failed_logins': AuditLog.objects.filter(
                action='FAILED_LOGIN'
            ).count(),
            'recent_activity': AuditLog.objects.select_related('user').order_by('-timestamp')[:5]
        }
        
        extra_context.update(stats)
        return super().index(request, extra_context)
