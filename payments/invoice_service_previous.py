from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.utils import timezone
from django.conf import settings
import os
from io import BytesIO
from decimal import Decimal

class InvoiceService:
    """Service pour générer des factures PDF avec mise en page structurée Platypus"""
    
    @staticmethod
    def generate_invoice_pdf(reservation, payment=None):
        """
        Génère une facture PDF pour une réservation avec mise en page structurée
        """
        buffer = BytesIO()
        
        # Définir les marges du document explicitement
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Style pour le titre FACTURE
        title_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        # Style pour les sous-titres
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            textColor=colors.black,
            fontName='Helvetica-Bold'
        )
        
        # Style pour le texte normal avec retour à la ligne automatique
        normal_style = ParagraphStyle(
            'NormalText',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=3,
            alignment=TA_LEFT,
            textColor=colors.black,
            fontName='Helvetica'
        )
        
        story = []
        
        # En-tête avec FACTURE
        story.append(Paragraph("FACTURE", title_style))
        story.append(Spacer(1, 15))
        
        # Données de la facture
        invoice_number = f"INV-{reservation.id:06d}-{timezone.now().strftime('%Y%m%d')}"
        invoice_date = timezone.now().strftime('%d/%m/%Y')
        
        # Tableau structuré à deux colonnes pour l'en-tête
        header_data = [
            [
                # Colonne gauche - Informations client/facture
                [
                    Paragraph(f"<b>Facture N°:</b> {invoice_number}", normal_style),
                    Paragraph(f"<b>Date:</b> {invoice_date}", normal_style),
                    Paragraph(f"<b>Client:</b> {reservation.user.get_full_name()}", normal_style),
                    Paragraph(f"<b>Téléphone:</b> {reservation.user.phone or 'Non renseigné'}", normal_style),
                    Paragraph(f"<b>Email:</b> {reservation.user.email}", normal_style),
                ],
                
                # Colonne droite - Informations entreprise
                [
                    Paragraph("<b>GESTSPORT</b>", normal_style),
                    Paragraph("Centre Sportif", normal_style),
                    Paragraph("N'Djamena, Tchad", normal_style),
                    Paragraph("Tél: (+235) 63205512/98901569", normal_style),
                    Paragraph("Email: contact@gestsport.com", normal_style),
                ]
            ]
        ]
        
        # Définir explicitement la largeur des colonnes
        header_table = Table(header_data, colWidths=[7.5*inch, 2.5*inch])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical explicite
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
        ]))
        
        story.append(header_table)
        story.append(Spacer(1, 20))
        
        # Détails de la réservation
        story.append(Paragraph("Détails de la réservation", subtitle_style))
        
        # Calcul de la durée
        from decimal import Decimal
        duration = Decimal(reservation.duration_minutes) / Decimal('60')
        unit_price = reservation.terrain.price_per_hour
        total_amount = unit_price * duration
        
        # Tableau des détails avec Paragraph pour retour à la ligne automatique
        details_data = [
            [
                Paragraph("<b>Terrain</b>", normal_style),
                Paragraph(reservation.terrain.name, normal_style)
            ],
            [
                Paragraph("<b>Type</b>", normal_style),
                Paragraph(reservation.terrain.get_terrain_type_display(), normal_style)
            ],
            [
                Paragraph("<b>Date</b>", normal_style),
                Paragraph(reservation.start_time.strftime('%d/%m/%Y'), normal_style)
            ],
            [
                Paragraph("<b>Heure de début</b>", normal_style),
                Paragraph(reservation.start_time.strftime('%H:%M'), normal_style)
            ],
            [
                Paragraph("<b>Heure de fin</b>", normal_style),
                Paragraph(reservation.end_time.strftime('%H:%M'), normal_style)
            ],
            [
                Paragraph("<b>Durée</b>", normal_style),
                Paragraph(f"{duration} heure(s)", normal_style)
            ],
        ]
        
        # Largeur de colonnes explicite pour les détails
        details_table = Table(details_data, colWidths=[2.5*inch, 4.5*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Tableau des prix
        story.append(Paragraph("Récapitulatif des prix", subtitle_style))
        
        # Calcul des taxes
        tax_rate = Decimal('0.18')  # 18% de TVA
        tax_amount = total_amount * tax_rate
        subtotal = total_amount
        total_with_tax = subtotal + tax_amount
        
        # Tableau des prix avec Paragraph pour retour à la ligne automatique
        price_data = [
            [
                Paragraph("<b>Description</b>", normal_style),
                Paragraph("<b>Quantité</b>", normal_style),
                Paragraph("<b>Prix unitaire</b>", normal_style),
                Paragraph("<b>Total</b>", normal_style)
            ],
            [
                Paragraph(f"Location terrain {reservation.terrain.get_terrain_type_display()} - {reservation.terrain.name}", normal_style),
                Paragraph(f"{duration}h", normal_style),
                Paragraph(f"{unit_price} FCFA", normal_style),
                Paragraph(f"{total_amount} FCFA", normal_style)
            ],
            [
                Paragraph("", normal_style),
                Paragraph("", normal_style),
                Paragraph("Sous-total", normal_style),
                Paragraph(f"{subtotal} FCFA", normal_style)
            ],
            [
                Paragraph("", normal_style),
                Paragraph("", normal_style),
                Paragraph(f"TVA ({tax_rate*100}%)", normal_style),
                Paragraph(f"{tax_amount} FCFA", normal_style)
            ],
            [
                Paragraph("", normal_style),
                Paragraph("", normal_style),
                Paragraph("<b>TOTAL</b>", normal_style),
                Paragraph(f"<b>{total_with_tax} FCFA</b>", normal_style)
            ],
        ]
        
        # Largeur de colonnes explicite pour les prix
        price_table = Table(price_data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
        price_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(price_table)
        
        # Informations de paiement si disponible
        if payment:
            story.append(Spacer(1, 20))
            story.append(Paragraph("Informations de paiement", subtitle_style))
            
            # Tableau de paiement avec Paragraph
            payment_data = [
                [
                    Paragraph("<b>Statut du paiement</b>", normal_style),
                    Paragraph("Payé", normal_style)
                ],
                [
                    Paragraph("<b>Méthode de paiement</b>", normal_style),
                    Paragraph(payment.get_payment_method_display(), normal_style)
                ],
                [
                    Paragraph("<b>Date de paiement</b>", normal_style),
                    Paragraph(payment.created_at.strftime('%d/%m/%Y %H:%M'), normal_style)
                ],
                [
                    Paragraph("<b>ID de transaction</b>", normal_style),
                    Paragraph(payment.transaction_id or "N/A", normal_style)
                ],
            ]
            
            # Largeur de colonnes explicite pour le paiement
            payment_table = Table(payment_data, colWidths=[3*inch, 3*inch])
            payment_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Alignement vertical
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            story.append(payment_table)
        
        # Pied de page
        story.append(Spacer(1, 30))
        
        footer_text = """<b>Mentions légales:</b><br/>
En cas de retard de paiement, une pénalité de 10% sera appliquée.<br/>
Toute réclamation doit être faite dans un délai de 8 jours après la date de facturation.<br/><br/>
Merci pour votre confiance ! Cette facture est générée automatiquement par GESTSPORT."""
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.black,
            fontName='Helvetica'
        )
        story.append(Paragraph(footer_text, footer_style))
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer, invoice_number
    
    @staticmethod
    def save_invoice_to_file(reservation, payment=None):
        """
        Sauvegarde la facture dans un fichier et retourne le chemin
        """
        buffer, invoice_number = InvoiceService.generate_invoice_pdf(reservation, payment)
        
        # Créer le répertoire des factures s'il n'existe pas
        invoices_dir = os.path.join(settings.MEDIA_ROOT, 'invoices')
        os.makedirs(invoices_dir, exist_ok=True)
        
        # Nom du fichier
        filename = f"{invoice_number}.pdf"
        filepath = os.path.join(invoices_dir, filename)
        
        # Sauvegarder le fichier
        with open(filepath, 'wb') as f:
            f.write(buffer.getvalue())
        
        return filepath, filename
