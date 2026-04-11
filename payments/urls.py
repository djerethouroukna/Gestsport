# payments/urls.py - URLs pour les templates et vues web
from django.urls import path
from . import views
from . import views_invoice
from . import stripe_views

app_name = 'payments'

urlpatterns = [
    # URLs principales (templates)
    path('list/', views.payment_list, name='payment-list'),
    path('admin/list/', views.admin_payment_list, name='admin_payment_list'),
    path('detail/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('checkout/', views.payment_checkout, name='checkout'),
    path('success/', views.payment_success, name='success'),
    path('cancel/', views.payment_cancel, name='cancel'),
    
    # URLs Stripe pour les templates
    path('stripe/checkout/<int:reservation_id>/', stripe_views.stripe_payment_checkout, name='stripe_checkout'),
    path('stripe/success/<int:reservation_id>/', stripe_views.stripe_payment_success, name='stripe_success'),
    path('stripe/cancel/<int:reservation_id>/', stripe_views.stripe_payment_cancel, name='stripe_cancel'),
    
    # Webhook Stripe (doit être accessible publiquement)
    path('stripe/webhook/', stripe_views.stripe_webhook, name='stripe_webhook'),
    
    # URLs pour les factures
    path('facture/<str:invoice_number>/', views_invoice.invoice_detail, name='invoice_detail'),
    path('facture/<str:invoice_number>/download/', views_invoice.invoice_download, name='invoice_download'),
    path('mes-factures/', views_invoice.invoice_list, name='invoice_list'),
    
    # URLs admin pour les factures
    path('admin/factures/', views_invoice.admin_invoice_list, name='admin_invoice_list'),
    path('admin/facture/<str:invoice_number>/regenerate/', views_invoice.admin_regenerate_invoice, name='admin_regenerate_invoice'),
    path('admin/facture/<str:invoice_number>/resend/', views_invoice.admin_resend_invoice, name='admin_resend_invoice'),
    
    # URLs admin pour les paiements
    path('admin/payment/<uuid:payment_id>/delete/', views.admin_delete_payment, name='admin_delete_payment'),
]
