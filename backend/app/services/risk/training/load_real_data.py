"""
ChainShield Real Data Loader

Loads and processes real fraud datasets from Kaggle for training.
Supports multiple dataset formats and combines them into unified training set.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()


class RealDataLoader:
    """
    Loads real fraud datasets from Kaggle.
    
    Supported Datasets:
    1. Ethereum Transaction Dataset (FLAG column)
    2. Bitcoin Scam Detection Dataset
    3. Exchange Data (2018/2024)
    """
    
    # Feature mapping: dataset columns -> our model features
    FEATURE_MAPPING = {
        # From Dataset-3 (transaction_dataset.csv)
        "Avg min between sent tnx": "tx_per_hour_avg",  # Inverse
        "Avg min between received tnx": "tx_per_hour_avg",
        "Time Diff between first and last (Mins)": "age_hours",  # Convert
        "Sent tnx": "tx_count_total",
        "Received Tnx": "tx_count_total",
        "avg val sent": "max_tx_value_eth",
        "avg val received": "total_received_eth",
        "total Ether sent": "total_sent_eth",
        "total ether received": "total_received_eth",
        "total ether balance": "balance_eth",
        "Unique Sent To Addresses": "unique_receivers",
        "Unique Received From Addresses": "unique_senders",
        "total ERC20 tnxs": "contract_interaction_ratio",
        "ERC20 total Ether received": "total_received_eth",
        "ERC20 total ether sent": "total_sent_eth",
        "ERC20 uniq sent addr": "unique_receivers",
        "ERC20 uniq rec addr": "unique_senders",
    }
    
    def __init__(self, data_dir: str = "d:/project"):
        """Initialize loader with data directory."""
        self.data_dir = Path(data_dir)
        self.logger = logger.bind(module="real_data_loader")
    
    def load_all_datasets(self) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Load all available datasets and combine.
        
        Returns:
            Tuple of (X, y, feature_names)
        """
        all_X = []
        all_y = []
        
        # Load Dataset 3 - Transaction data (best for our use case)
        X3, y3, names = self._load_transaction_dataset()
        if X3 is not None:
            all_X.append(X3)
            all_y.extend(y3)
            self.logger.info("loaded_transaction_dataset", samples=len(y3))
        
        # Load Dataset 1 - 2018 data
        X1, y1 = self._load_2018_dataset(names)
        if X1 is not None:
            all_X.append(X1)
            all_y.extend(y1)
            self.logger.info("loaded_2018_dataset", samples=len(y1))
        
        if not all_X:
            raise ValueError("No datasets could be loaded")
        
        # Combine
        X = np.vstack(all_X)
        y = np.array(all_y)
        
        self.logger.info(
            "datasets_combined",
            total_samples=len(y),
            fraud_count=sum(y),
            legit_count=len(y) - sum(y)
        )
        
        return X, y, names
    
    def _load_transaction_dataset(self) -> Tuple[Optional[np.ndarray], List[int], List[str]]:
        """Load Ethereum transaction dataset (Dataset 3)."""
        path = self.data_dir / "dataset-3" / "transaction_dataset.csv"
        
        if not path.exists():
            self.logger.warning("transaction_dataset_not_found", path=str(path))
            return None, [], []
        
        df = pd.read_csv(path)
        
        # Target column
        if "FLAG" not in df.columns:
            self.logger.error("no_flag_column")
            return None, [], []
        
        y = df["FLAG"].values.tolist()
        
        # Select numeric features (exclude index, address, etc.)
        feature_cols = [
            col for col in df.columns 
            if col not in ["Unnamed: 0", "Index", "Address", "FLAG"] 
            and df[col].dtype in ["float64", "int64"]
        ]
        
        # Handle missing values
        X = df[feature_cols].fillna(0).values
        
        return X, y, feature_cols
    
    def _load_2018_dataset(self, target_features: List[str]) -> Tuple[Optional[np.ndarray], List[int]]:
        """Load 2018 exchange data (Dataset 1)."""
        path = self.data_dir / "dataset-1" / "data_2018" / "data_processed.csv"
        
        if not path.exists():
            return None, []
        
        df = pd.read_csv(path)
        
        # Check for label column
        if "Label" not in df.columns:
            return None, []
        
        y = df["Label"].values.tolist()
        
        # Select numeric features
        feature_cols = [
            col for col in df.columns 
            if col not in ["Unnamed: 0", "Label", "Timestamp"] 
            and df[col].dtype in ["float64", "int64"]
        ]
        
        # Pad/align features to match target
        X = df[feature_cols].fillna(0).values
        
        # If feature count doesn't match, we need to handle it
        if X.shape[1] != len(target_features):
            # Pad with zeros or truncate
            if X.shape[1] < len(target_features):
                padding = np.zeros((X.shape[0], len(target_features) - X.shape[1]))
                X = np.hstack([X, padding])
            else:
                X = X[:, :len(target_features)]
        
        return X, y
    
    def get_dataset_stats(self) -> Dict[str, Any]:
        """Get statistics about available datasets."""
        stats = {}
        
        # Dataset 3
        path3 = self.data_dir / "dataset-3" / "transaction_dataset.csv"
        if path3.exists():
            df = pd.read_csv(path3)
            stats["transaction_dataset"] = {
                "rows": len(df),
                "columns": len(df.columns),
                "fraud_count": int(df["FLAG"].sum()) if "FLAG" in df.columns else 0,
                "legit_count": int((df["FLAG"] == 0).sum()) if "FLAG" in df.columns else 0,
            }
        
        # Dataset 1
        path1 = self.data_dir / "dataset-1" / "data_2018" / "data_processed.csv"
        if path1.exists():
            df = pd.read_csv(path1)
            stats["data_2018"] = {
                "rows": len(df),
                "columns": len(df.columns),
                "fraud_count": int(df["Label"].sum()) if "Label" in df.columns else 0,
                "legit_count": int((df["Label"] == 0).sum()) if "Label" in df.columns else 0,
            }
        
        return stats


if __name__ == "__main__":
    loader = RealDataLoader()
    stats = loader.get_dataset_stats()
    print("Dataset Statistics:")
    for name, info in stats.items():
        print(f"  {name}: {info}")
