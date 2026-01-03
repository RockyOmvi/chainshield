"""
ChainShield Feature Extraction Module

Extracts 30+ features from wallet and transaction data for risk assessment.
This is the core IP - the features we extract determine model quality.

Design Principles:
1. Every feature must be explainable to a regulator
2. Features must be computable in <10ms
3. Missing data handled gracefully (defaults, not crashes)
4. All features normalized to [0, 1] or standard scale
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import math
import structlog

logger = structlog.get_logger()


@dataclass
class FeatureVector:
    """
    Container for extracted features with metadata.
    
    Attributes:
        features: Dict of feature_name -> value
        metadata: Extraction metadata (timestamp, source, etc.)
        missing: List of features that couldn't be computed
    """
    features: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    missing: List[str] = field(default_factory=list)
    
    def to_array(self, feature_names: List[str]) -> List[float]:
        """Convert to ordered array for ML model input."""
        return [self.features.get(name, 0.0) for name in feature_names]
    
    def get(self, name: str, default: float = 0.0) -> float:
        """Get feature value with default."""
        return self.features.get(name, default)


class WalletFeatureExtractor:
    """
    Extracts risk-relevant features from wallet data.
    
    Features are organized into categories:
    - Basic: Age, balance, transaction count
    - Volume: Total in/out, averages, maximums
    - Velocity: Transactions per time window
    - Behavior: Patterns in transaction behavior
    - Network: Counterparty analysis
    - Temporal: Time-based patterns
    - Risk Signals: Known risk indicators
    """
    
    # Standard feature names (order matters for ML model)
    FEATURE_NAMES = [
        # Basic (5)
        "age_hours",
        "age_days",
        "balance_eth",
        "balance_log",
        "tx_count_total",
        
        # Volume (8)
        "total_received_eth",
        "total_sent_eth",
        "total_received_log",
        "total_sent_log",
        "avg_tx_value_eth",
        "max_tx_value_eth",
        "volume_24h_eth",
        "volume_7d_eth",
        
        # Velocity (5)
        "tx_per_hour_avg",
        "tx_per_hour_max",
        "tx_per_day_avg",
        "time_between_tx_avg_hours",
        "time_between_tx_min_hours",
        
        # Behavior (6)
        "in_out_ratio",
        "self_transfer_ratio",
        "contract_interaction_ratio",
        "failed_tx_ratio",
        "avg_gas_price_gwei",
        "gas_price_variance",
        
        # Network (4)
        "unique_senders",
        "unique_receivers",
        "counterparty_concentration",
        "new_counterparty_ratio",
        
        # Temporal (4)
        "active_hours_entropy",
        "weekend_tx_ratio",
        "night_tx_ratio",
        "burst_score",
        
        # Risk Signals (4)
        "mixer_interaction_count",
        "new_contract_interaction_count",
        "round_number_tx_ratio",
        "dust_tx_ratio",
    ]
    
    def __init__(self):
        self.logger = logger.bind(module="feature_extractor")
    
    def extract(self, wallet_data: Dict[str, Any]) -> FeatureVector:
        """
        Extract all features from wallet data.
        
        Args:
            wallet_data: Dictionary containing:
                - address: Wallet address
                - balance: Current balance in ETH
                - transactions: List of transaction objects
                - first_seen: First transaction timestamp
                - created_at: Account creation (if known)
                
        Returns:
            FeatureVector with all computed features
        """
        features = {}
        missing = []
        
        try:
            # Extract each category
            features.update(self._extract_basic(wallet_data, missing))
            features.update(self._extract_volume(wallet_data, missing))
            features.update(self._extract_velocity(wallet_data, missing))
            features.update(self._extract_behavior(wallet_data, missing))
            features.update(self._extract_network(wallet_data, missing))
            features.update(self._extract_temporal(wallet_data, missing))
            features.update(self._extract_risk_signals(wallet_data, missing))
            
        except Exception as e:
            self.logger.error("feature_extraction_failed", error=str(e))
            # Return partial features rather than crash
        
        return FeatureVector(
            features=features,
            metadata={
                "address": wallet_data.get("address"),
                "extracted_at": datetime.utcnow().isoformat(),
                "tx_count_analyzed": len(wallet_data.get("transactions", [])),
            },
            missing=missing
        )
    
    def _extract_basic(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract basic wallet metrics."""
        features = {}
        
        # Age calculation - check for pre-calculated age first (from test data or API)
        pre_age_hours = data.get("age_hours")
        if pre_age_hours is not None and pre_age_hours > 0:
            features["age_hours"] = float(pre_age_hours)
            features["age_days"] = float(pre_age_hours) / 24.0
        else:
            # Calculate from first_seen timestamp
            first_seen = data.get("first_seen")
            if first_seen:
                if isinstance(first_seen, str):
                    first_seen = datetime.fromisoformat(first_seen.replace("Z", "+00:00"))
                age = datetime.utcnow() - first_seen.replace(tzinfo=None)
                features["age_hours"] = age.total_seconds() / 3600
                features["age_days"] = age.days
            else:
                features["age_hours"] = 0.0
                features["age_days"] = 0.0
                missing.append("age_hours")
        
        # Balance
        balance = float(data.get("balance", 0))
        features["balance_eth"] = balance
        features["balance_log"] = math.log1p(balance)  # log(1 + balance) for scale
        
        # Transaction count
        transactions = data.get("transactions", [])
        features["tx_count_total"] = float(len(transactions))
        
        return features
    
    def _extract_volume(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract volume-based metrics."""
        features = {}
        transactions = data.get("transactions", [])
        address = data.get("address", "").lower()
        
        # Check for pre-calculated totals (from blockchain API)
        pre_total_received = data.get("total_received", 0)
        pre_total_sent = data.get("total_sent", 0)
        
        if not transactions and not pre_total_received and not pre_total_sent:
            # No data at all - use defaults
            for name in ["total_received_eth", "total_sent_eth", "total_received_log",
                        "total_sent_log", "avg_tx_value_eth", "max_tx_value_eth",
                        "volume_24h_eth", "volume_7d_eth"]:
                features[name] = 0.0
                missing.append(name)
            return features
        
        # Use pre-calculated values if available (from blockchain API)
        if pre_total_received > 0 or pre_total_sent > 0:
            features["total_received_eth"] = float(pre_total_received)
            features["total_sent_eth"] = float(pre_total_sent)
            features["total_received_log"] = math.log1p(pre_total_received)
            features["total_sent_log"] = math.log1p(pre_total_sent)
            
            # Estimate averages from tx_count_total
            tx_count = data.get("tx_count_total", 1) or 1
            total_volume = pre_total_received + pre_total_sent
            features["avg_tx_value_eth"] = total_volume / tx_count
            features["max_tx_value_eth"] = total_volume / 10  # Estimate
            features["volume_24h_eth"] = 0.0  # Can't calculate without tx timestamps
            features["volume_7d_eth"] = 0.0
            
            return features
        
        # Calculate from transactions if available
        total_in = 0.0
        total_out = 0.0
        values = []
        now = datetime.utcnow()
        volume_24h = 0.0
        volume_7d = 0.0
        
        for tx in transactions:
            value = float(tx.get("value", 0))
            values.append(value)
            
            # Direction
            if tx.get("to", "").lower() == address:
                total_in += value
            else:
                total_out += value
            
            # Time-based volume
            tx_time = tx.get("timestamp")
            if tx_time:
                if isinstance(tx_time, str):
                    tx_time = datetime.fromisoformat(tx_time.replace("Z", "+00:00"))
                age = now - tx_time.replace(tzinfo=None)
                if age <= timedelta(days=1):
                    volume_24h += value
                if age <= timedelta(days=7):
                    volume_7d += value
        
        features["total_received_eth"] = total_in
        features["total_sent_eth"] = total_out
        features["total_received_log"] = math.log1p(total_in)
        features["total_sent_log"] = math.log1p(total_out)
        features["avg_tx_value_eth"] = sum(values) / len(values) if values else 0.0
        features["max_tx_value_eth"] = max(values) if values else 0.0
        features["volume_24h_eth"] = volume_24h
        features["volume_7d_eth"] = volume_7d
        
        return features
    
    def _extract_velocity(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract velocity/speed metrics."""
        features = {}
        transactions = data.get("transactions", [])
        
        if len(transactions) < 2:
            for name in ["tx_per_hour_avg", "tx_per_hour_max", "tx_per_day_avg",
                        "time_between_tx_avg_hours", "time_between_tx_min_hours"]:
                features[name] = 0.0
            return features
        
        # Sort by timestamp
        sorted_txs = sorted(
            transactions, 
            key=lambda x: x.get("timestamp", ""),
            reverse=False
        )
        
        # Calculate time gaps
        gaps = []
        for i in range(1, len(sorted_txs)):
            t1 = sorted_txs[i-1].get("timestamp")
            t2 = sorted_txs[i].get("timestamp")
            if t1 and t2:
                if isinstance(t1, str):
                    t1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
                if isinstance(t2, str):
                    t2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
                gap = (t2.replace(tzinfo=None) - t1.replace(tzinfo=None)).total_seconds() / 3600
                if gap >= 0:  # Valid gap
                    gaps.append(gap)
        
        if gaps:
            features["time_between_tx_avg_hours"] = sum(gaps) / len(gaps)
            features["time_between_tx_min_hours"] = min(gaps)
        else:
            features["time_between_tx_avg_hours"] = 0.0
            features["time_between_tx_min_hours"] = 0.0
        
        # Transactions per time unit
        age_hours = data.get("age_hours", 1) or 1
        features["tx_per_hour_avg"] = len(transactions) / age_hours
        features["tx_per_day_avg"] = len(transactions) / (age_hours / 24) if age_hours >= 24 else float(len(transactions))
        
        # Max hourly rate (simplified - could be more precise with windowing)
        features["tx_per_hour_max"] = features["tx_per_hour_avg"] * 2  # Estimate
        
        return features
    
    def _extract_behavior(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract behavioral pattern metrics."""
        features = {}
        transactions = data.get("transactions", [])
        address = data.get("address", "").lower()
        
        if not transactions:
            for name in ["in_out_ratio", "self_transfer_ratio", "contract_interaction_ratio",
                        "failed_tx_ratio", "avg_gas_price_gwei", "gas_price_variance"]:
                features[name] = 0.0
            return features
        
        # Counters
        incoming = 0
        outgoing = 0
        self_transfers = 0
        contract_calls = 0
        failed = 0
        gas_prices = []
        
        for tx in transactions:
            # Direction
            if tx.get("to", "").lower() == address:
                incoming += 1
            elif tx.get("from", "").lower() == address:
                outgoing += 1
            
            # Self-transfer
            if tx.get("from", "").lower() == address and tx.get("to", "").lower() == address:
                self_transfers += 1
            
            # Contract interaction (has input data)
            if tx.get("input") and tx.get("input") != "0x":
                contract_calls += 1
            
            # Failed transactions
            if tx.get("status") == 0 or tx.get("is_error"):
                failed += 1
            
            # Gas price
            gas_price = tx.get("gas_price", 0)
            if gas_price:
                gas_prices.append(float(gas_price) / 1e9)  # Convert to gwei
        
        total = len(transactions)
        features["in_out_ratio"] = incoming / total if total > 0 else 0.5
        features["self_transfer_ratio"] = self_transfers / total if total > 0 else 0.0
        features["contract_interaction_ratio"] = contract_calls / total if total > 0 else 0.0
        features["failed_tx_ratio"] = failed / total if total > 0 else 0.0
        
        if gas_prices:
            features["avg_gas_price_gwei"] = sum(gas_prices) / len(gas_prices)
            mean = features["avg_gas_price_gwei"]
            variance = sum((x - mean) ** 2 for x in gas_prices) / len(gas_prices)
            features["gas_price_variance"] = variance
        else:
            features["avg_gas_price_gwei"] = 0.0
            features["gas_price_variance"] = 0.0
        
        return features
    
    def _extract_network(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract network/counterparty metrics."""
        features = {}
        transactions = data.get("transactions", [])
        address = data.get("address", "").lower()
        
        if not transactions:
            for name in ["unique_senders", "unique_receivers", 
                        "counterparty_concentration", "new_counterparty_ratio"]:
                features[name] = 0.0
            return features
        
        senders = set()
        receivers = set()
        counterparty_counts = {}
        
        for tx in transactions:
            from_addr = tx.get("from", "").lower()
            to_addr = tx.get("to", "").lower()
            
            if to_addr == address and from_addr:
                senders.add(from_addr)
                counterparty_counts[from_addr] = counterparty_counts.get(from_addr, 0) + 1
            elif from_addr == address and to_addr:
                receivers.add(to_addr)
                counterparty_counts[to_addr] = counterparty_counts.get(to_addr, 0) + 1
        
        features["unique_senders"] = float(len(senders))
        features["unique_receivers"] = float(len(receivers))
        
        # Concentration: How much activity is with top counterparty
        if counterparty_counts:
            max_count = max(counterparty_counts.values())
            total = sum(counterparty_counts.values())
            features["counterparty_concentration"] = max_count / total if total > 0 else 0.0
        else:
            features["counterparty_concentration"] = 0.0
        
        # New counterparty ratio (simplified - would need historical data)
        unique_counterparties = len(senders | receivers)
        features["new_counterparty_ratio"] = 1.0 if unique_counterparties <= 5 else 0.5
        
        return features
    
    def _extract_temporal(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract time-based pattern metrics."""
        features = {}
        transactions = data.get("transactions", [])
        
        if not transactions:
            for name in ["active_hours_entropy", "weekend_tx_ratio", 
                        "night_tx_ratio", "burst_score"]:
                features[name] = 0.0
            return features
        
        hour_counts = [0] * 24
        weekend_count = 0
        night_count = 0
        
        for tx in transactions:
            timestamp = tx.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                
                hour = timestamp.hour
                hour_counts[hour] += 1
                
                # Weekend (Saturday=5, Sunday=6)
                if timestamp.weekday() >= 5:
                    weekend_count += 1
                
                # Night (10 PM - 6 AM)
                if hour >= 22 or hour < 6:
                    night_count += 1
        
        total = len(transactions)
        
        # Entropy of active hours (bots tend to be uniform, humans have patterns)
        total_counts = sum(hour_counts)
        if total_counts > 0:
            probs = [c / total_counts for c in hour_counts if c > 0]
            entropy = -sum(p * math.log2(p) for p in probs) if probs else 0
            max_entropy = math.log2(24)
            features["active_hours_entropy"] = entropy / max_entropy if max_entropy > 0 else 0
        else:
            features["active_hours_entropy"] = 0.0
        
        features["weekend_tx_ratio"] = weekend_count / total if total > 0 else 0.0
        features["night_tx_ratio"] = night_count / total if total > 0 else 0.0
        
        # Burst score (simplified - high activity in short windows)
        max_hour = max(hour_counts) if hour_counts else 0
        features["burst_score"] = max_hour / total if total > 0 else 0.0
        
        return features
    
    def _extract_risk_signals(
        self, 
        data: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract known risk signal indicators."""
        features = {}
        transactions = data.get("transactions", [])
        
        # Import known patterns
        from app.services.risk.config import risk_config
        mixer_contracts = risk_config.known_patterns.mixer_contracts
        
        mixer_count = 0
        new_contract_count = 0
        round_number_count = 0
        dust_count = 0
        
        for tx in transactions:
            to_addr = tx.get("to", "").lower()
            value = float(tx.get("value", 0))
            
            # Mixer interaction
            if to_addr in mixer_contracts:
                mixer_count += 1
            
            # Contract creation (to is empty/null)
            if not to_addr or to_addr == "0x" or to_addr == "":
                new_contract_count += 1
            
            # Round numbers (exactly 1, 10, 100 ETH etc.)
            if value > 0:
                # Check if it's a round number
                if value in [0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000]:
                    round_number_count += 1
            
            # Dust transactions (very small amounts)
            if 0 < value < 0.001:
                dust_count += 1
        
        total = len(transactions) or 1
        features["mixer_interaction_count"] = float(mixer_count)
        features["new_contract_interaction_count"] = float(new_contract_count)
        features["round_number_tx_ratio"] = round_number_count / total
        features["dust_tx_ratio"] = dust_count / total
        
        return features


class TransactionFeatureExtractor:
    """
    Extracts features from a single transaction for risk assessment.
    
    Designed for real-time transaction screening.
    """
    
    FEATURE_NAMES = [
        # Basic (5)
        "value_eth",
        "value_log",
        "gas_price_gwei",
        "gas_limit",
        "gas_used_ratio",
        
        # Context (4)
        "sender_age_hours",
        "receiver_age_hours",
        "sender_tx_count",
        "receiver_tx_count",
        
        # Pattern (4)
        "is_contract_call",
        "is_contract_creation",
        "is_round_number",
        "value_percentile",
        
        # Risk (3)
        "is_to_new_address",
        "is_to_mixer",
        "is_high_value_new_sender",
    ]
    
    def __init__(self):
        self.logger = logger.bind(module="tx_feature_extractor")
    
    def extract(
        self, 
        tx_data: Dict[str, Any],
        sender_data: Optional[Dict[str, Any]] = None,
        receiver_data: Optional[Dict[str, Any]] = None
    ) -> FeatureVector:
        """
        Extract features from transaction.
        
        Args:
            tx_data: Transaction data
            sender_data: Optional sender wallet data
            receiver_data: Optional receiver wallet data
        """
        features = {}
        missing = []
        
        try:
            features.update(self._extract_basic(tx_data, missing))
            features.update(self._extract_context(tx_data, sender_data, receiver_data, missing))
            features.update(self._extract_patterns(tx_data, missing))
            features.update(self._extract_risk(tx_data, sender_data, receiver_data, missing))
        except Exception as e:
            self.logger.error("tx_feature_extraction_failed", error=str(e))
        
        return FeatureVector(
            features=features,
            metadata={
                "tx_hash": tx_data.get("hash"),
                "extracted_at": datetime.utcnow().isoformat(),
            },
            missing=missing
        )
    
    def _extract_basic(
        self, 
        tx: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract basic transaction metrics."""
        value = float(tx.get("value", 0))
        gas_price = float(tx.get("gas_price", 0)) / 1e9
        gas_limit = float(tx.get("gas", 0))
        gas_used = float(tx.get("gas_used", gas_limit))
        
        return {
            "value_eth": value,
            "value_log": math.log1p(value),
            "gas_price_gwei": gas_price,
            "gas_limit": gas_limit,
            "gas_used_ratio": gas_used / gas_limit if gas_limit > 0 else 0.0,
        }
    
    def _extract_context(
        self,
        tx: Dict[str, Any],
        sender: Optional[Dict[str, Any]],
        receiver: Optional[Dict[str, Any]],
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract context from sender/receiver."""
        features = {}
        
        if sender:
            features["sender_age_hours"] = sender.get("age_hours", 0.0)
            features["sender_tx_count"] = float(len(sender.get("transactions", [])))
        else:
            features["sender_age_hours"] = 0.0
            features["sender_tx_count"] = 0.0
            missing.extend(["sender_age_hours", "sender_tx_count"])
        
        if receiver:
            features["receiver_age_hours"] = receiver.get("age_hours", 0.0)
            features["receiver_tx_count"] = float(len(receiver.get("transactions", [])))
        else:
            features["receiver_age_hours"] = 0.0
            features["receiver_tx_count"] = 0.0
            missing.extend(["receiver_age_hours", "receiver_tx_count"])
        
        return features
    
    def _extract_patterns(
        self, 
        tx: Dict[str, Any], 
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract transaction patterns."""
        value = float(tx.get("value", 0))
        input_data = tx.get("input", "0x")
        to_addr = tx.get("to", "")
        
        return {
            "is_contract_call": 1.0 if input_data and input_data != "0x" else 0.0,
            "is_contract_creation": 1.0 if not to_addr else 0.0,
            "is_round_number": 1.0 if value in [0.1, 0.5, 1, 5, 10, 50, 100, 500, 1000] else 0.0,
            "value_percentile": min(value / 100, 1.0),  # Normalized, cap at 100 ETH
        }
    
    def _extract_risk(
        self,
        tx: Dict[str, Any],
        sender: Optional[Dict[str, Any]],
        receiver: Optional[Dict[str, Any]],
        missing: List[str]
    ) -> Dict[str, float]:
        """Extract risk signal features."""
        from app.services.risk.config import risk_config
        
        to_addr = tx.get("to", "").lower()
        value = float(tx.get("value", 0))
        
        # New address check
        is_new = 0.0
        if receiver:
            age = receiver.get("age_hours", 0)
            if age < 24:
                is_new = 1.0
        
        # Mixer check
        is_mixer = 1.0 if to_addr in risk_config.known_patterns.mixer_contracts else 0.0
        
        # High value from new sender
        is_high_value_new = 0.0
        if sender:
            sender_age = sender.get("age_hours", 0)
            if sender_age < 24 and value > 10:
                is_high_value_new = 1.0
        
        return {
            "is_to_new_address": is_new,
            "is_to_mixer": is_mixer,
            "is_high_value_new_sender": is_high_value_new,
        }
