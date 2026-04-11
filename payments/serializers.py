# payments/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Payment, PaymentMethod, Transaction, Refund, PaymentStatus,
    PaymentMethodType
)
from reservations.models import Reservation

User = get_user_model()


class PaymentMethodSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les moyens de paiement"""
    
    class Meta:
        model = PaymentMethod
        fields = (
            'id', 'method_type', 'provider', 'identifier', 
            'display_name', 'is_default', 'is_active', 'is_verified',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'is_verified', 'created_at', 'updated_at')
    
    def validate_identifier(self, value):
        """Valide l'identifiant selon le type"""
        method_type = self.initial_data.get('method_type')
        
        if method_type == PaymentMethodType.CARD:
            # Validation basique pour carte bancaire
            if not value.isdigit() or len(value) not in [16, 15]:
                raise serializers.ValidationError("Numéro de carte invalide")
        elif method_type == PaymentMethodType.MOBILE_MONEY:
            # Validation pour numéro de téléphone
            if not value.isdigit() or len(value) < 8:
                raise serializers.ValidationError("Numéro de téléphone invalide")
        
        return value


class PaymentMethodCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un moyen de paiement"""
    
    class Meta:
        model = PaymentMethod
        fields = (
            'method_type', 'provider', 'identifier', 'display_name'
        )
    
    def create(self, validated_data):
        user = self.context['request'].user
        from .services import PaymentService
        
        return PaymentService.add_payment_method(
            user=user,
            **validated_data
        )


class TransactionSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les transactions"""
    
    class Meta:
        model = Transaction
        fields = (
            'id', 'transaction_id', 'amount', 'currency', 'status',
            'gateway_response', 'failure_reason', 'processed_at',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'transaction_id', 'gateway_response', 'failure_reason',
            'processed_at', 'created_at', 'updated_at'
        )


class PaymentSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les paiements"""
    transaction = TransactionSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    reservation_details = serializers.SerializerMethodField()
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = (
            'id', 'reservation', 'reservation_details', 'user', 'user_name',
            'amount', 'currency', 'status', 'status_display', 'payment_method',
            'transaction', 'is_simulated', 'simulation_data', 'notes',
            'created_at', 'updated_at', 'paid_at'
        )
        read_only_fields = (
            'id', 'user', 'transaction', 'is_simulated', 'simulation_data',
            'created_at', 'updated_at', 'paid_at'
        )
    
    def get_reservation_details(self, obj):
        """Récupère les détails de la réservation"""
        if obj.reservation:
            return {
                'id': obj.reservation.id,
                'terrain_name': obj.reservation.terrain.name,
                'start_time': obj.reservation.start_time,
                'end_time': obj.reservation.end_time,
                'status': obj.reservation.status
            }
        return None


class PaymentCreateSerializer(serializers.Serializer):
    """Sérialiseur pour créer un paiement"""
    reservation_id = serializers.IntegerField()
    payment_method_id = serializers.IntegerField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_reservation_id(self, value):
        """Valide que la réservation existe et appartient à l'utilisateur"""
        try:
            reservation = Reservation.objects.get(
                id=value, 
                user=self.context['request'].user
            )
            
            # Vérifier qu'il n'y a pas déjà un paiement
            if hasattr(reservation, 'payment'):
                raise serializers.ValidationError("Cette réservation a déjà un paiement")
            
            return value
        except Reservation.DoesNotExist:
            raise serializers.ValidationError("Réservation introuvable")
    
    def validate_payment_method_id(self, value):
        """Valide le moyen de paiement"""
        if value:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=value,
                    user=self.context['request'].user,
                    is_active=True
                )
                return value
            except PaymentMethod.DoesNotExist:
                raise serializers.ValidationError("Moyen de paiement invalide")
        return None
    
    def create(self, validated_data):
        from .services import PaymentService
        
        reservation = Reservation.objects.get(
            id=validated_data['reservation_id']
        )
        
        return PaymentService.create_payment_from_reservation(
            reservation=reservation,
            payment_method_id=validated_data.get('payment_method_id'),
            notes=validated_data.get('notes', '')
        )


class RefundSerializer(serializers.ModelSerializer):
    """Sérialiseur pour les remboursements"""
    payment_details = PaymentSerializer(source='payment', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Refund
        fields = (
            'id', 'payment', 'payment_details', 'amount', 'reason',
            'status', 'status_display', 'refund_transaction',
            'processed_by', 'processed_by_name', 'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'refund_transaction', 'processed_by', 'processed_by_name',
            'created_at', 'updated_at'
        )


class RefundCreateSerializer(serializers.Serializer):
    """Sérialiseur pour créer un remboursement"""
    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    reason = serializers.CharField()
    
    def validate_payment_id(self, value):
        """Valide le paiement"""
        try:
            payment = Payment.objects.get(id=value)
            if not payment.can_be_refunded:
                raise serializers.ValidationError("Ce paiement ne peut pas être remboursé")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Paiement introuvable")
    
    def validate_amount(self, value):
        """Valide le montant du remboursement"""
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être positif")
        return value
    
    def create(self, validated_data):
        from .services import RefundService
        
        payment = Payment.objects.get(id=validated_data['payment_id'])
        
        return RefundService.create_refund(
            payment=payment,
            amount=validated_data['amount'],
            reason=validated_data['reason'],
            processed_by=self.context['request'].user
        )


class PaymentStatisticsSerializer(serializers.Serializer):
    """Sérialiseur pour les statistiques de paiement"""
    total_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    simulated_payments = serializers.IntegerField()
    real_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()


class PaymentMethodSetDefaultSerializer(serializers.Serializer):
    """Sérialiseur pour définir le moyen de paiement par défaut"""
    payment_method_id = serializers.IntegerField()
    
    def validate_payment_method_id(self, value):
        """Valide le moyen de paiement"""
        try:
            payment_method = PaymentMethod.objects.get(
                id=value,
                user=self.context['request'].user
            )
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError("Moyen de paiement introuvable")
    
    def save(self):
        from .services import PaymentService
        
        return PaymentService.set_default_payment_method(
            user=self.context['request'].user,
            payment_method_id=self.validated_data['payment_method_id']
        )


class SimulationOTPVerifySerializer(serializers.Serializer):
    """Sérialiseur pour vérifier l'OTP de simulation"""
    payment_id = serializers.UUIDField()
    otp_code = serializers.CharField(max_length=6)
    
    def validate_otp_code(self, value):
        """Valide le code OTP (toujours 123456 en simulation)"""
        if value != "123456":
            raise serializers.ValidationError("Code OTP invalide")
        return value
    
    def validate_payment_id(self, value):
        """Valide le paiement"""
        try:
            payment = Payment.objects.get(id=value)
            if not payment.is_simulated:
                raise serializers.ValidationError("Ce paiement n'est pas une simulation")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Paiement introuvable")
    
    def save(self):
        """Simule la vérification OTP"""
        payment = Payment.objects.get(id=self.validated_data['payment_id'])
        
        # En simulation, l'OTP est toujours valide
        return {
            'success': True,
            'message': 'Paiement vérifié avec succès',
            'payment': payment
        }
