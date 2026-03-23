#!/usr/bin/env python3
"""
ML-based classifier using local Ollama.
Classifies prompts with better accuracy than regex.
"""
import json
import requests
from pathlib import Path
from datetime import datetime
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3:8b"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"

CLASSIFICATION_PROMPT = """Analyze this jailbreak prompt and classify it.

PROMPT:
{prompt}

Respond with ONLY a JSON object (no other text):
{{
  "target_model": "chatgpt|claude|gemini|llama|grok|deepseek|mistral|generic",
  "technique": "roleplay|dan|encoding|multi_turn|emotional|authority|fiction|technical|injection|obfuscation|novel",
  "sophistication": 1-5,
  "novelty": 1-5,
  "working_likely": true|false,
  "brief_analysis": "one sentence"
}}"""

def classify_prompt(text: str, timeout: int = 30) -> dict:
    """Classify a single prompt using Ollama."""
    prompt = CLASSIFICATION_PROMPT.format(prompt=text[:1500])
    
    try:
        resp = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 200}
        }, timeout=timeout)
        
        if resp.status_code == 200:
            result = resp.json()
            response_text = result.get('response', '')
            
            # Try to parse JSON from response
            try:
                # Find JSON in response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    return json.loads(response_text[start:end])
            except json.JSONDecodeError:
                pass
    except Exception as e:
        logger.warning(f"Classification error: {e}")
    
    return None

def main():
    logger.info("=" * 60)
    logger.info("ML CLASSIFIER STARTING")
    logger.info(f"Model: {MODEL}")
    logger.info("=" * 60)
    
    # Load top quality prompts (subset for overnight processing)
    with open(PROCESSED_DIR / "top_quality.json") as f:
        data = json.load(f)
    
    prompts = data['prompts'][:500]  # Process top 500
    logger.info(f"Processing {len(prompts)} prompts...")
    
    results = []
    for i, p in enumerate(prompts):
        if i % 10 == 0:
            logger.info(f"Progress: {i}/{len(prompts)}")
        
        classification = classify_prompt(p['text'])
        if classification:
            p['ml_classification'] = classification
            results.append(p)
        
        # Small delay to not overwhelm Ollama
        time.sleep(0.5)
    
    # Save results
    output = {
        'metadata': {
            'model': MODEL,
            'processed': len(results),
            'timestamp': datetime.now().isoformat()
        },
        'prompts': results
    }
    
    with open(PROCESSED_DIR / "ml_classified.json", 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(results)} ML-classified prompts")
    logger.info("=" * 60)
    logger.info("COMPLETE")
    logger.info("=" * 60)

if __name__ == '__main__':
    main()
