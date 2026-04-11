from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.http import HttpResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import calendar
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reservations.models import Reservation
from terrains.models import Terrain
from reportlab.lib.colors import HexColor

@login_required
def reports_dashboard(request):
    """
    Vue pour le tableau de bord des rapports avec filtrage
    """
    # Récupérer les paramètres de filtrage
    terrain_id = request.GET.get('terrain')
    period = request.GET.get('period', 'month')  # week, month, year
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    # Base queryset
    reservations = Reservation.objects.filter(
        status__in=['confirmed', 'completed'],
        payment__status__in=['completed', 'paid']
    ).select_related('payment', 'terrain', 'user')
    
    # Appliquer les filtres
    if terrain_id:
        reservations = reservations.filter(terrain_id=terrain_id)
    
    # Filtrage par période
    today = timezone.now().date()
    if start_date:
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        reservations = reservations.filter(start_time__date__gte=start_date)
    else:
        if period == 'week':
            start_date = today - timedelta(days=today.weekday())
            reservations = reservations.filter(start_time__date__gte=start_date)
        elif period == 'month':
            start_date = today.replace(day=1)
            reservations = reservations.filter(start_time__date__gte=start_date)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            reservations = reservations.filter(start_time__date__gte=start_date)
    
    if end_date:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        reservations = reservations.filter(start_time__date__lte=end_date)
    
    # Statistiques générales
    total_reservations = reservations.count()
    total_revenue = reservations.aggregate(
        total=Sum('total_amount')
    )['total'] or Decimal('0')
    
    # Statistiques par terrain
    terrain_stats = []
    for terrain in Terrain.objects.all():
        terrain_reservations = reservations.filter(terrain=terrain)
        terrain_total = terrain_reservations.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        terrain_count = terrain_reservations.count()
        
        if terrain_count > 0:
            terrain_stats.append({
                'terrain': terrain,
                'reservations_count': terrain_count,
                'total_amount': terrain_total,
                'average_amount': terrain_total / terrain_count if terrain_count > 0 else Decimal('0')
            })
    
    # Trier par montant total décroissant
    terrain_stats.sort(key=lambda x: x['total_amount'], reverse=True)
    
    # Réservations détaillées pour le tableau
    detailed_reservations = reservations.select_related('terrain', 'user').order_by('-start_time')
    
    # Statistiques par période
    period_stats = get_period_stats(reservations, period)
    
    # Liste des terrains pour le filtre
    terrains = Terrain.objects.all()
    
    context = {
        'title': 'Rapports',
        'total_reservations': total_reservations,
        'total_revenue': total_revenue,
        'terrain_stats': terrain_stats,
        'detailed_reservations': detailed_reservations,
        'period_stats': period_stats,
        'terrains': terrains,
        'selected_terrain': terrain_id,
        'selected_period': period,
        'start_date': start_date,
        'end_date': end_date,
    }
    
    return render(request, 'reports/rapports.html', context)

def get_period_stats(reservations, period):
    """Calcule les statistiques par période"""
    stats = []
    
    if period == 'week':
        # Statistiques par jour de la semaine
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_reservations = reservations.filter(start_time__date=day)
            day_total = day_reservations.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0')
            
            stats.append({
                'period': day.strftime('%A %d/%m'),
                'reservations_count': day_reservations.count(),
                'total_amount': day_total,
                'percentage_change': 0  # Sera calculé après
            })
    
    elif period == 'month':
        # Statistiques par semaine du mois
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        week_num = 1
        current_week_start = month_start
        
        while current_week_start <= today:
            current_week_end = min(
                current_week_start + timedelta(days=6),
                today
            )
            
            week_reservations = reservations.filter(
                start_time__date__gte=current_week_start,
                start_time__date__lte=current_week_end
            )
            week_total = week_reservations.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0')
            
            stats.append({
                'period': f'Semaine {week_num} ({current_week_start.strftime("%d/%m")} - {current_week_end.strftime("%d/%m")})',
                'reservations_count': week_reservations.count(),
                'total_amount': week_total,
                'percentage_change': 0  # Sera calculé après
            })
            
            current_week_start += timedelta(days=7)
            week_num += 1
    
    elif period == 'year':
        # Statistiques par mois
        today = timezone.now().date()
        year_start = today.replace(month=1, day=1)
        
        for month in range(1, 13):
            if month <= today.month:
                month_start = today.replace(month=month, day=1)
                if month == 12:
                    month_end = today.replace(month=12, day=31)
                else:
                    month_end = today.replace(month=month+1, day=1) - timedelta(days=1)
                
                month_reservations = reservations.filter(
                    start_time__date__gte=month_start,
                    start_time__date__lte=month_end
                )
                month_total = month_reservations.aggregate(
                    total=Sum('total_amount')
                )['total'] or Decimal('0')
                
                stats.append({
                    'period': calendar.month_name[month],
                    'reservations_count': month_reservations.count(),
                    'total_amount': month_total,
                    'percentage_change': 0  # Sera calculé après
                })
    
    # Calculer les pourcentages de changement
    for i, stat in enumerate(stats):
        if i > 0 and stats[i-1]['total_amount'] and stats[i-1]['total_amount'] > 0:
            prev_amount = stats[i-1]['total_amount']
            current_amount = stat['total_amount']
            percentage_change = ((current_amount - prev_amount) / prev_amount) * 100
            stat['percentage_change'] = round(percentage_change, 2)
        else:
            stat['percentage_change'] = 0
    
    return stats

@login_required
def export_pdf(request):
    """
    Exporter les rapports en PDF avec ReportLab - VERSION CORRIGÉE
    """
    from .utils import get_accurate_reservation_stats
    
    print("=== DEBUG PDF START ===")
    
    # Récupérer les paramètres
    terrain_id = request.GET.get('terrain')
    period = request.GET.get('period', 'month')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    print(f"DEBUG PDF: terrain_id={terrain_id}, period={period}, start_date={start_date}, end_date={end_date}")
    
    # Utiliser la fonction unifiée pour des statistiques précises
    stats = get_accurate_reservation_stats(terrain_id, start_date, end_date)
    
    total_reservations = stats['total_reservations']
    total_revenue = stats['total_revenue']
    reservations = stats['reservations']
    completed_payments = stats['completed_payments']
    
    print(f"DEBUG PDF: total_reservations={total_reservations}, total_revenue={total_revenue}")
    print(f"DEBUG PDF: reservations count={reservations.count()}")
    
    # Statistiques par terrain
    terrain_stats = []
    for terrain in Terrain.objects.all():
        terrain_reservations = reservations.filter(terrain=terrain)
        terrain_total = terrain_reservations.aggregate(
            total=Sum('total_amount')
        )['total'] or Decimal('0')
        terrain_count = terrain_reservations.count()
        
        if terrain_count > 0:
            terrain_stats.append({
                'terrain': terrain,
                'reservations_count': terrain_count,
                'total_amount': terrain_total,
                'average_amount': terrain_total / terrain_count if terrain_count > 0 else Decimal('0')
            })
    
    terrain_stats.sort(key=lambda x: x['total_amount'], reverse=True)
    print(f"DEBUG PDF: terrain_stats count={len(terrain_stats)}")
    
    # Réservations détaillées
    detailed_reservations = reservations.select_related('terrain', 'user').order_by('-start_time')
    print(f"DEBUG PDF: detailed_reservations count = {detailed_reservations.count()}")
    
    # Période pour le titre
    period_text = ""
    if period == 'week':
        period_text = "La Semaine"
    elif period == 'month':
        period_text = "Le Mois"
    elif period == 'year':
        period_text = "L'Année"
    
    # Créer le PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="rapports_{period}_{timezone.now().strftime("%Y%m%d")}.pdf"'
    
    # Créer le document PDF
    doc = SimpleDocTemplate(response, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # Style personnalisé pour le titre
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        spaceAfter=10,
        alignment=1,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=1
    )
    
   
    
    # Entête avec logo et nom
    
    # Titre du rapport
    story.append(Paragraph(f"<u>RAPPORTS DES RESERVATIONS : {period_text}</u>", title_style))
    story.append(Spacer(1, 12))
    
    # Informations générales
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        alignment=1
    )
    story.append(Paragraph(f"Généré le {timezone.now().strftime('%d/%m/%Y %H:%M')}", info_style))
    story.append(Spacer(1, 20))
    
    # Statistiques principales
    stats_data = [
        ['Statistiques principales', ''],
        ['Total des réservations', str(total_reservations)],
        ['Revenu total', f'{total_revenue:.2f} F CFA'],
    ]
    
    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2ECC71')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, HexColor('#2ECC71'))
    ]))
    
    story.append(stats_table)
    story.append(Spacer(1, 20))
    
    # Tableau des statistiques par terrain
    if terrain_stats:
        story.append(Paragraph("<u>STATISTIQUES PAR TERRAINS</u>", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        terrain_data = [['Rang', 'Terrain', 'Type', 'Nb Réserv', 'Mnt/Total F CFA', 'Moy/Réserv F CFA']]
        
        for i, stat in enumerate(terrain_stats, 1):
            terrain_data.append([
                str(i),
                stat['terrain'].name,
                stat['terrain'].get_terrain_type_display(),
                str(stat['reservations_count']),
                f'{stat["total_amount"]:.2f} F CFA',
                f'{stat["average_amount"]:.2f} F CFA'
            ])
        
        # Ligne de total
        terrain_data.append([
            'TOTAL',
            '',
            '',
            str(total_reservations),
            f'{total_revenue:.2f} F CFA',
            f'{(total_revenue / total_reservations):.2f} F CFA' if total_reservations > 0 else '0.00 FCFA'
        ])
        
        terrain_table = Table(terrain_data, colWidths=[0.5*inch, 2*inch, 1*inch, 1*inch, 1*inch, 1.2*inch])
        terrain_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2ECC71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#2ECC71')),
            ('FONTSIZE', (0, 1), (-1, -1), 8)
        ]))
        
        story.append(terrain_table)
        story.append(Spacer(1, 20))
    
    # Tableau des réservations détaillées
    if detailed_reservations:
        story.append(Paragraph("<u>DETAIL DES RESERVATIONS</u>", styles['Heading2']))
        story.append(Spacer(1, 12))
        
        reservation_data = [
            ['Date', 'Terrain', 'Client', 'Heure début', 'Heure fin', 'Mnt F CFA', 'Statut']
        ]
        
        for reservation in detailed_reservations:
            reservation_data.append([
                reservation.start_time.strftime('%d/%m/%Y'),
                reservation.terrain.name,
                reservation.user.get_full_name() or reservation.user.username,
                reservation.start_time.strftime('%H:%M'),
                reservation.end_time.strftime('%H:%M'),
                f'{reservation.total_amount:.2f} F CFA',
                reservation.get_status_display()
            ])
        
        reservation_table = Table(reservation_data, colWidths=[0.8*inch, 1.5*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1*inch])
        reservation_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#2ECC71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, HexColor('#2ECC71')),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(reservation_table)
    
    # Construire le PDF
    print("DEBUG PDF: Starting doc.build...")
    try:
        doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
        print("DEBUG PDF: doc.build completed successfully")
    except Exception as e:
        print(f"DEBUG PDF: doc.build failed with error: {e}")
        raise
    
    print("=== DEBUG PDF END ===")
    return response

def add_header_footer(canvas, doc):
    """
    Ajoute l'entête et le pied de page à chaque page du PDF
    """
    # Enregistrer l'état du canvas
    canvas.saveState()
    
    
    # Pied de page
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(inch, 0.5 * inch, f"Généré le {timezone.now().strftime('%d/%m/%Y %H:%M')} - Page {doc.page}")
    canvas.drawRightString(doc.width - inch, 0.9 * inch, "Mnt= Montant, Moy= Moyenne,nb=nombre, Réserv=Réservation")
    canvas.drawRightString(doc.width - inch, 0.5 * inch, "© GestSport - Système de Gestion Sportive")
    
    # Ligne de séparation
    canvas.setStrokeColor(colors.lightgrey)
    canvas.setLineWidth(0.5)
    canvas.line(inch, doc.height - 0.75 * inch, doc.width - inch, doc.height - 0.75 * inch)
    canvas.line(inch, 0.75 * inch, doc.width - inch, 0.75 * inch)
    
    # Restaurer l'état du canvas
    canvas.restoreState()
