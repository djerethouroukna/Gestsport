# payments/urls_api.py - URLs pour l'API REST
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import stripe_views

app_name = 'payments_api'

# Router pour les vues API
router = DefaultRouter()

urlpatterns = [
    # URLs API Stripe
    path('stripe/checkout/<int:reservation_id>/', stripe_views.stripe_payment_checkout, name='stripe_checkout'),
    path('stripe/success/<int:reservation_id>/', stripe_views.stripe_payment_success, name='stripe_success'),
    path('stripe/cancel/<int:reservation_id>/', stripe_views.stripe_payment_cancel, name='stripe_cancel'),
    path('stripe/intent/<int:reservation_id>/', stripe_views.stripe_payment_intent, name='stripe_intent'),
    path('stripe/webhook/', stripe_views.stripe_webhook, name='stripe_webhook'),
    path('stripe/methods/', stripe_views.stripe_payment_methods, name='stripe_methods'),
    path('stripe/fees/', stripe_views.stripe_calculate_fees, name='stripe_fees'),
    path('stripe/status/<int:reservation_id>/', stripe_views.stripe_payment_status, name='stripe_status'),
    path('stripe/refund/<int:reservation_id>/', stripe_views.stripe_refund_payment, name='stripe_refund'),
    path('stripe/history/', stripe_views.stripe_payment_history, name='stripe_history'),
]
