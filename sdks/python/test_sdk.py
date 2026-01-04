"""
Test Python SDK - Verify all components work
"""

import sys
sys.path.insert(0, 'd:/project/chainshield/sdks/python')

def test_imports():
    """Test all imports work."""
    print("Testing Python SDK imports...")
    
    try:
        from chainshield import (
            ChainShield,
            RiskAssessment,
            RiskLevel,
            Chain,
            ChainShieldError,
            AuthenticationError,
            RateLimitError,
        )
        print("  [PASS] All imports successful")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False


def test_models():
    """Test model classes."""
    print("\nTesting models...")
    
    try:
        from chainshield.models import RiskAssessment, RiskLevel, Chain
        
        # Test RiskLevel enum
        assert RiskLevel.LOW.value == "LOW"
        assert RiskLevel.CRITICAL.value == "CRITICAL"
        print("  [PASS] RiskLevel enum works")
        
        # Test Chain enum
        assert Chain.ETHEREUM.value == "ethereum"
        assert Chain.BITCOIN.value == "bitcoin"
        print("  [PASS] Chain enum works")
        
        # Test RiskAssessment from_dict
        data = {
            "address": "0x123",
            "chain": "ethereum",
            "risk_score": 45.5,
            "risk_level": "MEDIUM",
            "blocked": False,
            "factors": ["test factor"]
        }
        assessment = RiskAssessment.from_dict(data)
        
        assert assessment.address == "0x123"
        assert assessment.risk_score == 45.5
        assert not assessment.is_high_risk
        assert not assessment.is_sanctioned
        print("  [PASS] RiskAssessment dataclass works")
        
        # Test high risk detection
        data["risk_level"] = "HIGH"
        data["risk_score"] = 85.0
        high_risk = RiskAssessment.from_dict(data)
        assert high_risk.is_high_risk
        print("  [PASS] is_high_risk property works")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Model error: {e}")
        return False


def test_exceptions():
    """Test exception classes."""
    print("\nTesting exceptions...")
    
    try:
        from chainshield.exceptions import (
            ChainShieldError,
            AuthenticationError,
            RateLimitError,
            ValidationError,
        )
        
        # Test base error
        err = ChainShieldError("Test error", status_code=500)
        assert err.message == "Test error"
        assert err.status_code == 500
        print("  [PASS] ChainShieldError works")
        
        # Test auth error
        auth_err = AuthenticationError("Invalid key")
        assert isinstance(auth_err, ChainShieldError)
        print("  [PASS] AuthenticationError inheritance works")
        
        # Test rate limit error
        rate_err = RateLimitError("Too many requests", retry_after=60)
        assert rate_err.retry_after == 60
        print("  [PASS] RateLimitError works")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Exception error: {e}")
        return False


def test_client_creation():
    """Test client can be created."""
    print("\nTesting client creation...")
    
    try:
        from chainshield.client import ChainShield
        from chainshield.exceptions import AuthenticationError
        
        # Test valid API key
        client = ChainShield(api_key="cs_test_key_123")
        assert client.api_key == "cs_test_key_123"
        print("  [PASS] Client created with valid key")
        
        # Test invalid API key format
        try:
            ChainShield(api_key="invalid_key")
            print("  [FAIL] Should have raised AuthenticationError")
            return False
        except AuthenticationError:
            print("  [PASS] Invalid key rejected correctly")
        
        # Test empty API key
        try:
            ChainShield(api_key="")
            print("  [FAIL] Should have raised AuthenticationError")
            return False
        except AuthenticationError:
            print("  [PASS] Empty key rejected correctly")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Client error: {e}")
        return False


def main():
    print("=" * 50)
    print("  PYTHON SDK TEST")
    print("=" * 50)
    
    results = [
        test_imports(),
        test_models(),
        test_exceptions(),
        test_client_creation(),
    ]
    
    passed = sum(results)
    total = len(results)
    
    print("\n" + "=" * 50)
    print(f"  RESULT: {passed}/{total} tests passed")
    print("=" * 50)
    
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
