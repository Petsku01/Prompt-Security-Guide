#!/usr/bin/env python3
"""
Prepare training data from PSG attack catalogs.

Usage:
    python training/prepare_data.py --output data/
"""

import argparse
import json
import random
from pathlib import Path


# Clean prompts (negative examples)
CLEAN_PROMPTS = [
    "What's the weather like today?",
    "Can you help me write a Python function?",
    "Explain quantum computing in simple terms",
    "What's the capital of France?",
    "How do I make a chocolate cake?",
    "Summarize this article for me",
    "What's 2 + 2?",
    "Tell me a joke",
    "How do I fix a leaky faucet?",
    "What are the benefits of exercise?",
    "Recommend a good book to read",
    "How do I learn a new language?",
    "What's the difference between Python and JavaScript?",
    "Help me debug this code",
    "Write a poem about nature",
    "Explain machine learning",
    "What happened in World War 2?",
    "How do computers work?",
    "What's the best way to study?",
    "Can you translate this to Spanish?",
    "What are some healthy breakfast ideas?",
    "How do I start a business?",
    "Explain the theory of relativity",
    "What's the plot of Romeo and Juliet?",
    "How do I improve my writing?",
    "What programming language should I learn first?",
    "Explain how the internet works",
    "What are some good exercises for beginners?",
    "How do I manage my time better?",
    "What's the meaning of life?",
    "Can you proofread this email?",
    "What are the symptoms of a cold?",
    "How do I cook rice properly?",
    "Explain blockchain technology",
    "What's the best way to save money?",
    "How do I meditate?",
    "What causes climate change?",
    "Help me plan a trip to Japan",
    "What are some stress relief techniques?",
    "How do neural networks work?",
    "What's the history of the internet?",
    "Can you explain this math problem?",
    "What are good interview tips?",
    "How do I set up a website?",
    "What's the difference between HTTP and HTTPS?",
    "Explain how vaccines work",
    "What are some creative writing prompts?",
    "How do I negotiate a salary?",
    "What's the best coffee brewing method?",
    "Explain the stock market",
]


def load_catalog(path: Path) -> list[dict]:
    """Load attack catalog JSON."""
    data = json.loads(path.read_text())
    if isinstance(data, dict) and "attacks" in data:
        return data["attacks"]
    return data if isinstance(data, list) else []


def extract_prompts(catalog: list[dict]) -> list[str]:
    """Extract prompts from catalog."""
    prompts = []
    for item in catalog:
        prompt = item.get("prompt") or item.get("text") or ""
        if prompt:
            prompts.append(prompt)
    return prompts


def main():
    parser = argparse.ArgumentParser(description="Prepare training data")
    parser.add_argument("--datasets", default="datasets/", help="Datasets directory")
    parser.add_argument("--output", default="training/data/", help="Output directory")
    parser.add_argument("--train-ratio", type=float, default=0.8, help="Train split ratio")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    random.seed(args.seed)
    datasets_dir = Path(args.datasets)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect attack prompts (positive examples)
    attack_prompts = []
    train_catalogs = [
        "prompt_injection_techniques.json",
        "jailbreakbench_behaviors.json",
        "encoding_attacks.json",
        "jailbreak_community.json",
        "dan_jailbreaks.json",
    ]
    
    for catalog_name in train_catalogs:
        catalog_path = datasets_dir / catalog_name
        if catalog_path.exists():
            catalog = load_catalog(catalog_path)
            prompts = extract_prompts(catalog)
            attack_prompts.extend(prompts)
            print(f"Loaded {len(prompts)} attacks from {catalog_name}")

    # Evaluation catalog (held out)
    eval_catalog_path = datasets_dir / "obliteratus_attacks.json"
    eval_attacks = []
    if eval_catalog_path.exists():
        eval_attacks = extract_prompts(load_catalog(eval_catalog_path))
        print(f"Loaded {len(eval_attacks)} attacks for evaluation")

    # Generate clean prompts (negative examples)
    # Augment with variations
    clean_prompts = CLEAN_PROMPTS.copy()
    for prompt in CLEAN_PROMPTS[:20]:
        clean_prompts.append(f"Please {prompt.lower()}")
        clean_prompts.append(f"Could you {prompt.lower()}")
        clean_prompts.append(f"I need help with: {prompt}")

    print(f"Total clean prompts: {len(clean_prompts)}")
    print(f"Total attack prompts: {len(attack_prompts)}")

    # Balance dataset
    min_size = min(len(clean_prompts), len(attack_prompts))
    clean_sample = random.sample(clean_prompts, min(min_size, len(clean_prompts)))
    attack_sample = random.sample(attack_prompts, min(min_size, len(attack_prompts)))

    # Create training examples
    examples = []
    for prompt in clean_sample:
        examples.append({"text": prompt, "label": 0})
    for prompt in attack_sample:
        examples.append({"text": prompt, "label": 1})

    random.shuffle(examples)

    # Split train/eval
    split_idx = int(len(examples) * args.train_ratio)
    train_examples = examples[:split_idx]
    val_examples = examples[split_idx:]

    # Create test set from held-out attacks + clean
    test_examples = []
    for prompt in eval_attacks:
        test_examples.append({"text": prompt, "label": 1})
    test_clean = random.sample(clean_prompts, min(len(eval_attacks), len(clean_prompts)))
    for prompt in test_clean:
        test_examples.append({"text": prompt, "label": 0})
    random.shuffle(test_examples)

    # Save
    (output_dir / "train.json").write_text(json.dumps(train_examples, indent=2))
    (output_dir / "val.json").write_text(json.dumps(val_examples, indent=2))
    (output_dir / "test.json").write_text(json.dumps(test_examples, indent=2))

    print(f"\nSaved to {output_dir}/")
    print(f"  train.json: {len(train_examples)} examples")
    print(f"  val.json:   {len(val_examples)} examples")
    print(f"  test.json:  {len(test_examples)} examples")


if __name__ == "__main__":
    main()
