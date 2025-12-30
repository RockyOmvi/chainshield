"""
Configuration Tests

Tests for Pydantic settings configuration.
"""

import pytest
import os


class TestSettings:
    """Test configuration settings."""
    
    def test_settings_loads(self):
        """Test settings can be loaded."""
        from app.core.config import settings
        
        assert settings.app_name == "chainshield"
        assert settings.api_v1_prefix == "/api/v1"
    
    def test_settings_has_required_fields(self):
        """Test settings has all required fields."""
        from app.core.config import settings
        
        # Check required fields exist
        assert hasattr(settings, "secret_key")
        assert hasattr(settings, "jwt_secret_key")
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")
    
    def test_settings_rate_limits(self):
        """Test rate limit settings."""
        from app.core.config import settings
        
        assert settings.rate_limit_requests_per_minute > 0
        assert settings.rate_limit_requests_per_hour > 0
    
    def test_settings_risk_thresholds(self):
        """Test risk threshold settings."""
        from app.core.config import settings
        
        assert settings.risk_high_threshold > settings.risk_medium_threshold
        assert settings.risk_medium_threshold > 0


class TestSettingsValidation:
    """Test settings validation."""
    
    def test_app_name_lowercase(self):
        """Test app name is lowercase."""
        from app.core.config import settings
        
        assert settings.app_name == settings.app_name.lower()
    
    def test_api_prefix_format(self):
        """Test API prefix starts with slash."""
        from app.core.config import settings
        
        assert settings.api_v1_prefix.startswith("/")
