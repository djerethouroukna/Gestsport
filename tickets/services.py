# tickets/services.py
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.colors import HexColor
from django.utils import timezone
from django.conf import settings
from django.template import defaultfilters
import os
import pytz
from PIL import Image as PILImage, ImageDraw, ImageFont
from io import BytesIO
from decimal import Decimal
import json


class TicketService:
    """Service pour générer des tickets PDF"""
    
    @staticmethod
    def generate_ticket_pdf(ticket):
        """
        Génère un ticket PDF pour une réservation
        """
        buffer = BytesIO()
        
        # Marges du document
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Couleurs personnalisées
        primary_color = HexColor('#2c3e50')  # Bleu foncé moderne
        accent_color = HexColor('#3498db')   # Bleu clair
        success_color = HexColor('#27ae60')    # Vert
        light_gray = HexColor('#f8f9fa')    # Fond très clair
        
        # Style pour le titre
        title_style = ParagraphStyle(
            'TicketTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=15,
            alignment=TA_CENTER,
            textColor=primary_color,
            fontName='Helvetica-Bold'
        )
        
        # Style pour les sous-titres
        subtitle_style = ParagraphStyle(
            'TicketSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=10,
            alignment=TA_CENTER,
            textColor=accent_color,
            fontName='Helvetica'
        )
        
        # Style pour les informations
        info_style = ParagraphStyle(
            'TicketInfo',
            parent=styles['Normal'],
            fontSize=12,
            spaceAfter=8,
            alignment=TA_LEFT,
            fontName='Helvetica'
        )
        
        # Style pour les labels
        label_style = ParagraphStyle(
            'TicketLabel',
            parent=styles['Normal'],
            fontSize=12,
            fontName='Helvetica-Bold',
            textColor=primary_color
        )
        
        # Contenu du ticket
        story = []
        
        # En-tête
        story.append(Paragraph("TICKET D'ACCÈS", title_style))
        story.append(Paragraph(f"Numéro: {ticket.ticket_number}", subtitle_style))
        story.append(Spacer(1, 20))
        
        # Informations de la réservation
        reservation = ticket.reservation
        
        # Tableau des informations
        info_data = [
            [Paragraph("<b>Type:</b>", label_style), 
             Paragraph("Réservation de terrain" if not reservation.activity else f"Activité: {reservation.activity.get_activity_type_display()}", info_style)],
            
            [Paragraph("<b>Référence:</b>", label_style), 
             Paragraph(f"Réservation #{reservation.id}", info_style)],
            
            [Paragraph("<b>Terrain:</b>", label_style), 
             Paragraph(f"{reservation.terrain.name} ({reservation.terrain.get_terrain_type_display()})", info_style)],
            
            [Paragraph("<b>Date:</b>", label_style), 
             Paragraph(reservation.start_time.astimezone().strftime('%d/%m/%Y'), info_style)],
            
            [Paragraph("<b>Heure:</b>", label_style), 
             Paragraph(f"{reservation.start_time.astimezone().strftime('%H:%M')} - {reservation.end_time.astimezone().strftime('%H:%M')}", info_style)],
            
            [Paragraph("<b>Durée:</b>", label_style), 
             Paragraph(f"{reservation.duration_minutes} minutes", info_style)],
            
            [Paragraph("<b>Coach/Entraîneur:</b>", label_style), 
             Paragraph(reservation.user.get_full_name() or reservation.user.username, info_style)],
        ]
        
        if reservation.activity:
            info_data.append([
                Paragraph("<b>Activité:</b>", label_style), 
                Paragraph(reservation.activity.title, info_style)
            ])
            info_data.append([
                Paragraph("<b>Participants max:</b>", label_style), 
                Paragraph(f"{reservation.activity.max_participants} participants", info_style)
            ])
        
        # Tableau des informations
        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_gray),
            ('TEXTCOLOR', (0, 0), (-1, -1), primary_color),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, primary_color),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # QR Code
        if ticket.qr_code:
            try:
                # Ajouter le QR code
                qr_path = os.path.join(settings.MEDIA_ROOT, ticket.qr_code.name)
                if os.path.exists(qr_path):
                    qr_image = Image(qr_path, width=4*cm, height=4*cm)
                    story.append(qr_image)
                    story.append(Spacer(1, 10))
                    
                    # Instructions QR code
                    qr_instructions = Paragraph(
                        "Scannez ce code QR pour valider votre entrée",
                        ParagraphStyle(
                            'QRInstructions',
                            parent=styles['Normal'],
                            fontSize=10,
                            alignment=TA_CENTER,
                            textColor=accent_color
                        )
                    )
                    story.append(qr_instructions)
            except Exception as e:
                print(f"Erreur ajout QR code: {e}")
        
        story.append(Spacer(1, 20))
        
        # Statut du ticket
        status_text = "VALIDE" if ticket.is_valid else "UTILISÉ"
        status_color = success_color if ticket.is_valid else colors.red
        
        status_table = Table([
            [Paragraph(f"<b>STATUT: {status_text}</b>", 
                      ParagraphStyle(
                          'Status',
                          parent=styles['Normal'],
                          fontSize=14,
                          alignment=TA_CENTER,
                          textColor=status_color,
                          fontName='Helvetica-Bold'
                      ))]
        ], colWidths=[16*cm])
        
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), light_gray),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 2, status_color),
        ]))
        
        story.append(status_table)
        story.append(Spacer(1, 20))
        
        # Informations importantes
        important_info = [
            "• Ce ticket est personnel et incessible",
            "• Présentez ce ticket à l'entrée",
            "• Le QR code sera scanné pour validation",
            "• Une fois validé, le ticket ne peut être réutilisé"
        ]
        
        for info in important_info:
            story.append(Paragraph(info, info_style))
        
        story.append(Spacer(1, 15))
        
        # Pied de page
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.gray
        )
        
        story.append(Paragraph(
            f"Généré le {timezone.now().strftime('%d/%m/%Y %H:%M')} - GestSport Platform",
            footer_style
        ))
        
        # Générer le PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer

    @staticmethod
    def create_custom_qr_pixel(ticket):
        """Crée un QR code simple sans cadres décoratifs"""
        
        # Dimensions
        width, height = 600, 600
        
        # Image de base
        img = PILImage.new('RGB', (width, height), color='white')
        
        # QR code simple et centré
        qr_size = 500
        qr_x = (width - qr_size) // 2
        qr_y = (height - qr_size) // 2
        
        # Générer le QR code
        try:
            import qrcode
            
            # Données du ticket
            ticket_data = {
                'ticket_number': ticket.ticket_number,
                'terrain_name': ticket.reservation.terrain.name,
                'date_formatted': ticket.reservation.start_time.strftime('%d/%m/%Y %H:%M'),
                'duration_minutes': str(ticket.reservation.duration_minutes),
                'user_name': ticket.reservation.user.get_full_name() or ticket.reservation.user.username,
                'is_valid': ticket.is_valid
            }
            
            # Générer QR code
            qr = qrcode.QRCode(
                version=5,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=15,
                border=2,
            )
            qr.add_data(json.dumps(ticket_data, separators=(',', ':')))
            qr.make(fit=True)
            
            # Créer et redimensionner le QR code
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((qr_size, qr_size), PILImage.LANCZOS)
            
            # Intégrer le QR code (centré)
            img.paste(qr_img, (qr_x, qr_y))
            
        except ImportError:
            print(" qrcode non installé")
        
        return img
