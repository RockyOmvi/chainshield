"""
ChainShield Training Package

Contains utilities for generating synthetic data and training ML models.
"""

from app.services.risk.training.generate_synthetic import SyntheticDataGenerator
from app.services.risk.training.train_models import ModelTrainer

__all__ = [
    "SyntheticDataGenerator",
    "ModelTrainer",
]
