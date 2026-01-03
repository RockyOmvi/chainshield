"""
ChainShield SDK Exceptions

Custom exceptions for better error handling.
"""


class ChainShieldError(Exception):
    """Base exception for all ChainShield errors."""
    
    def __init__(self, message: str, status_code: int = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(ChainShieldError):
    """Invalid or missing API key."""
    pass


class RateLimitError(ChainShieldError):
    """Rate limit exceeded."""
    
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ValidationError(ChainShieldError):
    """Invalid request parameters."""
    pass


class NotFoundError(ChainShieldError):
    """Resource not found."""
    pass


class ServerError(ChainShieldError):
    """Internal server error."""
    pass
