"""API routes for payment system."""

from decimal import Decimal
from typing import Dict, Any
from ..payments.processor import PaymentProcessor
from ..transactions.idempotency import IdempotencyStore


class PaymentAPI:
    """REST API for payment operations."""
    
    def __init__(self, processor: PaymentProcessor):
        """
        Initialize API.
        
        Args:
            processor: Payment processor instance
        """
        self.processor = processor
        self.idempotency_store = IdempotencyStore()
    
    def create_payment(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new payment.
        
        Args:
            request_data: Payment request data containing:
                - amount: Payment amount
                - currency: Currency code
                - customer_id: Customer identifier
                - payment_method: Payment method
                - idempotency_key: Optional idempotency key
                
        Returns:
            Response dictionary with transaction details
        """
        # Check idempotency
        idempotency_key = request_data.get('idempotency_key')
        if idempotency_key:
            cached_result = self.idempotency_store.check_key(idempotency_key)
            if cached_result:
                return cached_result
        
        # Validate request
        required_fields = ['amount', 'currency', 'customer_id', 'payment_method']
        for field in required_fields:
            if field not in request_data:
                return {
                    'error': f'Missing required field: {field}',
                    'status': 'error'
                }
        
        try:
            # Process payment
            transaction = self.processor.process_payment(
                amount=Decimal(str(request_data['amount'])),
                currency=request_data['currency'],
                customer_id=request_data['customer_id'],
                payment_method=request_data['payment_method']
            )
            
            result = {
                'status': 'success',
                'transaction': transaction.to_dict()
            }
            
            # Store for idempotency
            if idempotency_key:
                self.idempotency_store.store_result(idempotency_key, result)
            
            return result
            
        except ValueError as e:
            return {
                'error': str(e),
                'status': 'error'
            }
    
    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """
        Get transaction status.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Response dictionary with transaction status
        """
        status = self.processor.get_transaction_status(transaction_id)
        
        return {
            'status': 'success',
            'transaction_id': transaction_id,
            'transaction_status': status
        }
    
    def health_check(self) -> Dict[str, str]:
        """
        Health check endpoint.
        
        Returns:
            Health status
        """
        return {
            'status': 'healthy',
            'service': 'payment-api'
        }

# Made with Bob
