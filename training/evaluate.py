#!/usr/bin/env python3
"""
Evaluate a prompt injection detector.

Usage:
    python training/evaluate.py --model output/psg-detector
"""

import argparse
import json
from pathlib import Path

try:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix,
        classification_report,
    )
except ImportError:
    print("Error: Install dependencies:")
    print("  pip install torch transformers scikit-learn")
    exit(1)


def load_data(path: Path) -> list[dict]:
    """Load JSON data file."""
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description="Evaluate prompt injection detector")
    parser.add_argument("--model", required=True, help="Model path or HuggingFace ID")
    parser.add_argument("--test-data", default="training/data/test.json")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--output", default=None, help="Save results to JSON")
    args = parser.parse_args()

    test_path = Path(args.test_data)
    if not test_path.exists():
        print(f"Error: {test_path} not found")
        exit(1)

    print(f"Loading model: {args.model}")
    classifier = pipeline(
        "text-classification",
        model=args.model,
        device=0 if torch.cuda.is_available() else -1,
    )

    print(f"Loading test data: {test_path}")
    test_data = load_data(test_path)
    
    texts = [item["text"] for item in test_data]
    true_labels = [item["label"] for item in test_data]

    print(f"Evaluating {len(texts)} examples...")
    predictions = classifier(texts, batch_size=args.batch_size, truncation=True)

    # Convert predictions to binary labels
    pred_labels = []
    for pred in predictions:
        # Handle both INJECTION/LEGIT and LABEL_1/LABEL_0 formats
        if pred["label"] in ("INJECTION", "LABEL_1"):
            pred_labels.append(1)
        else:
            pred_labels.append(0)

    # Calculate metrics
    accuracy = accuracy_score(true_labels, pred_labels)
    precision = precision_score(true_labels, pred_labels)
    recall = recall_score(true_labels, pred_labels)
    f1 = f1_score(true_labels, pred_labels)
    cm = confusion_matrix(true_labels, pred_labels)

    print("\n" + "=" * 40)
    print("Evaluation Results")
    print("=" * 40)
    print(f"Accuracy:  {accuracy:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1:        {f1:.4f}")
    print()
    print("Confusion Matrix:")
    print("              Predicted")
    print("              Clean  Injection")
    print(f"Actual Clean   {cm[0][0]:4d}      {cm[0][1]:4d}")
    print(f"       Inject  {cm[1][0]:4d}      {cm[1][1]:4d}")
    print()

    # Detailed report
    print("Classification Report:")
    print(classification_report(
        true_labels, pred_labels,
        target_names=["Clean", "Injection"],
    ))

    # Find errors
    errors = []
    for i, (text, true, pred) in enumerate(zip(texts, true_labels, pred_labels)):
        if true != pred:
            errors.append({
                "text": text[:100] + "..." if len(text) > 100 else text,
                "true": "injection" if true == 1 else "clean",
                "predicted": "injection" if pred == 1 else "clean",
            })

    if errors:
        print(f"\nErrors ({len(errors)} total):")
        for err in errors[:5]:
            print(f"  [{err['true']} -> {err['predicted']}] {err['text']}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more")

    # Save results
    if args.output:
        results = {
            "model": args.model,
            "test_data": str(test_path),
            "total_examples": len(texts),
            "metrics": {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            },
            "confusion_matrix": cm.tolist(),
            "errors": errors,
        }
        Path(args.output).write_text(json.dumps(results, indent=2))
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
