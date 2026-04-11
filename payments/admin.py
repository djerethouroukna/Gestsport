# payments/admin.py
from django.contrib import admin
from .models import Payment, PaymentMethod, Transaction, Refund, PaymentSettings


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('user', 'method_type', 'provider', 'display_name', 'is_default', 'is_active', 'created_at')
    list_filter = ('method_type', 'provider', 'is_default', 'is_active', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'provider', 'display_name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_id', 'amount', 'currency', 'status', 'payment_method', 'created_at')
    list_filter = ('status', 'currency', 'payment_method__method_type', 'created_at')
    search_fields = ('transaction_id', 'payment_method__identifier')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'transaction_id', 'created_at', 'updated_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'user', 'amount', 'currency', 'status', 'is_simulated', 'payment_method', 'created_at')
    list_filter = ('status', 'is_simulated', 'currency', 'payment_method__method_type', 'created_at')
    search_fields = ('reservation__id', 'user__email', 'user__first_name', 'user__last_name', 'transaction__transaction_id')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'paid_at')
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('reservation', 'user', 'amount', 'currency', 'status')
        }),
        ('Paiement', {
            'fields': ('payment_method', 'transaction', 'is_simulated')
        }),
        ('Détails', {
            'fields': ('notes', 'simulation_data')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'amount', 'reason', 'status', 'processed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__reservation__id', 'payment__user__email', 'reason')
    ordering = ('-created_at',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    list_display = ('key', 'description', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('key', 'description')
    ordering = ('key',)
