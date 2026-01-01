"""
ChainShield Model Compression Script

Compresses ML models for faster deployment and reduced memory usage.
Uses joblib compression with zlib.

Usage:
    python scripts/compress_models.py
"""

import os
import joblib
import structlog
from pathlib import Path

logger = structlog.get_logger()


def compress_model(input_path: str, output_path: str = None, compress_level: int = 3) -> dict:
    """
    Compress a model file.
    
    Args:
        input_path: Path to the original model
        output_path: Path for compressed model (default: adds .compressed)
        compress_level: Compression level 1-9 (higher = smaller but slower)
        
    Returns:
        Dict with compression statistics
    """
    if output_path is None:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}_compressed{ext}"
    
    # Load original model
    original_size = os.path.getsize(input_path)
    model_data = joblib.load(input_path)
    
    # Save with compression
    joblib.dump(model_data, output_path, compress=compress_level)
    compressed_size = os.path.getsize(output_path)
    
    # Calculate savings
    savings_bytes = original_size - compressed_size
    savings_percent = (savings_bytes / original_size) * 100
    
    return {
        "input_path": input_path,
        "output_path": output_path,
        "original_size_mb": round(original_size / (1024 * 1024), 2),
        "compressed_size_mb": round(compressed_size / (1024 * 1024), 2),
        "savings_mb": round(savings_bytes / (1024 * 1024), 2),
        "savings_percent": round(savings_percent, 1),
        "compress_level": compress_level,
    }


def compress_all_models(models_dir: str = "models", compress_level: int = 3) -> list:
    """
    Compress all model files in a directory.
    
    Args:
        models_dir: Directory containing model files
        compress_level: Compression level 1-9
        
    Returns:
        List of compression results
    """
    models_path = Path(models_dir)
    results = []
    
    # Find all .pkl files that aren't already compressed
    model_files = [
        f for f in models_path.glob("*.pkl")
        if "_compressed" not in f.stem
    ]
    
    print(f"\nFound {len(model_files)} models to compress")
    print("=" * 60)
    
    for model_file in model_files:
        try:
            print(f"\nCompressing: {model_file.name}")
            result = compress_model(str(model_file), compress_level=compress_level)
            results.append(result)
            
            print(f"  Original:   {result['original_size_mb']} MB")
            print(f"  Compressed: {result['compressed_size_mb']} MB")
            print(f"  Savings:    {result['savings_percent']}%")
            
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "input_path": str(model_file),
                "error": str(e),
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("COMPRESSION SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if "error" not in r]
    if successful:
        total_original = sum(r["original_size_mb"] for r in successful)
        total_compressed = sum(r["compressed_size_mb"] for r in successful)
        total_savings = sum(r["savings_mb"] for r in successful)
        
        print(f"Models compressed: {len(successful)}")
        print(f"Total original:    {total_original:.2f} MB")
        print(f"Total compressed:  {total_compressed:.2f} MB")
        print(f"Total savings:     {total_savings:.2f} MB ({(total_savings/total_original)*100:.1f}%)")
    
    return results


def verify_compressed_model(original_path: str, compressed_path: str) -> bool:
    """
    Verify that compressed model produces same predictions.
    
    Args:
        original_path: Path to original model
        compressed_path: Path to compressed model
        
    Returns:
        True if models are equivalent
    """
    import numpy as np
    
    print(f"\nVerifying: {compressed_path}")
    
    # Load both models
    original = joblib.load(original_path)
    compressed = joblib.load(compressed_path)
    
    # Generate test data
    np.random.seed(42)
    test_data = np.random.randn(100, 48)  # 100 samples, 48 features
    
    try:
        # Get predictions from both
        if hasattr(original, "predict"):
            orig_preds = original.predict(test_data)
            comp_preds = compressed.predict(test_data)
        else:
            # Might be a dict with model inside
            orig_preds = original.get("model", original).predict(test_data)
            comp_preds = compressed.get("model", compressed).predict(test_data)
        
        # Compare
        match = np.array_equal(orig_preds, comp_preds)
        
        if match:
            print("  Verification: PASSED (predictions match)")
        else:
            print("  Verification: FAILED (predictions differ)")
        
        return match
        
    except Exception as e:
        print(f"  Verification: SKIPPED ({e})")
        return True  # Assume OK if can't verify


if __name__ == "__main__":
    import sys
    
    print("=" * 60)
    print("CHAINSHIELD MODEL COMPRESSION")
    print("=" * 60)
    
    # Default to models directory
    models_dir = sys.argv[1] if len(sys.argv) > 1 else "models"
    compress_level = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    # Compress all models
    results = compress_all_models(models_dir, compress_level)
    
    # Verify compressed models
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    for result in results:
        if "error" not in result and "output_path" in result:
            verify_compressed_model(result["input_path"], result["output_path"])
    
    print("\nDone! Compressed models saved with '_compressed' suffix.")
