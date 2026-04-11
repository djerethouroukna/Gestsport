# payments/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import patch

from .models import Payment, PaymentMethod, Transaction, PaymentStatus, PaymentMethodType
from .services import PaymentService, PaymentSimulationService
from reservations.models import Reservation
from terrains.models import Terrain

User = get_user_model()


class PaymentServiceTestCase(TestCase):
    """Tests des services de paiement"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
        
        self.terrain = Terrain.objects.create(
            name='Terrain Test',
            terrain_type='football',
            capacity=10,
            price_per_hour=Decimal('5000.00')
        )
        
        self.reservation = Reservation.objects.create(
            user=self.user,
            terrain=self.terrain,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2)
        )
    
    def test_calculate_reservation_amount(self):
        """Test du calcul du montant d'une réservation"""
        amount = PaymentService._calculate_reservation_amount(self.reservation)
        expected = Decimal('10000.00')  # 2 heures * 5000
        self.assertEqual(amount, expected)
    
    def test_create_payment_method(self):
        """Test de création d'un moyen de paiement"""
        payment_method = PaymentService.add_payment_method(
            user=self.user,
            method_type=PaymentMethodType.MOBILE_MONEY,
            provider='Orange',
            identifier='0123456789',
            display_name='Orange ****6789'
        )
        
        self.assertEqual(payment_method.user, self.user)
        self.assertEqual(payment_method.method_type, PaymentMethodType.MOBILE_MONEY)
        self.assertTrue(payment_method.is_default)
        self.assertTrue(payment_method.is_verified)
    
    def test_create_payment_from_reservation(self):
        """Test de création d'un paiement depuis une réservation"""
        payment_method = PaymentService.add_payment_method(
            user=self.user,
            method_type=PaymentMethodType.MOBILE_MONEY,
            provider='Orange',
            identifier='0123456789',
            display_name='Orange ****6789'
        )
        
        payment = PaymentService.create_payment_from_reservation(
            reservation=self.reservation,
            payment_method_id=payment_method.id
        )
        
        self.assertEqual(payment.reservation, self.reservation)
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.amount, Decimal('10000.00'))
        self.assertTrue(payment.is_simulated)
        self.assertEqual(payment.status, PaymentStatus.SIMULATED)
        
        # Vérifier que la réservation est confirmée
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'confirmed')


class PaymentSimulationServiceTestCase(TestCase):
    """Tests du service de simulation"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
        
        self.terrain = Terrain.objects.create(
            name='Terrain Test',
            terrain_type='football',
            capacity=10,
            price_per_hour=Decimal('5000.00')
        )
        
        self.reservation = Reservation.objects.create(
            user=self.user,
            terrain=self.terrain,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2)
        )
        
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            method_type=PaymentMethodType.MOBILE_MONEY,
            provider='Orange',
            identifier='0123456789',
            display_name='Orange ****6789'
        )
    
    def test_generate_transaction_id(self):
        """Test de génération d'ID de transaction"""
        transaction_id = PaymentSimulationService.generate_transaction_id()
        self.assertTrue(transaction_id.startswith('SIM-'))
        self.assertEqual(len(transaction_id), 20)  # SIM-YYYYMMDD-8HEX
    
    def test_generate_otp(self):
        """Test de génération d'OTP"""
        otp = PaymentSimulationService.generate_otp()
        self.assertEqual(otp, '123456')
    
    def test_validate_payment_data(self):
        """Test de validation des données de paiement"""
        # Valid data
        errors = PaymentSimulationService.validate_payment_data(
            self.payment_method, 
            Decimal('10000.00')
        )
        self.assertEqual(len(errors), 0)
        
        # Invalid amount
        errors = PaymentSimulationService.validate_payment_data(
            self.payment_method, 
            Decimal('0')
        )
        self.assertGreater(len(errors), 0)
        
        # Inactive payment method
        self.payment_method.is_active = False
        self.payment_method.save()
        errors = PaymentSimulationService.validate_payment_data(
            self.payment_method, 
            Decimal('10000.00')
        )
        self.assertGreater(len(errors), 0)
    
    @patch('payments.services.NotificationService')
    def test_create_payment_simulation(self, mock_notification):
        """Test de création d'un paiement simulé"""
        payment = PaymentSimulationService.create_payment(
            reservation=self.reservation,
            payment_method=self.payment_method,
            amount=Decimal('10000.00'),
            notes='Test simulation'
        )
        
        self.assertEqual(payment.reservation, self.reservation)
        self.assertEqual(payment.amount, Decimal('10000.00'))
        self.assertTrue(payment.is_simulated)
        self.assertEqual(payment.status, PaymentStatus.SIMULATED)
        
        # Vérifier la transaction
        self.assertIsNotNone(payment.transaction)
        self.assertEqual(payment.transaction.status, PaymentStatus.SIMULATED)
        self.assertTrue(payment.transaction.transaction_id.startswith('SIM-'))
        
        # Vérifier les données de simulation
        self.assertIn('otp', payment.simulation_data)
        self.assertEqual(payment.simulation_data['otp'], '123456')
        
        # Vérifier que la réservation est confirmée
        self.reservation.refresh_from_db()
        self.assertEqual(self.reservation.status, 'confirmed')
        
        # Vérifier la notification
        mock_notification.create_notification.assert_called_once()


class PaymentModelTestCase(TestCase):
    """Tests des modèles de paiement"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role='player'
        )
        
        self.terrain = Terrain.objects.create(
            name='Terrain Test',
            terrain_type='football',
            capacity=10,
            price_per_hour=Decimal('5000.00')
        )
        
        self.reservation = Reservation.objects.create(
            user=self.user,
            terrain=self.terrain,
            start_time=datetime.now() + timedelta(days=1),
            end_time=datetime.now() + timedelta(days=1, hours=2)
        )
    
    def test_payment_properties(self):
        """Test des propriétés du modèle Payment"""
        payment = Payment.objects.create(
            reservation=self.reservation,
            user=self.user,
            amount=Decimal('10000.00'),
            status=PaymentStatus.SIMULATED,
            is_simulated=True
        )
        
        self.assertTrue(payment.is_paid)
        self.assertTrue(payment.can_be_refunded)
    
    def test_reservation_payment_properties(self):
        """Test des propriétés de paiement du modèle Reservation"""
        # Sans paiement
        self.assertFalse(self.reservation.has_payment)
        self.assertFalse(self.reservation.is_paid)
        self.assertIsNone(self.reservation.payment_status)
        self.assertTrue(self.reservation.can_be_paid)
        
        # Avec paiement
        payment = Payment.objects.create(
            reservation=self.reservation,
            user=self.user,
            amount=Decimal('10000.00'),
            status=PaymentStatus.SIMULATED,
            is_simulated=True
        )
        
        self.assertTrue(self.reservation.has_payment)
        self.assertTrue(self.reservation.is_paid)
        self.assertEqual(self.reservation.payment_status, PaymentStatus.SIMULATED)
        self.assertFalse(self.reservation.can_be_paid)
