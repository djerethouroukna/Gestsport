# payments/views_invoice.py - Vues pour les factures
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, Http404, FileResponse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum, Q
from django.urls import reverse
from django.conf import settings

from reservations.models import Reservation
from payments.models import Payment, Invoice, InvoiceStatus
from .invoice_service import InvoiceService
import os
import logging

logger = logging.getLogger(__name__)


@login_required
def invoice_detail(request, invoice_number):
    """
    Affiche les détails d'une facture
    """
    try:
        invoice = get_object_or_404(
            Invoice.objects.select_related('user', 'reservation', 'reservation__terrain'),
            invoice_number=invoice_number
        )
        
        # Vérifier les permissions
        if invoice.user != request.user and not request.user.is_staff:
            raise Http404("Facture non trouvée")
        
        context = {
            'invoice': invoice,
            'company_info': InvoiceService.get_company_info(),
        }
        
        return render(request, 'payments/invoice_detail.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage de la facture {invoice_number}: {e}")
        messages.error(request, "Une erreur est survenue lors de l'affichage de la facture.")
        return redirect('dashboard_admin')


@login_required
def invoice_download(request, invoice_number):
    """
    Télécharge le PDF d'une facture
    """
    try:
        invoice = get_object_or_404(
            Invoice.objects.select_related('user'),
            invoice_number=invoice_number
        )
        
        # Vérifier les permissions
        if invoice.user != request.user and not request.user.is_staff:
            raise Http404("Facture non trouvée")
        
        # Vérifier si le PDF existe
        if not invoice.pdf_file:
            # Générer le PDF si nécessaire
            if not InvoiceService.generate_pdf(invoice):
                messages.error(request, "Impossible de générer le PDF de la facture.")
                return redirect('payments:invoice_detail', invoice_number=invoice_number)
        
        # Servir le fichier
        if os.path.exists(invoice.pdf_file.path):
            response = FileResponse(
                open(invoice.pdf_file.path, 'rb'),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="facture_{invoice.invoice_number}.pdf"'
            return response
        else:
            messages.error(request, "Le fichier PDF n'est pas disponible.")
            return redirect('payments:invoice_detail', invoice_number=invoice_number)
            
    except Exception as e:
        logger.error(f"Erreur lors du téléchargement de la facture {invoice_number}: {e}")
        messages.error(request, "Une erreur est survenue lors du téléchargement.")
        return redirect('dashboard_admin')


@login_required
def invoice_list(request):
    """
    Liste des factures de l'utilisateur
    """
    try:
        # Récupérer les factures de l'utilisateur
        invoices = Invoice.objects.filter(
            user=request.user
        ).select_related(
            'reservation',
            'reservation__terrain'
        ).order_by('-created_at')
        
        # Filtrage
        status_filter = request.GET.get('status')
        year_filter = request.GET.get('year')
        
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        
        if year_filter:
            invoices = invoices.filter(created_at__year=year_filter)
        
        # Pagination
        paginator = Paginator(invoices, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Statistiques
        stats = InvoiceService.get_invoice_stats(request.user)
        
        # Années disponibles pour le filtre
        available_years = Invoice.objects.filter(
            user=request.user
        ).dates('created_at', 'year', order='DESC')
        
        context = {
            'page_obj': page_obj,
            'stats': stats,
            'available_years': available_years,
            'current_status': status_filter,
            'current_year': year_filter,
        }
        
        return render(request, 'payments/invoice_list.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage de la liste des factures: {e}")
        messages.error(request, "Une erreur est survenue lors de l'affichage de vos factures.")
        return redirect('reservations_admin:admin_dashboard')


@staff_member_required
def admin_invoice_list(request):
    """
    Liste des factures pour l'administration
    """
    try:
        # Récupérer toutes les factures
        invoices = Invoice.objects.select_related(
            'user',
            'reservation',
            'reservation__terrain'
        ).order_by('-created_at')
        
        # Filtrage
        status_filter = request.GET.get('status')
        user_filter = request.GET.get('user')
        year_filter = request.GET.get('year')
        
        if status_filter:
            invoices = invoices.filter(status=status_filter)
        
        if user_filter:
            invoices = invoices.filter(
                Q(user__email__icontains=user_filter) |
                Q(user__first_name__icontains=user_filter) |
                Q(user__last_name__icontains=user_filter)
            )
        
        if year_filter:
            invoices = invoices.filter(created_at__year=year_filter)
        
        # Pagination
        paginator = Paginator(invoices, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Statistiques globales
        stats = InvoiceService.get_invoice_stats()
        
        # Années disponibles pour le filtre
        available_years = Invoice.objects.dates('created_at', 'year', order='desc')
        
        context = {
            'page_obj': page_obj,
            'stats': stats,
            'available_years': available_years,
            'current_status': status_filter,
            'current_user': user_filter,
            'current_year': year_filter,
        }
        
        return render(request, 'payments/admin_invoice_list.html', context)
        
    except Exception as e:
        logger.error(f"Erreur lors de l'affichage de la liste admin des factures: {e}")
        messages.error(request, "Une erreur est survenue.")
        return redirect('admin:index')


@staff_member_required
def admin_regenerate_invoice(request, invoice_number):
    """
    Régénère le PDF d'une facture (admin)
    """
    try:
        invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
        
        # Régénérer le PDF
        if InvoiceService.generate_pdf(invoice):
            messages.success(request, f"Le PDF de la facture {invoice_number} a été régénéré avec succès.")
        else:
            messages.error(request, "Erreur lors de la régénération du PDF.")
        
        return redirect('payments:admin_invoice_list')
        
    except Exception as e:
        logger.error(f"Erreur lors de la régénération de la facture {invoice_number}: {e}")
        messages.error(request, "Une erreur est survenue.")
        return redirect('payments:admin_invoice_list')


@staff_member_required
def admin_resend_invoice(request, invoice_number):
    """
    Renvoie une facture par email (admin)
    """
    try:
        invoice = get_object_or_404(Invoice, invoice_number=invoice_number)
        
        # Envoyer l'email
        if InvoiceService.send_invoice_email(invoice):
            messages.success(request, f"La facture {invoice_number} a été renvoyée par email.")
        else:
            messages.error(request, "Erreur lors de l'envoi de l'email.")
        
        return redirect('payments:admin_invoice_list')
        
    except Exception as e:
        logger.error(f"Erreur lors du renvoi de la facture {invoice_number}: {e}")
        messages.error(request, "Une erreur est survenue.")
        return redirect('payments:admin_invoice_list')
