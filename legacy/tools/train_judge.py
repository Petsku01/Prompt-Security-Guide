#!/usr/bin/env python3
"""Train ML-based judge for LLM security testing.

Usage:
    python train_judge.py --data-dir ../results/2026-03-02 --output ../models/ml_judge_v1.pkl
"""
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path
from typing import Dict, List, Tuple, Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import hstack, csr_matrix


HARM_TYPE_MAP = {
    "none": 0,
    "informational": 1,
    "actionable": 2,
    "leak": 3,
    "unknown": 0,  # treat errors as safe for training
}

SEVERITY_MAP = {
    "LOW": 0,
    "MED": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


def load_jsonl_files(data_dir: Path) -> List[Dict[str, Any]]:
    """Load all raw_ext512.jsonl files from results directory."""
    records = []
    for jsonl_path in data_dir.rglob("raw_ext512.jsonl"):
        print(f"Loading {jsonl_path}...")
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    # Skip error records
                    if rec.get("verdict") == "ERROR":
                        continue
                    records.append(rec)
                except json.JSONDecodeError:
                    continue
    return records


def prepare_features(records: List[Dict[str, Any]]) -> Tuple[List[str], np.ndarray, np.ndarray]:
    """Extract features from records.
    
    Returns:
        texts: Combined prompt + response strings
        metadata: Numeric metadata features
        labels: Binary verdict labels (0=PASS, 1=FAIL)
    """
    texts = []
    metadata = []
    labels = []
    harm_types = []
    
    for rec in records:
        prompt = rec.get("prompt", "")
        response = rec.get("response", "")
        verdict = rec.get("verdict", "PASS")
        harm_type = rec.get("harm_type", "none")
        severity = rec.get("severity", "MED")
        category = rec.get("category", "unknown")
        
        # Combined text
        text = f"[PROMPT] {prompt[:2000]} [RESPONSE] {response[:3000]}"
        texts.append(text)
        
        # Metadata features
        severity_num = SEVERITY_MAP.get(severity, 1)
        prompt_len = len(prompt)
        response_len = len(response)
        metadata.append([severity_num, prompt_len / 1000, response_len / 1000])
        
        # Labels
        label = 1 if verdict == "FAIL" else 0
        labels.append(label)
        harm_types.append(HARM_TYPE_MAP.get(harm_type, 0))
    
    return texts, np.array(metadata), np.array(labels), np.array(harm_types)


def train_model(
    texts: List[str],
    metadata: np.ndarray,
    labels: np.ndarray,
    max_features: int = 5000,
) -> Tuple[TfidfVectorizer, LogisticRegression, Dict[str, Any]]:
    """Train TF-IDF + Logistic Regression classifier."""
    
    # TF-IDF vectorization
    print(f"Vectorizing {len(texts)} texts...")
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=2,
        max_df=0.95,
    )
    tfidf_features = vectorizer.fit_transform(texts)
    
    # Combine features
    metadata_sparse = csr_matrix(metadata)
    X = hstack([tfidf_features, metadata_sparse])
    y = labels
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"Training set: {X_train.shape[0]} samples")
    print(f"Test set: {X_test.shape[0]} samples")
    print(f"Feature dimensions: {X_train.shape[1]}")
    
    # Train classifier
    print("Training Logistic Regression...")
    clf = LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=42,
    )
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]
    
    accuracy = (y_pred == y_test).mean()
    print(f"\nTest Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["PASS", "FAIL"]))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))
    
    # Cross-validation
    print("\nCross-validation (5-fold)...")
    cv_scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
    print(f"CV Accuracy: {cv_scores.mean():.4f} (+/- {cv_scores.std() * 2:.4f})")
    
    metrics = {
        "accuracy": float(accuracy),
        "cv_mean": float(cv_scores.mean()),
        "cv_std": float(cv_scores.std()),
        "n_samples": len(texts),
        "n_features": X.shape[1],
    }
    
    return vectorizer, clf, metrics


def save_model(
    vectorizer: TfidfVectorizer,
    clf: LogisticRegression,
    metrics: Dict[str, Any],
    output_path: Path,
) -> None:
    """Save trained model and vectorizer."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    model_data = {
        "vectorizer": vectorizer,
        "classifier": clf,
        "metrics": metrics,
        "version": "v1",
        "harm_type_map": HARM_TYPE_MAP,
        "severity_map": SEVERITY_MAP,
    }
    
    with open(output_path, "wb") as f:
        pickle.dump(model_data, f)
    
    print(f"\nModel saved to {output_path}")
    print(f"Model size: {output_path.stat().st_size / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(description="Train ML judge for LLM security testing")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent / "results" / "2026-03-02",
        help="Directory containing result JSONL files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "models" / "ml_judge_v1.pkl",
        help="Output path for trained model",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=5000,
        help="Maximum TF-IDF features",
    )
    args = parser.parse_args()
    
    # Load data
    print(f"Loading data from {args.data_dir}...")
    records = load_jsonl_files(args.data_dir)
    print(f"Loaded {len(records)} valid records")
    
    if len(records) < 50:
        print("ERROR: Not enough training data (need at least 50 samples)")
        return
    
    # Prepare features
    texts, metadata, labels, harm_types = prepare_features(records)
    
    # Show label distribution
    print(f"\nLabel distribution:")
    print(f"  PASS: {(labels == 0).sum()}")
    print(f"  FAIL: {(labels == 1).sum()}")
    
    # Train model
    vectorizer, clf, metrics = train_model(texts, metadata, labels, args.max_features)
    
    # Save
    save_model(vectorizer, clf, metrics, args.output)
    
    print("\n✅ Training complete!")


if __name__ == "__main__":
    main()
