"""
ChainShield Kaggle Feature Adapter

Transforms engine features to the 45-feature format used by the 
trained Kaggle models (ensemble, isolation forest).

The Kaggle dataset has these 45 features:
1-4: Timing (avg min between sent/received tnx, time diff first/last)
5-6: Counts (sent tnx, received tnx)
7: Created contracts
8-9: Unique addresses (received from, sent to)
10-15: Value stats for received (min, max, avg)
16-21: Value stats for sent (min, max, avg, contract variants)
22-25: Totals (transactions, ETH sent, received, balance)
26-45: ERC20 token metrics (20 features)
"""

from typing import Dict, List
import structlog

logger = structlog.get_logger()


# Kaggle feature names in exact order expected by model
KAGGLE_FEATURE_NAMES = [
    "Avg min between sent tnx",
    "Avg min between received tnx",
    "Time Diff between first and last (Mins)",
    "Sent tnx",
    "Received Tnx",
    "Number of Created Contracts",
    "Unique Received From Addresses",
    "Unique Sent To Addresses",
    "min value received",
    "max value received ",
    "avg val received",
    "min val sent",
    "max val sent",
    "avg val sent",
    "min value sent to contract",
    "max val sent to contract",
    "avg value sent to contract",
    "total transactions (including tnx to create contract",
    "total Ether sent",
    "total ether received",
    "total ether sent contracts",
    "total ether balance",
    " Total ERC20 tnxs",
    " ERC20 total Ether received",
    " ERC20 total ether sent",
    " ERC20 total Ether sent contract",
    " ERC20 uniq sent addr",
    " ERC20 uniq rec addr",
    " ERC20 uniq sent addr.1",
    " ERC20 uniq rec contract addr",
    " ERC20 avg time between sent tnx",
    " ERC20 avg time between rec tnx",
    " ERC20 avg time between rec 2 tnx",
    " ERC20 avg time between contract tnx",
    " ERC20 min val rec",
    " ERC20 max val rec",
    " ERC20 avg val rec",
    " ERC20 min val sent",
    " ERC20 max val sent",
    " ERC20 avg val sent",
    " ERC20 min val sent contract",
    " ERC20 max val sent contract",
    " ERC20 avg val sent contract",
    " ERC20 uniq sent token name",
    " ERC20 uniq rec token name",
]


class KaggleFeatureAdapter:
    """
    Transforms engine FeatureVector to Kaggle 45-feature format.
    
    Maps engine features to Kaggle equivalents:
    - age_hours -> Time Diff between first and last (Mins)
    - tx_per_hour_avg -> Avg min between sent/received tnx
    - total_sent_eth -> total Ether sent
    - etc.
    
    Missing ERC20 features default to 0.
    """
    
    def __init__(self):
        self.logger = logger.bind(module="kaggle_adapter")
        self.n_features = len(KAGGLE_FEATURE_NAMES)
    
    def transform(self, engine_features: Dict[str, float]) -> List[float]:
        """
        Transform engine features dict to Kaggle feature array.
        
        Args:
            engine_features: Feature dict from WalletFeatureExtractor
            
        Returns:
            List of 45 floats in Kaggle order
        """
        f = engine_features
        
        # Calculate derived values
        time_between_sent = f.get("time_between_tx_avg_hours", 1) * 60  # hours -> mins
        time_between_recv = time_between_sent * 1.2  # estimate
        
        age_mins = f.get("age_hours", 0) * 60
        
        tx_count = f.get("tx_count_total", 0)
        sent_tnx = int(tx_count * f.get("in_out_ratio", 0.5))
        recv_tnx = tx_count - sent_tnx
        
        total_sent = f.get("total_sent_eth", 0)
        total_received = f.get("total_received_eth", 0)
        
        avg_received = total_received / max(recv_tnx, 1)
        avg_sent = total_sent / max(sent_tnx, 1)
        
        max_val = f.get("max_tx_value_eth", 0)
        
        # Build 45-feature array
        kaggle_features = [
            # 1-4: Timing
            time_between_sent,                          # Avg min between sent tnx
            time_between_recv,                          # Avg min between received tnx
            age_mins,                                   # Time Diff first/last (Mins)
            
            # 5-6: Transaction counts
            sent_tnx,                                   # Sent tnx
            recv_tnx,                                   # Received Tnx
            
            # 7: Contracts created
            f.get("new_contract_interaction_count", 0), # Number of Created Contracts
            
            # 8-9: Unique addresses
            f.get("unique_senders", 1),                 # Unique Received From
            f.get("unique_receivers", 1),              # Unique Sent To
            
            # 10-12: Value received (min, max, avg)
            0.0,                                        # min value received
            max_val if total_received > 0 else 0,       # max value received
            avg_received,                               # avg val received
            
            # 13-15: Value sent (min, max, avg)
            0.0,                                        # min val sent
            max_val if total_sent > 0 else 0,           # max val sent
            avg_sent,                                   # avg val sent
            
            # 16-18: Contract value (estimate 0 for now)
            0.0,                                        # min value sent to contract
            0.0,                                        # max val sent to contract
            0.0,                                        # avg value sent to contract
            
            # 19-22: Totals
            tx_count,                                   # total transactions
            total_sent,                                 # total Ether sent
            total_received,                             # total ether received
            total_sent * 0.1,                           # total ether sent contracts (est.)
            f.get("balance_eth", 0),                    # total ether balance
            
            # 23-45: ERC20 features (default to 0 or estimate)
            tx_count * 0.3,                             # Total ERC20 tnxs (estimate 30%)
            total_received * 0.2,                       # ERC20 total Ether received
            total_sent * 0.2,                           # ERC20 total ether sent
            total_sent * 0.05,                          # ERC20 total Ether sent contract
            f.get("unique_receivers", 1) * 0.5,         # ERC20 uniq sent addr
            f.get("unique_senders", 1) * 0.5,           # ERC20 uniq rec addr
            f.get("unique_receivers", 1) * 0.3,         # ERC20 uniq sent addr.1
            0.0,                                        # ERC20 uniq rec contract addr
            time_between_sent * 1.5,                    # ERC20 avg time between sent tnx
            time_between_recv * 1.5,                    # ERC20 avg time between rec tnx
            time_between_recv * 1.5,                    # ERC20 avg time between rec 2 tnx
            0.0,                                        # ERC20 avg time between contract tnx
            0.0,                                        # ERC20 min val rec
            max_val * 0.3,                              # ERC20 max val rec
            avg_received * 0.3,                         # ERC20 avg val rec
            0.0,                                        # ERC20 min val sent
            max_val * 0.3,                              # ERC20 max val sent
            avg_sent * 0.3,                             # ERC20 avg val sent
            0.0,                                        # ERC20 min val sent contract
            0.0,                                        # ERC20 max val sent contract
            0.0,                                        # ERC20 avg val sent contract
            1.0,                                        # ERC20 uniq sent token name
            1.0,                                        # ERC20 uniq rec token name
        ]
        
        return kaggle_features
    
    def get_feature_names(self) -> List[str]:
        """Return ordered list of Kaggle feature names."""
        return KAGGLE_FEATURE_NAMES


# Singleton
_adapter = None

def get_kaggle_adapter() -> KaggleFeatureAdapter:
    """Get singleton Kaggle adapter."""
    global _adapter
    if _adapter is None:
        _adapter = KaggleFeatureAdapter()
    return _adapter
