# payments/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import Sum, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Payment, PaymentMethod, Refund, PaymentStatus
from .serializers import (
    PaymentSerializer, PaymentCreateSerializer, PaymentMethodSerializer,
    PaymentMethodCreateSerializer, RefundSerializer, RefundCreateSerializer,
    PaymentStatisticsSerializer, PaymentMethodSetDefaultSerializer,
    SimulationOTPVerifySerializer
)
from .services import PaymentService, RefundService
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from reservations.models import Reservation
from django.contrib.auth.decorators import login_required

User = get_user_model()


@login_required
def payment_list(request):
    """Vue template pour l'historique des paiements"""
    user = request.user
    
    if user.role == 'admin':
        # Les admins voient tous les paiements
        payments = Payment.objects.all().order_by('-created_at')
        template_name = 'payments/admin_payment_list.html'
        
        # Statistiques pour admin
        total_payments = payments.count()
        completed_payments = payments.filter(status__in=['completed', 'simulated']).count()
        total_amount = payments.filter(status__in=['completed', 'simulated']).aggregate(total=Sum('amount'))['total'] or 0
        success_rate = round((completed_payments / total_payments) * 100, 1) if total_payments > 0 else 0
        completed_percentage = round((completed_payments / total_payments) * 100, 1) if total_payments > 0 else 0
        
        context = {
            'payments': payments,
            'total_payments': total_payments,
            'completed_payments': completed_payments,
            'total_amount': total_amount,
            'success_rate': success_rate,
            'completed_percentage': completed_percentage,
        }
        
    elif user.role == 'coach':
        # Les coachs voient seulement leurs paiements
        payments = Payment.objects.filter(user=user).order_by('-created_at')
        template_name = 'payments/coach_payment_list.html'
        
        # Statistiques pour coach
        total_payments = payments.count()
        completed_payments = payments.filter(status__in=['completed', 'simulated']).count()
        completed_percentage = round((completed_payments / total_payments) * 100, 1) if total_payments > 0 else 0
        
        # Dernier paiement
        last_payment = payments.first()
        last_payment_date = last_payment.created_at if last_payment else None
        last_payment_amount = last_payment.amount if last_payment else 0
        
        context = {
            'payments': payments,
            'total_payments': total_payments,
            'completed_payments': completed_payments,
            'completed_percentage': completed_percentage,
            'last_payment_date': last_payment_date,
            'last_payment_amount': last_payment_amount,
        }
        
    else:  # player
        # Les joueurs voient uniquement leurs paiements
        payments = Payment.objects.filter(user=user).order_by('-created_at')
        template_name = 'payments/payment_list.html'
        
        context = {'payments': payments}
    
    return render(request, template_name, context)


@login_required
def admin_payment_list(request):
    """Vue admin pour voir tous les paiements avec filtrage par coach"""
    if request.user.role != 'admin':
        messages.error(request, 'Accès refusé. Réservé aux administrateurs.')
        return redirect('payments:payment_list')
    
    # Récupérer tous les coaches pour le filtrage
    coaches = User.objects.filter(role='coach')
    
    # Filtrage par coach si spécifié
    coach_filter = request.GET.get('coach')
    if coach_filter:
        payments = Payment.objects.filter(user_id=coach_filter).order_by('-created_at')
    else:
        payments = Payment.objects.all().order_by('-created_at')
    
    # Statistiques
    total_payments = payments.count()
    completed_payments = payments.filter(status__in=['completed', 'simulated']).count()
    total_amount = payments.filter(status__in=['completed', 'simulated']).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calcul du taux de succès et pourcentage complété
    success_rate = 0
    completed_percentage = 0
    if total_payments > 0:
        success_rate = round((completed_payments / total_payments) * 100, 1)
        completed_percentage = round((completed_payments / total_payments) * 100, 1)
    
    # Debug prints détaillés
    print(f"DEBUG admin_payment_list:")
    print(f"  - coach_filter: {coach_filter}")
    print(f"  - payments count: {payments.count()}")
    print(f"  - total_payments: {total_payments}")
    print(f"  - completed_payments: {completed_payments}")
    print(f"  - total_amount: {total_amount}")
    print(f"  - success_rate: {success_rate}")
    print(f"  - completed_percentage: {completed_percentage}")
    
    # Vérifier les paiements individuellement
    for i, payment in enumerate(payments[:5]):  # Premier 5 paiements
        print(f"  - Payment {i+1}: id={payment.id}, amount={payment.amount}, status={payment.status}")
    
    context = {
        'payments': payments,
        'coaches': coaches,
        'selected_coach': coach_filter,
        'total_payments': total_payments,
        'completed_payments': completed_payments,
        'total_amount': total_amount,
        'success_rate': success_rate,
        'completed_percentage': completed_percentage,
    }
    
    return render(request, 'payments/admin_payment_list.html', context)


@login_required
def payment_detail(request, payment_id):
    """Vue pour les détails d'un paiement spécifique"""
    try:
        payment = Payment.objects.get(id=payment_id)
        
        # Vérification des permissions
        if request.user.role == 'admin':
            # Admin peut voir tous les paiements
            pass
        elif request.user.role == 'coach':
            # Coach peut voir seulement ses paiements
            if payment.user != request.user:
                messages.error(request, 'Accès refusé.')
                return redirect('payments:payment_list')
        else:  # player
            # Joueur peut voir seulement ses paiements
            if payment.user != request.user:
                messages.error(request, 'Accès refusé.')
                return redirect('payments:payment_list')
        
        return render(request, 'payments/payment_detail.html', {'payment': payment})
        
    except Payment.DoesNotExist:
        messages.error(request, 'Paiement introuvable.')
        return redirect('payments:payment_list')


@login_required
def payment_checkout(request):
    """Vue template pour le checkout (redirigé vers Stripe)"""
    # Cette vue est maintenant gérée dans reservations/views.py
    # Gardée pour compatibilité
    messages.info(request, 'Veuillez utiliser le système de paiement Stripe.')
    return redirect('reservations:reservation_list')


@login_required
def payment_success(request):
    """Vue template pour le succès de paiement"""
    # Cette vue est maintenant gérée dans reservations/views.py
    # Gardée pour compatibilité
    messages.success(request, 'Paiement effectué avec succès!')
    return redirect('reservations:reservation_list')


@login_required
def payment_cancel(request):
    """Vue template pour l'annulation de paiement"""
    # Cette vue est maintenant gérée dans reservations/views.py
    # Gardée pour compatibilité
    messages.warning(request, 'Paiement annulé.')
    return redirect('reservations:reservation_list')


class PaymentPagination(PageNumberPagination):
    """Pagination pour les paiements"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour la consultation des paiements"""
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PaymentPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'is_simulated', 'payment_method']
    search_fields = ['reservation__terrain__name', 'transaction__transaction_id']
    ordering_fields = ['created_at', 'amount', 'paid_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrer selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return Payment.objects.all()
        elif user.role == 'coach':
            # Les coachs voient tous les paiements
            return Payment.objects.all()
        else:  # player
            # Les joueurs voient uniquement leurs paiements
            return Payment.objects.filter(user=user)
    
    @action(detail=False, methods=['post'])
    def create_payment(self, request):
        """Créer un nouveau paiement"""
        serializer = PaymentCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            payment = serializer.save()
            
            # Retourner les détails complets du paiement
            response_serializer = PaymentSerializer(payment)
            return Response({
                'success': True,
                'message': 'Paiement créé avec succès',
                'payment': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def verify_otp(self, request, pk=None):
        """Vérifier le code OTP pour un paiement simulé"""
        try:
            payment = self.get_object()
            
            if not payment.is_simulated:
                return Response({
                    'success': False,
                    'message': 'Ce paiement n\'est pas une simulation'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = SimulationOTPVerifySerializer(
                data=request.data,
                context={'request': request}
            )
            
            if serializer.is_valid():
                result = serializer.save()
                return Response({
                    'success': True,
                    'message': 'OTP vérifié avec succès',
                    'payment': PaymentSerializer(payment).data
                })
            
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def receipt(self, request, pk=None):
        """Générer un reçu de paiement"""
        try:
            payment = self.get_object()
            
            if not payment.is_paid:
                return Response({
                    'success': False,
                    'message': 'Ce paiement n\'a pas été effectué'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            receipt_data = {
                'payment_id': str(payment.id),
                'transaction_id': payment.transaction.transaction_id if payment.transaction else None,
                'amount': float(payment.amount),
                'currency': payment.currency,
                'status': payment.status,
                'payment_method': payment.payment_method.display_name if payment.payment_method else 'Non spécifié',
                'reservation': {
                    'id': payment.reservation.id,
                    'terrain': payment.reservation.terrain.name,
                    'date': payment.reservation.start_time.strftime('%d/%m/%Y'),
                    'time': f"{payment.reservation.start_time.strftime('%H:%M')} - {payment.reservation.end_time.strftime('%H:%M')}"
                },
                'user': {
                    'name': payment.user.get_full_name() or payment.user.username,
                    'email': payment.user.email
                },
                'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
                'is_simulated': payment.is_simulated,
                'created_at': payment.created_at.isoformat()
            }
            
            return Response({
                'success': True,
                'receipt': receipt_data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des moyens de paiement"""
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['method_type', 'provider', 'is_default', 'is_active']
    search_fields = ['provider', 'display_name', 'identifier']
    ordering_fields = ['created_at', 'is_default']
    ordering = ['-is_default', '-created_at']
    
    def get_queryset(self):
        """Uniquement les moyens de paiement de l'utilisateur"""
        return PaymentMethod.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Utiliser le bon sérialiseur selon l'action"""
        if self.action == 'create':
            return PaymentMethodCreateSerializer
        return PaymentMethodSerializer
    
    def perform_create(self, serializer):
        """Assigner l'utilisateur lors de la création"""
        serializer.save(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def set_default(self, request):
        """Définir un moyen de paiement par défaut"""
        serializer = PaymentMethodSetDefaultSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            payment_method = serializer.save()
            return Response({
                'success': True,
                'message': 'Moyen de paiement défini par défaut',
                'payment_method': PaymentMethodSerializer(payment_method).data
            })
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Désactiver un moyen de paiement"""
        try:
            payment_method = self.get_object()
            
            if payment_method.is_default:
                return Response({
                    'success': False,
                    'message': 'Impossible de désactiver le moyen de paiement par défaut'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            payment_method.is_active = False
            payment_method.save()
            
            return Response({
                'success': True,
                'message': 'Moyen de paiement désactivé'
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RefundViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des remboursements"""
    serializer_class = RefundSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = PaymentPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'payment']
    search_fields = ['reason', 'payment__reservation__terrain__name']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filtrer selon le rôle de l'utilisateur"""
        user = self.request.user
        
        if user.role == 'admin':
            return Refund.objects.all()
        elif user.role == 'coach':
            # Les coachs voient tous les remboursements
            return Refund.objects.all()
        else:  # player
            # Les joueurs voient uniquement leurs remboursements
            return Refund.objects.filter(payment__user=user)
    
    def get_serializer_class(self):
        """Utiliser le bon sérialiseur selon l'action"""
        if self.action == 'create':
            return RefundCreateSerializer
        return RefundSerializer
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Traiter un remboursement (admin/coach uniquement)"""
        if request.user.role not in ['admin', 'coach']:
            return Response({
                'success': False,
                'message': 'Permission refusée'
            }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            refund = self.get_object()
            processed_refund = RefundService.process_refund(
                refund_id=refund.id,
                processed_by=request.user
            )
            
            return Response({
                'success': True,
                'message': 'Remboursement traité avec succès',
                'refund': RefundSerializer(processed_refund).data
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def payment_statistics(request):
    """Statistiques des paiements"""
    try:
        # Paramètres de filtrage
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Récupérer les statistiques
        user = request.user if request.user.role == 'player' else None
        stats = PaymentService.get_payment_statistics(
            user=user,
            start_date=start_date,
            end_date=end_date
        )
        
        serializer = PaymentStatisticsSerializer(stats)
        return Response({
            'success': True,
            'statistics': serializer.data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_payments(request):
    """Récupérer les paiements de l'utilisateur connecté"""
    try:
        payments = Payment.objects.filter(user=request.user).order_by('-created_at')
        
        # Pagination
        page_size = int(request.GET.get('page_size', 20))
        page = int(request.GET.get('page', 1))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        payments_page = payments[start:end]
        
        serializer = PaymentSerializer(payments_page, many=True)
        
        return Response({
            'success': True,
            'payments': serializer.data,
            'pagination': {
                'current_page': page,
                'total_pages': (payments.count() + page_size - 1) // page_size,
                'total_count': payments.count(),
                'page_size': page_size
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def simulate_payment(request):
    """Simuler un paiement pour une réservation"""
    try:
        reservation_id = request.data.get('reservation_id')
        payment_method_id = request.data.get('payment_method_id')
        notes = request.data.get('notes', '')
        
        if not reservation_id:
            return Response({
                'success': False,
                'message': 'ID de réservation requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer la réservation
        from reservations.models import Reservation
        try:
            reservation = Reservation.objects.get(
                id=reservation_id,
                user=request.user
            )
        except Reservation.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Réservation introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier qu'il n'y a pas déjà un paiement
        if hasattr(reservation, 'payment'):
            return Response({
                'success': False,
                'message': 'Cette réservation a déjà un paiement'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le paiement
        payment = PaymentService.create_payment_from_reservation(
            reservation=reservation,
            payment_method_id=payment_method_id,
            notes=notes
        )
        
        return Response({
            'success': True,
            'message': 'Paiement simulé avec succès',
            'payment': PaymentSerializer(payment).data,
            'otp_code': '123456'  # Code OTP pour la simulation
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def admin_delete_payment(request, payment_id):
    """Vue admin pour supprimer un paiement"""
    print(f"DEBUG: admin_delete_payment appelé - payment_id={payment_id}, method={request.method}")
    print(f"DEBUG: user.role={request.user.role}")
    
    if request.user.role != 'admin':
        print("DEBUG: Accès refusé - pas admin")
        messages.error(request, 'Accès refusé. Réservé aux administrateurs.')
        return redirect('payments:admin_payment_list')
    
    try:
        payment = Payment.objects.get(id=payment_id)
        print(f"DEBUG: Payment trouvé: {payment.id}")
    except Payment.DoesNotExist:
        print(f"DEBUG: Payment non trouvé avec id={payment_id}")
        return redirect('payments:admin_payment_list')
    
    print(f"DEBUG: Payment trouvé avec succès")
    
    if request.method == 'POST':
        print("DEBUG: Méthode POST détectée")
        try:
            # Récupérer les informations pour le message
            reservation = payment.reservation
            user = payment.user
            amount = payment.amount
            
            print(f"DEBUG: Tentative de suppression du paiement {payment.id}")
            # Supprimer le paiement
            payment.delete()
            print("DEBUG: Paiement supprimé avec succès")
            
            # Mettre la réservation en pending si elle était confirmée
            if reservation.status == 'confirmed':
                reservation.status = 'pending'
                reservation.save()
            
            messages.success(request, f'Paiement de {amount} FCFA pour {user.get_full_name() or user.email} supprimé avec succès.')
            
        except Exception as e:
            messages.error(request, f'Erreur lors de la suppression: {str(e)}')
        
        # Préserver le filtre coach (depuis le formulaire ou l'URL de référence)
        coach_id = request.POST.get('coach')  # Priorité au formulaire
        
        if not coach_id:
            # Si pas dans le formulaire, vérifier l'URL de référence
            referer = request.META.get('HTTP_REFERER')
            if referer and 'coach=' in referer:
                from urllib.parse import urlparse, parse_qs
                parsed_url = urlparse(referer)
                query_params = parse_qs(parsed_url.query)
                if 'coach' in query_params:
                    coach_id = query_params['coach'][0]
        
        if coach_id:
            return redirect(f"{reverse('payments:admin_payment_list')}?coach={coach_id}")
        
        return redirect('payments:admin_payment_list')
    
    # Afficher la page de confirmation
    return render(request, 'payments/admin_payment_delete_confirm.html', {
        'payment': payment,
        'reservation': payment.reservation,
        'user': payment.user
    })
