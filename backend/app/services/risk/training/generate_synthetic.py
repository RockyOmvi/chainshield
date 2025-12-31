"""
ChainShield Synthetic Data Generator

Generates realistic synthetic blockchain wallet data for training ML models.
Creates both fraudulent and legitimate wallet profiles with known patterns.

Design Philosophy:
1. Fraud patterns should match real-world behaviors (mixers, rug pulls, phishing)
2. Legitimate wallets should have realistic transaction patterns
3. Feature distributions should mimic actual blockchain data
"""

import random
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import json
import structlog

from app.services.risk.features import WalletFeatureExtractor

logger = structlog.get_logger()


@dataclass
class SyntheticWallet:
    """A synthetic wallet with computed features."""
    address: str
    is_fraud: bool
    fraud_type: str  # "legit", "mixer", "rugpull", "phishing", "honeypot", "new_suspicious"
    features: Dict[str, float]
    raw_data: Dict[str, Any]


class SyntheticDataGenerator:
    """
    Generates synthetic blockchain data for ML training.
    
    Creates balanced datasets with realistic fraud patterns.
    """
    
    # Fraud type distribution
    FRAUD_TYPES = {
        "mixer": 0.25,        # Uses mixers like Tornado Cash
        "rugpull": 0.25,      # Drains funds quickly  
        "phishing": 0.20,     # Abnormal approval patterns
        "honeypot": 0.15,     # In/out imbalance
        "new_suspicious": 0.15,  # New account, high activity
    }
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed for reproducibility."""
        random.seed(seed)
        self.extractor = WalletFeatureExtractor()
        self.logger = logger.bind(module="synthetic_generator")
    
    def generate_dataset(
        self,
        n_samples: int = 10000,
        fraud_ratio: float = 0.3
    ) -> Tuple[List[List[float]], List[int], List[str]]:
        """
        Generate a complete training dataset.
        
        Args:
            n_samples: Total number of samples
            fraud_ratio: Proportion that should be fraud (0.0-1.0)
            
        Returns:
            Tuple of (feature_matrix, labels, feature_names)
        """
        n_fraud = int(n_samples * fraud_ratio)
        n_legit = n_samples - n_fraud
        
        self.logger.info(
            "generating_dataset",
            total=n_samples,
            fraud=n_fraud,
            legit=n_legit
        )
        
        wallets = []
        
        # Generate legitimate wallets
        for i in range(n_legit):
            wallet = self._generate_legit_wallet(f"0xlegit_{i:08x}")
            wallets.append(wallet)
        
        # Generate fraud wallets
        fraud_types = list(self.FRAUD_TYPES.keys())
        fraud_weights = list(self.FRAUD_TYPES.values())
        
        for i in range(n_fraud):
            fraud_type = random.choices(fraud_types, weights=fraud_weights)[0]
            wallet = self._generate_fraud_wallet(f"0xfraud_{i:08x}", fraud_type)
            wallets.append(wallet)
        
        # Shuffle
        random.shuffle(wallets)
        
        # Extract features
        feature_names = WalletFeatureExtractor.FEATURE_NAMES
        feature_matrix = []
        labels = []
        
        for wallet in wallets:
            features = [wallet.features.get(name, 0.0) for name in feature_names]
            feature_matrix.append(features)
            labels.append(1 if wallet.is_fraud else 0)
        
        self.logger.info(
            "dataset_generated",
            samples=len(wallets),
            features=len(feature_names)
        )
        
        return feature_matrix, labels, feature_names
    
    def _generate_legit_wallet(self, address: str) -> SyntheticWallet:
        """Generate a legitimate wallet profile."""
        # Age: typically older accounts (30 days to 2 years)
        age_hours = random.uniform(720, 17520)  # 30 days to 2 years
        age_days = age_hours / 24
        
        # Balance: reasonable amounts
        balance_eth = random.lognormvariate(1, 2)  # Log-normal distribution
        balance_eth = max(0.01, min(balance_eth, 1000))
        
        # Transaction count: grows with age
        tx_per_day = random.uniform(0.1, 2)
        tx_count = int(age_days * tx_per_day)
        tx_count = max(1, min(tx_count, 500))
        
        # Volume: proportional to activity
        total_received = balance_eth + random.uniform(0, balance_eth * 5)
        total_sent = total_received - balance_eth
        
        # Behavioral features - legitimate patterns
        features = {
            # Basic
            "age_hours": age_hours,
            "age_days": age_days,
            "balance_eth": balance_eth,
            "balance_log": math.log1p(balance_eth),
            "tx_count_total": float(tx_count),
            
            # Volume
            "total_received_eth": total_received,
            "total_received_log": math.log1p(total_received),
            "total_sent_eth": total_sent,
            "total_sent_log": math.log1p(total_sent),
            "volume_24h_eth": random.uniform(0, balance_eth * 0.2),
            "volume_24h_log": 0.0,
            "volume_7d_eth": random.uniform(0, balance_eth * 0.5),
            "max_tx_value_eth": random.uniform(balance_eth * 0.1, balance_eth * 2),
            
            # Velocity - normal patterns
            "tx_per_hour_avg": tx_count / age_hours if age_hours > 0 else 0,
            "tx_per_hour_max": random.uniform(0.5, 3),
            "tx_per_day_avg": tx_count / age_days if age_days > 0 else 0,
            "volume_velocity": random.uniform(0, 0.5),
            "tx_count_24h": random.randint(0, 5),
            
            # Behavior - legitimate patterns
            "in_out_ratio": random.uniform(0.4, 0.6),  # Balanced
            "self_transfer_ratio": random.uniform(0, 0.05),
            "contract_interaction_ratio": random.uniform(0.1, 0.4),
            "unique_senders": random.randint(3, 50),
            "unique_receivers": random.randint(3, 50),
            "failed_tx_ratio": random.uniform(0, 0.05),
            
            # Network
            "counterparty_concentration": random.uniform(0.1, 0.4),
            "avg_counterparty_age_hours": random.uniform(age_hours * 0.5, age_hours * 2),
            
            # Temporal - normal human patterns
            "active_hours_entropy": random.uniform(0.5, 0.8),  # Natural variation
            "weekend_tx_ratio": random.uniform(0.2, 0.35),
            "night_tx_ratio": random.uniform(0.1, 0.3),
            "burst_score": random.uniform(0, 0.3),
            
            # Risk signals - none for legitimate
            "mixer_interaction_count": 0,
            "new_contract_interaction_count": random.randint(0, 5),
            "round_number_tx_ratio": random.uniform(0.05, 0.15),
            "dust_tx_ratio": random.uniform(0, 0.02),
        }
        
        return SyntheticWallet(
            address=address,
            is_fraud=False,
            fraud_type="legit",
            features=features,
            raw_data={"generated": True}
        )
    
    def _generate_fraud_wallet(self, address: str, fraud_type: str) -> SyntheticWallet:
        """Generate a fraudulent wallet profile."""
        if fraud_type == "mixer":
            return self._generate_mixer_wallet(address)
        elif fraud_type == "rugpull":
            return self._generate_rugpull_wallet(address)
        elif fraud_type == "phishing":
            return self._generate_phishing_wallet(address)
        elif fraud_type == "honeypot":
            return self._generate_honeypot_wallet(address)
        else:
            return self._generate_new_suspicious_wallet(address)
    
    def _generate_mixer_wallet(self, address: str) -> SyntheticWallet:
        """Generate a wallet that uses mixers."""
        age_hours = random.uniform(24, 720)  # 1-30 days
        
        features = self._base_features(age_hours)
        
        # Key indicator: mixer interactions
        features["mixer_interaction_count"] = random.randint(1, 10)
        
        # High velocity around mixer usage
        features["tx_per_hour_avg"] = random.uniform(2, 10)
        features["volume_velocity"] = random.uniform(0.5, 2)
        
        # Round numbers (privacy conscious)
        features["round_number_tx_ratio"] = random.uniform(0.4, 0.8)
        
        # Low entropy (programmatic timing)
        features["active_hours_entropy"] = random.uniform(0.1, 0.4)
        
        return SyntheticWallet(
            address=address,
            is_fraud=True,
            fraud_type="mixer",
            features=features,
            raw_data={"generated": True}
        )
    
    def _generate_rugpull_wallet(self, address: str) -> SyntheticWallet:
        """Generate a rug pull pattern wallet."""
        age_hours = random.uniform(1, 48)  # Very new
        
        features = self._base_features(age_hours)
        
        # Key indicator: receive a lot, send everything out quickly
        features["total_received_eth"] = random.uniform(50, 500)
        features["total_sent_eth"] = features["total_received_eth"] * random.uniform(0.9, 0.99)
        features["balance_eth"] = features["total_received_eth"] - features["total_sent_eth"]
        
        # Extreme in/out imbalance
        features["in_out_ratio"] = random.uniform(0.85, 0.99)  # Almost all outbound
        
        # Very high velocity
        features["tx_per_hour_avg"] = random.uniform(10, 50)
        features["volume_velocity"] = random.uniform(2, 10)
        
        # Many senders, few receivers
        features["unique_senders"] = random.randint(50, 500)
        features["unique_receivers"] = random.randint(1, 5)
        
        # High counterparty concentration (exit address)
        features["counterparty_concentration"] = random.uniform(0.7, 0.95)
        
        return SyntheticWallet(
            address=address,
            is_fraud=True,
            fraud_type="rugpull",
            features=features,
            raw_data={"generated": True}
        )
    
    def _generate_phishing_wallet(self, address: str) -> SyntheticWallet:
        """Generate a phishing pattern wallet."""
        age_hours = random.uniform(24, 168)  # 1-7 days
        
        features = self._base_features(age_hours)
        
        # Lots of small transactions
        features["tx_count_total"] = random.uniform(50, 500)
        features["dust_tx_ratio"] = random.uniform(0.3, 0.7)
        
        # Contract interactions (approval exploits)
        features["contract_interaction_ratio"] = random.uniform(0.7, 0.95)
        features["new_contract_interaction_count"] = random.randint(10, 100)
        
        # Bot-like timing
        features["active_hours_entropy"] = random.uniform(0.05, 0.2)
        features["burst_score"] = random.uniform(0.6, 0.95)
        
        return SyntheticWallet(
            address=address,
            is_fraud=True,
            fraud_type="phishing",
            features=features,
            raw_data={"generated": True}
        )
    
    def _generate_honeypot_wallet(self, address: str) -> SyntheticWallet:
        """Generate a honeypot pattern wallet."""
        age_hours = random.uniform(48, 720)
        
        features = self._base_features(age_hours)
        
        # Key indicator: lots of receives, almost no sends
        features["total_received_eth"] = random.uniform(10, 200)
        features["total_sent_eth"] = features["total_received_eth"] * random.uniform(0.01, 0.1)
        
        # Extreme imbalance
        features["in_out_ratio"] = random.uniform(0.01, 0.15)
        
        # High failed transaction ratio
        features["failed_tx_ratio"] = random.uniform(0.3, 0.7)
        
        # Many unique senders (victims)
        features["unique_senders"] = random.randint(20, 200)
        features["unique_receivers"] = random.randint(1, 3)
        
        return SyntheticWallet(
            address=address,
            is_fraud=True,
            fraud_type="honeypot",
            features=features,
            raw_data={"generated": True}
        )
    
    def _generate_new_suspicious_wallet(self, address: str) -> SyntheticWallet:
        """Generate a new account with suspicious activity."""
        age_hours = random.uniform(1, 24)  # Very new
        
        features = self._base_features(age_hours)
        
        # New but very active
        features["tx_count_total"] = random.uniform(20, 100)
        features["tx_per_hour_avg"] = features["tx_count_total"] / age_hours
        
        # High volume for new account
        features["volume_24h_eth"] = random.uniform(10, 100)
        
        # Bot-like behavior
        features["active_hours_entropy"] = random.uniform(0.05, 0.2)
        
        return SyntheticWallet(
            address=address,
            is_fraud=True,
            fraud_type="new_suspicious",
            features=features,
            raw_data={"generated": True}
        )
    
    def _base_features(self, age_hours: float) -> Dict[str, float]:
        """Generate base features for any wallet."""
        age_days = age_hours / 24
        balance_eth = random.lognormvariate(1, 2)
        
        return {
            # Basic
            "age_hours": age_hours,
            "age_days": age_days,
            "balance_eth": balance_eth,
            "balance_log": math.log1p(balance_eth),
            "tx_count_total": random.uniform(5, 50),
            
            # Volume
            "total_received_eth": balance_eth * random.uniform(1, 5),
            "total_received_log": 0.0,
            "total_sent_eth": balance_eth * random.uniform(0, 3),
            "total_sent_log": 0.0,
            "volume_24h_eth": random.uniform(0, balance_eth),
            "volume_24h_log": 0.0,
            "volume_7d_eth": random.uniform(0, balance_eth * 3),
            "max_tx_value_eth": random.uniform(0.1, balance_eth * 2),
            
            # Velocity
            "tx_per_hour_avg": random.uniform(0.1, 2),
            "tx_per_hour_max": random.uniform(1, 5),
            "tx_per_day_avg": random.uniform(1, 10),
            "volume_velocity": random.uniform(0, 1),
            "tx_count_24h": random.randint(0, 10),
            
            # Behavior
            "in_out_ratio": random.uniform(0.3, 0.7),
            "self_transfer_ratio": random.uniform(0, 0.1),
            "contract_interaction_ratio": random.uniform(0, 0.5),
            "unique_senders": random.randint(1, 20),
            "unique_receivers": random.randint(1, 20),
            "failed_tx_ratio": random.uniform(0, 0.2),
            
            # Network
            "counterparty_concentration": random.uniform(0.1, 0.5),
            "avg_counterparty_age_hours": random.uniform(100, 10000),
            
            # Temporal
            "active_hours_entropy": random.uniform(0.3, 0.7),
            "weekend_tx_ratio": random.uniform(0.15, 0.4),
            "night_tx_ratio": random.uniform(0.1, 0.4),
            "burst_score": random.uniform(0, 0.5),
            
            # Risk signals
            "mixer_interaction_count": 0,
            "new_contract_interaction_count": random.randint(0, 10),
            "round_number_tx_ratio": random.uniform(0, 0.3),
            "dust_tx_ratio": random.uniform(0, 0.1),
        }
    
    def save_dataset(
        self,
        feature_matrix: List[List[float]],
        labels: List[int],
        feature_names: List[str],
        output_path: str
    ) -> None:
        """Save dataset to JSON file."""
        data = {
            "feature_names": feature_names,
            "n_samples": len(labels),
            "n_fraud": sum(labels),
            "n_legit": len(labels) - sum(labels),
            "samples": [
                {"features": features, "label": label}
                for features, label in zip(feature_matrix, labels)
            ]
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f)
        
        self.logger.info("dataset_saved", path=output_path)


if __name__ == "__main__":
    # Quick test
    generator = SyntheticDataGenerator()
    X, y, names = generator.generate_dataset(n_samples=100)
    print(f"Generated {len(X)} samples with {len(names)} features")
    print(f"Fraud: {sum(y)}, Legit: {len(y) - sum(y)}")
