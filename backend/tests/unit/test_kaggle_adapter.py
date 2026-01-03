"""
Unit tests for Kaggle feature adapter.
"""

import pytest
import sys
sys.path.insert(0, '.')

from app.services.risk.ml.kaggle_adapter import (
    KaggleFeatureAdapter,
    get_kaggle_adapter,
    KAGGLE_FEATURE_NAMES
)


class TestKaggleAdapter:
    """Test suite for KaggleFeatureAdapter."""
    
    @pytest.fixture
    def adapter(self):
        """Create a fresh adapter instance."""
        return KaggleFeatureAdapter()
    
    @pytest.fixture
    def sample_features(self):
        """Sample engine features for testing."""
        return {
            "age_hours": 1000,
            "balance_eth": 10.0,
            "tx_count_total": 50,
            "total_sent_eth": 100.0,
            "total_received_eth": 120.0,
            "time_between_tx_avg_hours": 2.0,
            "in_out_ratio": 0.45,
            "unique_senders": 10,
            "unique_receivers": 15,
            "max_tx_value_eth": 25.0,
            "new_contract_interaction_count": 2,
        }
    
    def test_output_has_45_features(self, adapter, sample_features):
        """Adapter should output exactly 45 features."""
        result = adapter.transform(sample_features)
        
        assert len(result) == 45
    
    def test_output_is_list_of_floats(self, adapter, sample_features):
        """Output should be a list of numbers."""
        result = adapter.transform(sample_features)
        
        assert isinstance(result, list)
        for i, val in enumerate(result):
            assert isinstance(val, (int, float)), f"Feature {i} is not a number: {val}"
    
    def test_age_converted_to_minutes(self, adapter, sample_features):
        """Age in hours should be converted to minutes."""
        result = adapter.transform(sample_features)
        
        # Feature 2 is "Time Diff between first and last (Mins)"
        expected_mins = sample_features["age_hours"] * 60
        assert result[2] == expected_mins
    
    def test_tx_count_split(self, adapter, sample_features):
        """Transaction count should be split between sent and received."""
        result = adapter.transform(sample_features)
        
        # Features 3 and 4 are sent_tnx and received_tnx
        sent_tnx = result[3]
        recv_tnx = result[4]
        
        # Should roughly split based on in_out_ratio
        assert sent_tnx + recv_tnx == sample_features["tx_count_total"]
    
    def test_balance_preserved(self, adapter, sample_features):
        """Balance should be preserved in output."""
        result = adapter.transform(sample_features)
        
        # Feature 21 is "total ether balance"
        assert result[21] == sample_features["balance_eth"]
    
    def test_empty_features_handled(self, adapter):
        """Should handle empty/minimal features."""
        empty_features = {}
        result = adapter.transform(empty_features)
        
        assert len(result) == 45
        # Should have zeros, not errors
        assert all(isinstance(v, (int, float)) for v in result)
    
    def test_singleton_works(self):
        """get_kaggle_adapter should return same instance."""
        adapter1 = get_kaggle_adapter()
        adapter2 = get_kaggle_adapter()
        
        assert adapter1 is adapter2
    
    def test_feature_names_correct_count(self):
        """KAGGLE_FEATURE_NAMES should have 45 names."""
        assert len(KAGGLE_FEATURE_NAMES) == 45
    
    def test_no_nan_or_inf(self, adapter, sample_features):
        """Output should not contain NaN or Inf."""
        import math
        
        result = adapter.transform(sample_features)
        
        for i, val in enumerate(result):
            assert not math.isnan(val), f"Feature {i} is NaN"
            assert not math.isinf(val), f"Feature {i} is Inf"


class TestFeatureMapping:
    """Test specific feature mappings."""
    
    @pytest.fixture
    def adapter(self):
        return KaggleFeatureAdapter()
    
    def test_unique_addresses_mapped(self, adapter):
        """Unique sender/receiver counts should be mapped."""
        features = {
            "unique_senders": 25,
            "unique_receivers": 30,
        }
        result = adapter.transform(features)
        
        # Features 6, 7 are unique addresses
        assert result[6] == 25  # Unique Received From
        assert result[7] == 30  # Unique Sent To


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
