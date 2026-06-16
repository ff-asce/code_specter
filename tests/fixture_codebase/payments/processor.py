"""Payment processing module."""

from decimal import Decimal
from typing import Optional
from ..transactions.models import Transaction


class PaymentProcessor:
    """Handles payment processing operations."""
    
    def __init__(self, merchant_id: str, api_key: str):
        """
        Initialize payment processor.
        
        Args:
            merchant_id: Merchant identifier
            api_key: API key for payment gateway
        """
        self.merchant_id = merchant_id
        self.api_key = api_key
        self.gateway_url = "https://api.payment-gateway.example.com"
    
    def process_payment(
        self,
        amount: Decimal,
        currency: str,
        customer_id: str,
        payment_method: str
    ) -> Transaction:
        """
        Process a payment transaction.
        
        Args:
            amount: Payment amount
            currency: Currency code (e.g., 'USD')
            customer_id: Customer identifier
            payment_method: Payment method (e.g., 'card', 'bank')
            
        Returns:
            Transaction object with result
            
        Raises:
            ValueError: If amount is negative or zero
            PaymentError: If payment processing fails
        """
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        # Validate payment method
        if payment_method not in ['card', 'bank', 'wallet']:
            raise ValueError(f"Invalid payment method: {payment_method}")
        
        # Create transaction
        transaction = Transaction(
            amount=amount,
            currency=currency,
            customer_id=customer_id,
            payment_method=payment_method,
            merchant_id=self.merchant_id
        )
        
        # Process with gateway
        result = self._call_gateway(transaction)
        transaction.status = result['status']
        transaction.transaction_id = result['transaction_id']
        
        return transaction
    
    def _call_gateway(self, transaction: Transaction) -> dict:
        """
        Call payment gateway API.
        
        This is a stub - in production would make actual API call.
        """
        # Simulate gateway call
        return {
            'status': 'completed',
            'transaction_id': f'txn_{transaction.customer_id}_{transaction.amount}'
        }
    
    def get_transaction_status(self, transaction_id: str) -> str:
        """
        Get status of a transaction.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Status string ('pending', 'completed', 'failed')
        """
        # Stub implementation
        return 'completed'

# Made with Bob
