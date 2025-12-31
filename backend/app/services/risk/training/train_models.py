"""
ChainShield Model Training Script

Trains and saves ML models for fraud detection:
- Random Forest Classifier (supervised)
- Isolation Forest (unsupervised anomaly detection)

Usage:
    python -m app.services.risk.training.train_models

This creates:
    models/risk_classifier_v1.pkl
    models/isolation_forest_v1.pkl
    models/preprocessor_v1.pkl
    models/model_metadata.json
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import structlog

from app.services.risk.training.generate_synthetic import SyntheticDataGenerator
from app.services.risk.ml.preprocessor import FeaturePreprocessor
from app.services.risk.features import WalletFeatureExtractor

logger = structlog.get_logger()


class ModelTrainer:
    """
    Trains and evaluates ML models for risk assessment.
    
    Training Pipeline:
    1. Generate synthetic data (or load real data)
    2. Preprocess and split data
    3. Train Random Forest classifier
    4. Train Isolation Forest anomaly detector
    5. Evaluate and save models
    """
    
    def __init__(self, output_dir: str = "models"):
        """
        Initialize trainer.
        
        Args:
            output_dir: Directory to save trained models
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger.bind(module="model_trainer")
        
        self.generator = SyntheticDataGenerator()
        self.preprocessor = FeaturePreprocessor()
        self.feature_names = WalletFeatureExtractor.FEATURE_NAMES
        
        self.classifier = None
        self.anomaly_detector = None
        self.metrics = {}
    
    def train_all(
        self,
        n_samples: int = 10000,
        fraud_ratio: float = 0.3,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train all models.
        
        Args:
            n_samples: Number of training samples
            fraud_ratio: Proportion of fraud samples
            test_size: Proportion for test split
            
        Returns:
            Dictionary with training metrics
        """
        self.logger.info(
            "training_starting",
            n_samples=n_samples,
            fraud_ratio=fraud_ratio
        )
        
        # Step 1: Generate data
        X, y, feature_names = self.generator.generate_dataset(n_samples, fraud_ratio)
        
        # Step 2: Split data
        X_train, X_test, y_train, y_test = self._train_test_split(X, y, test_size)
        
        # Step 3: Fit preprocessor
        self._fit_preprocessor(X_train)
        
        # Step 4: Transform data
        X_train_scaled = [self.preprocessor.transform(dict(zip(feature_names, x)), feature_names) 
                         for x in X_train]
        X_test_scaled = [self.preprocessor.transform(dict(zip(feature_names, x)), feature_names)
                        for x in X_test]
        
        # Step 5: Train models
        self._train_classifier(X_train_scaled, y_train)
        self._train_anomaly_detector(X_train_scaled)
        
        # Step 6: Evaluate
        self.metrics = self._evaluate(X_test_scaled, y_test)
        
        # Step 7: Save models
        self._save_all()
        
        self.logger.info("training_complete", metrics=self.metrics)
        
        return self.metrics
    
    def _train_test_split(
        self,
        X: List[List[float]],
        y: List[int],
        test_size: float
    ) -> Tuple[List, List, List, List]:
        """Simple train/test split."""
        import random
        
        indices = list(range(len(X)))
        random.shuffle(indices)
        
        split_idx = int(len(indices) * (1 - test_size))
        
        train_idx = indices[:split_idx]
        test_idx = indices[split_idx:]
        
        X_train = [X[i] for i in train_idx]
        X_test = [X[i] for i in test_idx]
        y_train = [y[i] for i in train_idx]
        y_test = [y[i] for i in test_idx]
        
        return X_train, X_test, y_train, y_test
    
    def _fit_preprocessor(self, X_train: List[List[float]]) -> None:
        """Fit preprocessor on training data."""
        # Convert to feature dictionaries
        feature_dicts = [
            dict(zip(self.feature_names, x)) for x in X_train
        ]
        self.preprocessor.fit(feature_dicts, self.feature_names)
    
    def _train_classifier(
        self, 
        X_train: List[List[float]], 
        y_train: List[int]
    ) -> None:
        """Train Random Forest classifier."""
        try:
            from sklearn.ensemble import RandomForestClassifier
            
            self.classifier = RandomForestClassifier(
                n_estimators=100,
                max_depth=15,
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight="balanced",  # Handle imbalanced data
                random_state=42,
                n_jobs=-1
            )
            
            self.classifier.fit(X_train, y_train)
            
            self.logger.info(
                "classifier_trained",
                n_estimators=100,
                n_features=len(X_train[0])
            )
            
        except ImportError:
            self.logger.error("sklearn_not_available")
            raise
    
    def _train_anomaly_detector(self, X_train: List[List[float]]) -> None:
        """Train Isolation Forest anomaly detector."""
        try:
            from sklearn.ensemble import IsolationForest
            
            self.anomaly_detector = IsolationForest(
                n_estimators=100,
                contamination=0.1,  # Expected 10% anomalies
                max_samples="auto",
                random_state=42,
                n_jobs=-1
            )
            
            self.anomaly_detector.fit(X_train)
            
            self.logger.info("anomaly_detector_trained")
            
        except ImportError:
            self.logger.error("sklearn_not_available")
            raise
    
    def _evaluate(
        self, 
        X_test: List[List[float]], 
        y_test: List[int]
    ) -> Dict[str, Any]:
        """Evaluate models on test data."""
        from sklearn.metrics import (
            accuracy_score, 
            precision_score, 
            recall_score, 
            f1_score,
            roc_auc_score,
            confusion_matrix
        )
        
        # Classifier evaluation
        y_pred = self.classifier.predict(X_test)
        y_proba = self.classifier.predict_proba(X_test)[:, 1]
        
        cm = confusion_matrix(y_test, y_pred)
        
        metrics = {
            "classifier": {
                "accuracy": round(accuracy_score(y_test, y_pred), 4),
                "precision": round(precision_score(y_test, y_pred), 4),
                "recall": round(recall_score(y_test, y_pred), 4),
                "f1_score": round(f1_score(y_test, y_pred), 4),
                "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
                "confusion_matrix": cm.tolist(),
            },
            "feature_importance": self._get_feature_importance(),
            "anomaly_detector": {
                "n_estimators": self.anomaly_detector.n_estimators,
                "contamination": self.anomaly_detector.contamination,
            }
        }
        
        self.logger.info(
            "evaluation_complete",
            accuracy=metrics["classifier"]["accuracy"],
            f1=metrics["classifier"]["f1_score"],
            auc=metrics["classifier"]["roc_auc"]
        )
        
        return metrics
    
    def _get_feature_importance(self) -> List[Tuple[str, float]]:
        """Get feature importance from classifier."""
        importances = self.classifier.feature_importances_
        paired = list(zip(self.feature_names, importances))
        return sorted(paired, key=lambda x: x[1], reverse=True)[:15]
    
    def _save_all(self) -> None:
        """Save all models and metadata."""
        import joblib
        
        # Save classifier
        classifier_path = self.output_dir / "risk_classifier_v1.pkl"
        joblib.dump(self.classifier, classifier_path)
        self.logger.info("model_saved", path=str(classifier_path))
        
        # Save anomaly detector
        anomaly_path = self.output_dir / "isolation_forest_v1.pkl"
        joblib.dump(self.anomaly_detector, anomaly_path)
        self.logger.info("model_saved", path=str(anomaly_path))
        
        # Save preprocessor
        preprocessor_path = self.output_dir / "preprocessor_v1.json"
        self.preprocessor.save(str(preprocessor_path))
        self.logger.info("preprocessor_saved", path=str(preprocessor_path))
        
        # Save metadata
        metadata = {
            "version": "1.0.0",
            "trained_at": datetime.utcnow().isoformat(),
            "feature_names": self.feature_names,
            "n_features": len(self.feature_names),
            "classifier": {
                "type": "RandomForestClassifier",
                "n_estimators": self.classifier.n_estimators,
                "max_depth": self.classifier.max_depth,
            },
            "anomaly_detector": {
                "type": "IsolationForest",
                "n_estimators": self.anomaly_detector.n_estimators,
            },
            "metrics": self.metrics,
        }
        
        metadata_path = self.output_dir / "model_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        self.logger.info("metadata_saved", path=str(metadata_path))


def main():
    """Run training pipeline."""
    print("\n" + "="*70)
    print("🧠 CHAINSHIELD ML MODEL TRAINING")
    print("="*70 + "\n")
    
    # Suppress structlog for cleaner output
    import logging
    logging.disable(logging.WARNING)
    
    trainer = ModelTrainer(output_dir="models")
    
    print("📊 Generating synthetic training data...")
    print("   - 10,000 samples (70% legit, 30% fraud)")
    print("   - 5 fraud types: mixer, rugpull, phishing, honeypot, suspicious")
    print()
    
    print("🔧 Training models...")
    metrics = trainer.train_all(n_samples=10000, fraud_ratio=0.3)
    
    print("\n" + "-"*50)
    print("📈 TRAINING RESULTS")
    print("-"*50)
    print(f"   Accuracy:  {metrics['classifier']['accuracy']*100:.1f}%")
    print(f"   Precision: {metrics['classifier']['precision']*100:.1f}%")
    print(f"   Recall:    {metrics['classifier']['recall']*100:.1f}%")
    print(f"   F1 Score:  {metrics['classifier']['f1_score']*100:.1f}%")
    print(f"   ROC AUC:   {metrics['classifier']['roc_auc']*100:.1f}%")
    
    print("\n📊 Top 5 Important Features:")
    for i, (name, importance) in enumerate(metrics['feature_importance'][:5], 1):
        print(f"   {i}. {name}: {importance:.4f}")
    
    print("\n" + "="*70)
    print("✅ MODELS SAVED TO: models/")
    print("   - risk_classifier_v1.pkl")
    print("   - isolation_forest_v1.pkl")
    print("   - preprocessor_v1.json")
    print("   - model_metadata.json")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
