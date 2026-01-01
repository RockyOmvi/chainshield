"""
ChainShield SMOTE Training

Balanced model training using SMOTE (Synthetic Minority Over-sampling).
Improves fraud recall by addressing class imbalance.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import structlog

logger = structlog.get_logger()


class SMOTETrainer:
    """
    Model trainer with SMOTE for class-imbalanced data.
    
    Features:
    - SMOTE oversampling for minority class
    - Cross-validation for robust estimates
    - Ensemble with balanced weights
    """
    
    def __init__(self, random_state: int = 42):
        """Initialize SMOTE trainer."""
        self.logger = logger.bind(module="smote_trainer")
        self.random_state = random_state
        self.model = None
        self.scaler = None
        self.smote = None
    
    def train_with_smote(
        self,
        X: np.ndarray,
        y: np.ndarray,
        test_size: float = 0.2
    ) -> Dict[str, Any]:
        """
        Train models with SMOTE oversampling.
        
        Args:
            X: Feature matrix
            y: Labels (0=legit, 1=fraud)
            test_size: Test split ratio
            
        Returns:
            Training results with metrics
        """
        from sklearn.model_selection import train_test_split, cross_val_score
        from sklearn.preprocessing import StandardScaler
        from sklearn.ensemble import RandomForestClassifier, VotingClassifier
        from sklearn.metrics import (
            accuracy_score, precision_score, recall_score,
            f1_score, roc_auc_score, classification_report
        )
        
        self.logger.info(
            "starting_smote_training",
            samples=len(y),
            fraud_ratio=f"{sum(y)/len(y)*100:.2f}%"
        )
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.random_state, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Apply SMOTE
        try:
            from imblearn.over_sampling import SMOTE
            self.smote = SMOTE(random_state=self.random_state, k_neighbors=5)
            X_train_resampled, y_train_resampled = self.smote.fit_resample(
                X_train_scaled, y_train
            )
            smote_applied = True
            
            self.logger.info(
                "smote_applied",
                before=len(y_train),
                after=len(y_train_resampled),
                new_fraud_ratio=f"{sum(y_train_resampled)/len(y_train_resampled)*100:.1f}%"
            )
        except ImportError:
            self.logger.warning("imblearn_not_installed_using_class_weights")
            X_train_resampled = X_train_scaled
            y_train_resampled = y_train
            smote_applied = False
        
        # Train ensemble with class weights as backup
        rf = RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            class_weight='balanced',  # Backup for class imbalance
            random_state=self.random_state,
            n_jobs=-1
        )
        
        try:
            from xgboost import XGBClassifier
            xgb = XGBClassifier(
                n_estimators=100,
                max_depth=6,
                scale_pos_weight=sum(y == 0) / max(sum(y == 1), 1),  # Class balance
                random_state=self.random_state,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            
            self.model = VotingClassifier(
                estimators=[("rf", rf), ("xgb", xgb)],
                voting="soft"
            )
        except ImportError:
            self.logger.warning("xgboost_not_available")
            self.model = rf
        
        # Train
        self.model.fit(X_train_resampled, y_train_resampled)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_prob = self.model.predict_proba(X_test_scaled)[:, 1]
        
        # Cross-validation
        cv_scores = cross_val_score(
            self.model, X_train_resampled, y_train_resampled,
            cv=5, scoring='roc_auc'
        )
        
        results = {
            "smote_applied": smote_applied,
            "train_samples": len(X_train_resampled),
            "test_samples": len(X_test),
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
            "roc_auc": roc_auc_score(y_test, y_prob),
            "cv_mean_auc": cv_scores.mean(),
            "cv_std_auc": cv_scores.std(),
        }
        
        self.logger.info(
            "smote_training_complete",
            accuracy=f"{results['accuracy']:.3f}",
            recall=f"{results['recall']:.3f}",
            roc_auc=f"{results['roc_auc']:.3f}"
        )
        
        return results
    
    def save_model(self, path: str) -> bool:
        """Save trained model."""
        import joblib
        
        if self.model is None:
            return False
        
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "smote_applied": self.smote is not None,
        }, path)
        
        self.logger.info("smote_model_saved", path=path)
        return True
    
    def load_model(self, path: str) -> bool:
        """Load trained model."""
        import joblib
        
        try:
            data = joblib.load(path)
            self.model = data["model"]
            self.scaler = data["scaler"]
            return True
        except Exception as e:
            self.logger.error("load_failed", error=str(e))
            return False
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Make predictions."""
        if self.model is None or self.scaler is None:
            raise ValueError("Model not trained")
        
        X_scaled = self.scaler.transform(X)
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)[:, 1]
        
        return predictions, probabilities


def train_smote_model_from_kaggle(
    csv_path: str,
    output_path: str = "models/smote_model.pkl"
) -> Dict[str, Any]:
    """
    Train SMOTE model from Kaggle dataset.
    
    Args:
        csv_path: Path to Kaggle transaction dataset
        output_path: Where to save trained model
    """
    print("Loading Kaggle dataset...")
    df = pd.read_csv(csv_path)
    
    # Get features and labels
    feature_cols = [
        c for c in df.columns
        if c not in ["Unnamed: 0", "Index", "Address", "FLAG"]
        and df[c].dtype in ["float64", "int64"]
    ]
    
    X = df[feature_cols].fillna(0).values
    y = df["FLAG"].values
    
    print(f"Training with {len(X)} samples, {sum(y)} fraud cases...")
    
    trainer = SMOTETrainer()
    results = trainer.train_with_smote(X, y)
    
    # Save
    trainer.save_model(output_path)
    
    print("\n" + "="*50)
    print("SMOTE TRAINING RESULTS")
    print("="*50)
    print(f"SMOTE Applied:  {results['smote_applied']}")
    print(f"Accuracy:       {results['accuracy']*100:.1f}%")
    print(f"Recall:         {results['recall']*100:.1f}%")
    print(f"Precision:      {results['precision']*100:.1f}%")
    print(f"F1 Score:       {results['f1_score']:.3f}")
    print(f"ROC AUC:        {results['roc_auc']:.3f}")
    print(f"CV Mean AUC:    {results['cv_mean_auc']:.3f} ± {results['cv_std_auc']:.3f}")
    print(f"Saved to:       {output_path}")
    
    return results


if __name__ == "__main__":
    import sys
    
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "d:/project/dataset-3/transaction_dataset.csv"
    train_smote_model_from_kaggle(csv_path)
