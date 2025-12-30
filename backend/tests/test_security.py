"""
Security Tests

Tests for security functionality.
"""

import pytest

from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_api_key,
    hash_api_key,
)


class TestPasswordHashing:
    """Test password hashing functionality."""
    
    def test_hash_password(self):
        """Test password hashing."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "TestPassword123!"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
    
    def test_verify_wrong_password(self):
        """Test verifying wrong password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
    
    def test_different_hashes_for_same_password(self):
        """Test that same password produces different hashes."""
        password = "TestPassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Different salts should produce different hashes
        assert hash1 != hash2


class TestJWTTokens:
    """Test JWT token functionality."""
    
    def test_create_access_token(self):
        """Test access token creation."""
        data = {"sub": "user@example.com", "type": "access"}
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
    
    def test_create_refresh_token(self):
        """Test refresh token creation."""
        data = {"sub": "user@example.com"}
        token = create_refresh_token(data)
        
        assert token is not None
        assert len(token) > 0
    
    def test_verify_access_token(self):
        """Test access token verification."""
        data = {"sub": "user@example.com", "type": "access"}
        token = create_access_token(data)
        
        payload = verify_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == "user@example.com"
    
    def test_verify_invalid_token(self):
        """Test invalid token verification."""
        with pytest.raises(Exception):
            verify_token("invalid.token.here", "access")


class TestAPIKeys:
    """Test API key functionality."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        full_key, key_hash, key_id = generate_api_key()
        
        assert full_key.startswith("cs_")
        assert len(key_hash) == 64  # SHA-256 hex
        assert len(key_id) == 32  # 16 bytes hex
    
    def test_hash_api_key(self):
        """Test API key hashing."""
        key = "cs_test_key_12345"
        hashed = hash_api_key(key)
        
        assert hashed != key
        assert len(hashed) == 64  # SHA-256 hex
    
    def test_same_key_same_hash(self):
        """Test same key produces same hash."""
        key = "cs_test_key_12345"
        hash1 = hash_api_key(key)
        hash2 = hash_api_key(key)
        
        assert hash1 == hash2
