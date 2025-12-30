"""
Security Module Tests

Tests for JWT, password hashing, and API key functions.
"""

import pytest
from datetime import timedelta

from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)
from app.core.errors import UnauthorizedError


class TestPasswordHashing:
    """Test password hashing functions."""
    
    def test_hash_password(self):
        """Test password is hashed."""
        password = "secure_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are long
        assert hashed.startswith("$2")  # bcrypt prefix
    
    def test_verify_correct_password(self):
        """Test correct password verifies."""
        password = "secure_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test wrong password fails."""
        password = "secure_password_123"
        hashed = get_password_hash(password)
        
        assert verify_password("wrong_password", hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test same password produces different hashes (salt)."""
        password = "secure_password_123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2  # Different salts


class TestJWTTokens:
    """Test JWT token functions."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        token = create_access_token(subject="user_123")
        
        assert token is not None
        assert len(token) > 50
        assert token.count(".") == 2  # JWT format: header.payload.signature
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        token = create_refresh_token(subject="user_123")
        
        assert token is not None
        assert len(token) > 50
    
    def test_verify_valid_access_token(self):
        """Test valid access token verifies."""
        token = create_access_token(subject="user_123")
        payload = verify_token(token, token_type="access")
        
        assert payload["sub"] == "user_123"
        assert payload["type"] == "access"
    
    def test_verify_valid_refresh_token(self):
        """Test valid refresh token verifies."""
        token = create_refresh_token(subject="user_456")
        payload = verify_token(token, token_type="refresh")
        
        assert payload["sub"] == "user_456"
        assert payload["type"] == "refresh"
        assert "jti" in payload  # Unique token ID
    
    def test_wrong_token_type_rejected(self):
        """Test wrong token type is rejected."""
        access_token = create_access_token(subject="user_123")
        
        with pytest.raises(UnauthorizedError, match="Invalid token type"):
            verify_token(access_token, token_type="refresh")
    
    def test_invalid_token_rejected(self):
        """Test invalid token is rejected."""
        with pytest.raises(UnauthorizedError, match="Invalid token"):
            verify_token("invalid.token.here", token_type="access")
    
    def test_extra_claims_in_token(self):
        """Test extra claims are included in token."""
        token = create_access_token(
            subject="user_123",
            extra_claims={"role": "admin", "scopes": ["read", "write"]}
        )
        payload = verify_token(token, token_type="access")
        
        assert payload["role"] == "admin"
        assert payload["scopes"] == ["read", "write"]


class TestAPIKeys:
    """Test API key functions."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        full_key, key_hash, key_id = generate_api_key()
        
        assert full_key.startswith("cs_")  # Prefix from settings
        assert len(full_key) > 40
        assert len(key_hash) == 64  # SHA-256 hex
        assert len(key_id) == 32
    
    def test_hash_api_key(self):
        """Test API key hashing is consistent."""
        key = "cs_abc123def456"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256
    
    def test_verify_correct_api_key(self):
        """Test correct API key verifies."""
        full_key, key_hash, _ = generate_api_key()
        
        assert verify_api_key(full_key, key_hash) is True
    
    def test_verify_wrong_api_key(self):
        """Test wrong API key fails."""
        _, key_hash, _ = generate_api_key()
        
        assert verify_api_key("wrong_key", key_hash) is False
    
    def test_timing_safe_comparison(self):
        """Test verify uses timing-safe comparison (hmac.compare_digest)."""
        # This is a behavioral test - just verify it works correctly
        full_key, key_hash, _ = generate_api_key()
        
        # Correct key
        assert verify_api_key(full_key, key_hash) is True
        
        # Wrong keys (timing should be similar)
        assert verify_api_key(full_key + "x", key_hash) is False
        assert verify_api_key("totally_wrong", key_hash) is False
