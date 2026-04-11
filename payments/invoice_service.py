# payments/invoice_service.py
import os
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.urls import reverse
from django.db import models
import tempfile
import logging

from .models import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service pour la génération et gestion des factures"""
    
    @staticmethod
    def create_invoice_for_payment(payment):
        """
        Crée une facture pour un paiement réussi
        """
        try:
            # Vérifier si une facture existe déjà
            if Invoice.objects.filter(payment=payment).exists():
                logger.info(f"Facture existe déjà pour le paiement {payment.id}")
                return None
            
            # Créer la facture
            invoice = Invoice.objects.create(
                reservation=payment.reservation,
                user=payment.user,
                payment=payment,
                amount_ht=payment.amount / Decimal('1.20'),  # TVA 20%
                vat_rate=Decimal('20.00'),
                due_date=timezone.now().date(),  # Payée immédiatement
                status=InvoiceStatus.PAID,
                paid_date=timezone.now().date()
            )
            
            logger.info(f"Facture {invoice.invoice_number} créée pour le paiement {payment.id}")
            
            # Générer le PDF
            InvoiceService.generate_pdf(invoice)
            
            # Envoyer par email
            InvoiceService.send_invoice_email(invoice)
            
            return invoice
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la facture: {e}")
            return None
    
    @staticmethod
    def generate_pdf(invoice):
        """
        Génère le fichier PDF de la facture avec ReportLab
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib.colors import HexColor
            from io import BytesIO
            
            # Configuration du document
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
            
            # Styles
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor=colors.HexColor('#2c3e50')
            )
            
            heading_style = ParagraphStyle(
                'CustomHeading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor=colors.HexColor('#2c3e50')
            )
            
            normal_style = styles['Normal']
            
            # Contenu du document
            story = []
            
            # En-tête
            story.append(Paragraph("FACTURE", title_style))
            story.append(Spacer(1, 0.3*cm))
            
            # Informations de l'entreprise
            company_info = InvoiceService.get_company_info()
            company_data = [
                [Paragraph(f"<b>{company_info['name']}</b>", normal_style)],
                [Paragraph(company_info['address'], normal_style)],
                [Paragraph(f"Tél: {company_info['phone']}", normal_style)],
                [Paragraph(f"Email: {company_info['email']}", normal_style)],
                [Paragraph(f"SIRET: {company_info['siret']}", normal_style)],
                [Paragraph(f"TVA: {company_info['tva_number']}", normal_style)],
            ]
            
            company_table = Table(company_data, colWidths=[15*cm])
            company_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            
            story.append(company_table)
            story.append(Spacer(1, 0.5*cm))
            
            # Informations de la facture
            invoice_data = [
                ['Numéro de facture:', invoice.invoice_number],
                ['Date de facture:', invoice.invoice_date.strftime('%d/%m/%Y')],
                ['Date de paiement:', invoice.paid_date.strftime('%d/%m/%Y') if invoice.paid_date else ''],
                ['Client:', invoice.user.get_full_name() or invoice.user.email],
                ['Email client:', invoice.user.email],
            ]
            
            info_table = Table(invoice_data, colWidths=[4*cm, 8*cm])
            info_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#ffffff')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ]))
            
            story.append(info_table)
            story.append(Spacer(1, 0.5*cm))
            
            # Détails de la réservation
            story.append(Paragraph("Détails de la réservation", heading_style))
            story.append(Spacer(1, 0.2*cm))
            
            reservation_data = [
                ['Terrain:', invoice.reservation.terrain.name],
                ['Type:', invoice.reservation.terrain.terrain_type],
                ['Date:', invoice.reservation.start_time.strftime('%d/%m/%Y')],
                ['Heure:', f"{invoice.reservation.start_time.strftime('%H:%M')} - {invoice.reservation.end_time.strftime('%H:%M')}"],
                ['Durée:', f"{invoice.reservation.duration} heures"],
            ]
            
            reservation_table = Table(reservation_data, colWidths=[4*cm, 8*cm])
            reservation_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (1, 0), (1, -1), colors.HexColor('#ffffff')),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
            ]))
            
            story.append(reservation_table)
            story.append(Spacer(1, 0.5*cm))
            
            # Détails financiers
            story.append(Paragraph("Détails financiers", heading_style))
            story.append(Spacer(1, 0.2*cm))
            
            financial_data = [
                ['Description', 'Quantité', 'Prix unitaire HT', 'Total HT'],
                [f"Location {invoice.reservation.terrain.name}", '1', f"{invoice.amount_ht:.2f} €", f"{invoice.amount_ht:.2f} €"],
                ['', '', '', ''],
                ['TVA (20%)', '', '', f"{invoice.vat_amount:.2f} €"],
                ['', '', '', ''],
                ['TOTAL TTC', '', '', f"<b>{invoice.amount_ttc:.2f} €</b>"],
            ]
            
            financial_table = Table(financial_data, colWidths=[6*cm, 2*cm, 3*cm, 3*cm])
            financial_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
                ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6')),
                ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#f8f9fa')),
                ('BACKGROUND', (3, 3), (-1, 3), colors.HexColor('#e9ecef')),
                ('TEXTCOLOR', (3, 3), (-1, 3), colors.HexColor('#2c3e50')),
            ]))
            
            story.append(financial_table)
            story.append(Spacer(1, 1*cm))
            
            # Pied de page
            footer_text = f"""
            <br/><br/>
            <center>
                <font size="8" color="#666">
                    GestSport - {company_info['address']}<br/>
                    SIRET: {company_info['siret']} - TVA: {company_info['tva_number']}<br/>
                    Email: {company_info['email']} - Tel: {company_info['phone']}<br/>
                    Facture payée électroniquement le {invoice.paid_date.strftime('%d/%m/%Y')} si applicable.
                </font>
            </center>
            """
            
            story.append(Paragraph(footer_text, normal_style))
            
            # Générer le PDF
            doc.build(story)
            
            # Sauvegarder le fichier
            pdf_value = buffer.getvalue()
            buffer.close()
            
            filename = f"facture_{invoice.invoice_number.replace('-', '_')}.pdf"
            invoice.pdf_file.save(filename, pdf_value, save=True)
            
            logger.info(f"PDF généré pour la facture {invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération PDF: {e}")
            return False
    
    @staticmethod
    def send_invoice_email(invoice):
        """
        Envoie la facture par email
        """
        try:
            from django.core.mail import EmailMessage
            from django.contrib.sites.shortcuts import get_current_site
            
            site = get_current_site()
            
            # Sujet et contenu
            subject = f"Facture {invoice.invoice_number} - GestSport"
            
            html_content = render_to_string('payments/invoice_email.html', {
                'invoice': invoice,
                'site': site,
                'download_url': f"https://{site.domain}{invoice.get_absolute_url()}"
            })
            
            # Créer l'email
            email = EmailMessage(
                subject=subject,
                body=html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[invoice.user.email],
            )
            email.content_subtype = "html"
            
            # Attacher le PDF
            if invoice.pdf_file:
                email.attach_file(
                    invoice.pdf_file.path,
                    f"facture_{invoice.invoice_number}.pdf",
                    'application/pdf'
                )
            
            # Envoyer
            email.send()
            
            # Marquer comme envoyée
            invoice.mark_as_sent()
            
            logger.info(f"Email envoyé pour la facture {invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi email: {e}")
            return False
    
    @staticmethod
    def get_company_info():
        """
        Retourne les informations de l'entreprise
        """
        return {
            'name': 'GestSport',
            'address': '123 Rue du Sport, 75001 Paris, France',
            'phone': '+235 63205512',
            'email': 'contact@gestsport.com',
            'siret': '12345678901234',
            'tva_number': 'FR12345678901',
            'website': 'https://gestsport.com',
            'logo_url': settings.STATIC_URL + 'images/logo.png'
        }
    
    @staticmethod
    def get_invoice_stats(user=None):
        """
        Retourne les statistiques des factures
        """
        queryset = Invoice.objects.all()
        if user:
            queryset = queryset.filter(user=user)
        
        return {
            'total_count': queryset.count(),
            'total_amount': queryset.aggregate(
                total=models.Sum('amount_ttc')
            )['total'] or Decimal('0'),
            'paid_count': queryset.filter(status=InvoiceStatus.PAID).count(),
            'sent_count': queryset.filter(sent_by_email=True).count(),
            'overdue_count': queryset.filter(status=InvoiceStatus.OVERDUE).count(),
        }
