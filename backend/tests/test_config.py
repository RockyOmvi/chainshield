"""
Configuration Tests

Tests for Pydantic settings and configuration loading.
"""

import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Test Settings configuration."""
    
    def test_settings_loads_defaults(self):
        """Test settings loads with defaults."""
        from app.core.config import Settings
        
        # Create settings with minimal required values
        with patch.dict(os.environ, {
            "SECRET_KEY": "test-secret",
            "JWT_SECRET_KEY": "test-jwt-secret",
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db"
        }):
            settings = Settings()
            
            assert settings.app_name == "chainshield"
            assert settings.app_env == "development"
            assert settings.port == 8000
    
    def test_settings_validates_required(self):
        """Test settings requires mandatory fields."""
        from app.core.config import Settings
        from pydantic import ValidationError
        
        # Clear environment and try to create settings
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()
    
    def test_is_production_property(self):
        """Test is_production property."""
        from app.core.config import Settings
        
        with patch.dict(os.environ, {
            "SECRET_KEY": "test",
            "JWT_SECRET_KEY": "test",
            "DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "APP_ENV": "production"
        }):
            settings = Settings()
            assert settings.is_production is True
    
    def test_is_development_property(self):
        """Test is_development property."""
        from app.core.config import Settings
        
        with patch.dict(os.environ, {
            "SECRET_KEY": "test",
            "JWT_SECRET_KEY": "test",
            "DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "APP_ENV": "development"
        }):
            settings = Settings()
            assert settings.is_development is True
    
    def test_alchemy_url_construction(self):
        """Test Alchemy URL is constructed correctly."""
        from app.core.config import Settings
        
        with patch.dict(os.environ, {
            "SECRET_KEY": "test",
            "JWT_SECRET_KEY": "test",
            "DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "ALCHEMY_API_KEY": "test-alchemy-key",
            "ALCHEMY_NETWORK": "eth-mainnet"
        }):
            settings = Settings()
            assert "test-alchemy-key" in settings.alchemy_url
            assert "eth-mainnet" in settings.alchemy_url
    
    def test_cors_origins_parsing_json(self):
        """Test CORS origins can be parsed from JSON."""
        from app.core.config import Settings
        
        with patch.dict(os.environ, {
            "SECRET_KEY": "test",
            "JWT_SECRET_KEY": "test",
            "DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "CORS_ORIGINS": '["http://localhost:3000", "http://localhost:5173"]'
        }):
            settings = Settings()
            assert "http://localhost:3000" in settings.cors_origins
            assert len(settings.cors_origins) == 2
    
    def test_cors_origins_parsing_csv(self):
        """Test CORS origins can be parsed from CSV."""
        from app.core.config import Settings
        
        with patch.dict(os.environ, {
            "SECRET_KEY": "test",
            "JWT_SECRET_KEY": "test",
            "DATABASE_URL": "postgresql+asyncpg://localhost/db",
            "CORS_ORIGINS": "http://localhost:3000, http://localhost:5173"
        }):
            settings = Settings()
            assert len(settings.cors_origins) == 2
