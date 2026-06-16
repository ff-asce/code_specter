"""Transaction data models."""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """Represents a payment transaction."""
    
    amount: Decimal
    currency: str
    customer_id: str
    payment_method: str
    merchant_id: str
    status: str = "pending"
    transaction_id: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()
    
    def is_completed(self) -> bool:
        """Check if transaction is completed."""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """Check if transaction failed."""
        return self.status == "failed"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'amount': str(self.amount),
            'currency': self.currency,
            'customer_id': self.customer_id,
            'payment_method': self.payment_method,
            'merchant_id': self.merchant_id,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


@dataclass
class RefundRequest:
    """Represents a refund request."""
    
    transaction_id: str
    amount: Decimal
    reason: str
    requested_by: str
    status: str = "pending"
    refund_id: Optional[str] = None
    created_at: datetime = None
    
    def __post_init__(self):
        """Initialize timestamp if not provided."""
        if self.created_at is None:
            self.created_at = datetime.utcnow()

# Made with Bob
