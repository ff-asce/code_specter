"""Idempotency handling for transactions."""

from typing import Optional, Dict
from datetime import datetime, timedelta


class IdempotencyStore:
    """In-memory store for idempotency keys."""
    
    def __init__(self, ttl_hours: int = 24):
        """
        Initialize idempotency store.
        
        Args:
            ttl_hours: Time-to-live for idempotency keys in hours
        """
        self.store: Dict[str, dict] = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def check_key(self, idempotency_key: str) -> Optional[dict]:
        """
        Check if idempotency key exists and return cached result.
        
        Args:
            idempotency_key: Unique key for the operation
            
        Returns:
            Cached result if key exists and not expired, None otherwise
        """
        if idempotency_key not in self.store:
            return None
        
        entry = self.store[idempotency_key]
        
        # Check if expired
        if datetime.utcnow() - entry['timestamp'] > self.ttl:
            del self.store[idempotency_key]
            return None
        
        return entry['result']
    
    def store_result(self, idempotency_key: str, result: dict) -> None:
        """
        Store result for an idempotency key.
        
        Args:
            idempotency_key: Unique key for the operation
            result: Result to cache
        """
        self.store[idempotency_key] = {
            'result': result,
            'timestamp': datetime.utcnow()
        }
    
    def cleanup_expired(self) -> int:
        """
        Remove expired entries.
        
        Returns:
            Number of entries removed
        """
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self.store.items()
            if now - entry['timestamp'] > self.ttl
        ]
        
        for key in expired_keys:
            del self.store[key]
        
        return len(expired_keys)


def generate_idempotency_key(customer_id: str, operation: str, timestamp: str) -> str:
    """
    Generate an idempotency key.
    
    Args:
        customer_id: Customer identifier
        operation: Operation type
        timestamp: Timestamp string
        
    Returns:
        Idempotency key
    """
    return f"{customer_id}:{operation}:{timestamp}"

# Made with Bob
