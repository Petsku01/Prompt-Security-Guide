#!/usr/bin/env python3
"""
Fine-tune a prompt injection detector.

Usage:
    python training/fine_tune.py --epochs 3 --output output/psg-detector
"""

import argparse
import json
from pathlib import Path

try:
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
        DataCollatorWithPadding,
    )
    from datasets import Dataset
except ImportError:
    print("Error: Install ML dependencies first:")
    print("  pip install torch transformers datasets")
    exit(1)


def load_data(path: Path) -> list[dict]:
    """Load JSON data file."""
    return json.loads(path.read_text())


def tokenize_function(examples, tokenizer, max_length):
    """Tokenize examples."""
    return tokenizer(
        examples["text"],
        padding=False,
        truncation=True,
        max_length=max_length,
    )


def main():
    parser = argparse.ArgumentParser(description="Fine-tune prompt injection detector")
    parser.add_argument(
        "--model",
        default="deepset/deberta-v3-base-injection",
        help="Base model to fine-tune",
    )
    parser.add_argument("--train-data", default="training/data/train.json")
    parser.add_argument("--eval-data", default="training/data/val.json")
    parser.add_argument("--output", default="output/psg-detector")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Check data exists
    train_path = Path(args.train_data)
    eval_path = Path(args.eval_data)
    if not train_path.exists():
        print(f"Error: {train_path} not found. Run prepare_data.py first.")
        exit(1)

    print(f"Loading model: {args.model}")
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model,
        num_labels=2,
        id2label={0: "LEGIT", 1: "INJECTION"},
        label2id={"LEGIT": 0, "INJECTION": 1},
    )

    # Load data
    print("Loading training data...")
    train_data = load_data(train_path)
    train_dataset = Dataset.from_list(train_data)
    
    eval_dataset = None
    if eval_path.exists():
        eval_data = load_data(eval_path)
        eval_dataset = Dataset.from_list(eval_data)

    # Tokenize
    print("Tokenizing...")
    train_dataset = train_dataset.map(
        lambda x: tokenize_function(x, tokenizer, args.max_length),
        batched=True,
        remove_columns=["text"],
    )
    if eval_dataset:
        eval_dataset = eval_dataset.map(
            lambda x: tokenize_function(x, tokenizer, args.max_length),
            batched=True,
            remove_columns=["text"],
        )

    # Training arguments
    output_dir = Path(args.output)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=args.warmup_ratio,
        weight_decay=args.weight_decay,
        logging_dir=str(output_dir / "logs"),
        logging_steps=10,
        evaluation_strategy="epoch" if eval_dataset else "no",
        save_strategy="epoch",
        load_best_model_at_end=True if eval_dataset else False,
        seed=args.seed,
        report_to=[],  # Disable wandb etc
    )

    # Data collator
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    # Trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=data_collator,
        tokenizer=tokenizer,
    )

    # Train
    print(f"\nTraining for {args.epochs} epochs...")
    print(f"  Train examples: {len(train_dataset)}")
    if eval_dataset:
        print(f"  Eval examples: {len(eval_dataset)}")
    print()

    trainer.train()

    # Save
    print(f"\nSaving model to {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    print("\nDone! ✅")
    print(f"\nTo use in PSG:")
    print(f"  export PSG_DETECTOR_MODEL={output_dir}")
    print(f"  psg defend validate 'test'")


if __name__ == "__main__":
    main()
