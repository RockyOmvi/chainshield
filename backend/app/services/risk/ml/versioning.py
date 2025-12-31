"""
ChainShield Model Versioning

Tracks model versions, metrics, and deployment history.
Enables model rollback and A/B testing.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger()


@dataclass
class ModelVersion:
    """Metadata for a model version."""
    version: str
    model_type: str
    trained_at: str
    file_path: str
    
    # Training info
    n_samples: int = 0
    fraud_ratio: float = 0.0
    
    # Metrics
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    roc_auc: float = 0.0
    
    # Status
    is_active: bool = False
    is_shadow: bool = False  # Running in shadow mode for testing
    
    # Additional metadata
    notes: str = ""
    feature_names: List[str] = field(default_factory=list)


@dataclass 
class VersionRegistry:
    """Registry of all model versions."""
    current_version: str = ""
    versions: List[ModelVersion] = field(default_factory=list)
    last_updated: str = ""


class ModelVersionManager:
    """
    Manages model versions and deployments.
    
    Features:
    1. Version tracking
    2. Active model selection
    3. Shadow mode for A/B testing
    4. Rollback support
    5. Metrics history
    """
    
    def __init__(self, registry_path: str = "models/version_registry.json"):
        """
        Initialize version manager.
        
        Args:
            registry_path: Path to version registry file
        """
        self.registry_path = Path(registry_path)
        self.logger = logger.bind(module="version_manager")
        self.registry = self._load_registry()
    
    def _load_registry(self) -> VersionRegistry:
        """Load registry from file."""
        if self.registry_path.exists():
            with open(self.registry_path, "r") as f:
                data = json.load(f)
                versions = [ModelVersion(**v) for v in data.get("versions", [])]
                return VersionRegistry(
                    current_version=data.get("current_version", ""),
                    versions=versions,
                    last_updated=data.get("last_updated", "")
                )
        return VersionRegistry()
    
    def _save_registry(self) -> None:
        """Save registry to file."""
        self.registry.last_updated = datetime.utcnow().isoformat()
        
        data = {
            "current_version": self.registry.current_version,
            "last_updated": self.registry.last_updated,
            "versions": [asdict(v) for v in self.registry.versions]
        }
        
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)
    
    def register_version(
        self,
        version: str,
        model_type: str,
        file_path: str,
        metrics: Dict[str, float],
        n_samples: int = 0,
        fraud_ratio: float = 0.0,
        feature_names: Optional[List[str]] = None,
        notes: str = ""
    ) -> ModelVersion:
        """
        Register a new model version.
        
        Args:
            version: Version string (e.g., "1.0.0")
            model_type: Type of model ("classifier", "anomaly")
            file_path: Path to model file
            metrics: Dictionary of evaluation metrics
            n_samples: Number of training samples
            fraud_ratio: Fraud ratio in training data
            feature_names: List of feature names
            notes: Optional notes
            
        Returns:
            Created ModelVersion
        """
        model_version = ModelVersion(
            version=version,
            model_type=model_type,
            trained_at=datetime.utcnow().isoformat(),
            file_path=file_path,
            n_samples=n_samples,
            fraud_ratio=fraud_ratio,
            accuracy=metrics.get("accuracy", 0),
            precision=metrics.get("precision", 0),
            recall=metrics.get("recall", 0),
            f1_score=metrics.get("f1_score", 0),
            roc_auc=metrics.get("roc_auc", 0),
            is_active=False,
            is_shadow=False,
            notes=notes,
            feature_names=feature_names or []
        )
        
        self.registry.versions.append(model_version)
        self._save_registry()
        
        self.logger.info(
            "version_registered",
            version=version,
            model_type=model_type
        )
        
        return model_version
    
    def activate_version(self, version: str) -> bool:
        """
        Set a version as the active production model.
        
        Args:
            version: Version string to activate
            
        Returns:
            True if successful
        """
        for v in self.registry.versions:
            if v.version == version:
                # Deactivate current active
                for other in self.registry.versions:
                    other.is_active = False
                
                v.is_active = True
                v.is_shadow = False
                self.registry.current_version = version
                self._save_registry()
                
                self.logger.info("version_activated", version=version)
                return True
        
        self.logger.warning("version_not_found", version=version)
        return False
    
    def enable_shadow_mode(self, version: str) -> bool:
        """
        Enable shadow mode for a version (A/B testing).
        
        Shadow mode runs the model alongside production
        without affecting actual predictions.
        """
        for v in self.registry.versions:
            if v.version == version:
                v.is_shadow = True
                self._save_registry()
                
                self.logger.info("shadow_mode_enabled", version=version)
                return True
        
        return False
    
    def rollback(self, target_version: Optional[str] = None) -> Optional[str]:
        """
        Rollback to a previous version.
        
        Args:
            target_version: Specific version to rollback to.
                          If None, rolls back to previous active.
                          
        Returns:
            Version rolled back to, or None if failed
        """
        if target_version:
            if self.activate_version(target_version):
                self.logger.info("rollback_to_version", version=target_version)
                return target_version
        else:
            # Find previous active version
            for i, v in enumerate(reversed(self.registry.versions)):
                if v.version != self.registry.current_version:
                    if self.activate_version(v.version):
                        self.logger.info("rollback_to_previous", version=v.version)
                        return v.version
        
        return None
    
    def get_active_version(self) -> Optional[ModelVersion]:
        """Get the currently active version."""
        for v in self.registry.versions:
            if v.is_active:
                return v
        return None
    
    def get_shadow_version(self) -> Optional[ModelVersion]:
        """Get the shadow mode version if any."""
        for v in self.registry.versions:
            if v.is_shadow:
                return v
        return None
    
    def get_version(self, version: str) -> Optional[ModelVersion]:
        """Get a specific version."""
        for v in self.registry.versions:
            if v.version == version:
                return v
        return None
    
    def list_versions(self) -> List[ModelVersion]:
        """List all versions."""
        return self.registry.versions
    
    def get_metrics_history(self, model_type: str = "classifier") -> List[Dict[str, Any]]:
        """Get metrics history for a model type."""
        history = []
        for v in self.registry.versions:
            if v.model_type == model_type:
                history.append({
                    "version": v.version,
                    "trained_at": v.trained_at,
                    "accuracy": v.accuracy,
                    "f1_score": v.f1_score,
                    "roc_auc": v.roc_auc,
                    "is_active": v.is_active,
                })
        return history
    
    def compare_versions(self, v1: str, v2: str) -> Dict[str, Any]:
        """Compare metrics between two versions."""
        version1 = self.get_version(v1)
        version2 = self.get_version(v2)
        
        if not version1 or not version2:
            return {"error": "Version not found"}
        
        return {
            "version_1": v1,
            "version_2": v2,
            "comparison": {
                "accuracy": {v1: version1.accuracy, v2: version2.accuracy},
                "f1_score": {v1: version1.f1_score, v2: version2.f1_score},
                "roc_auc": {v1: version1.roc_auc, v2: version2.roc_auc},
            },
            "recommendation": v1 if version1.f1_score > version2.f1_score else v2
        }
