#!/usr/bin/env python3
"""
LLM Classifier v2 - Built with SE Methodology
=============================================

ASSUMPTIONS:
1. Ollama running at localhost:11434 with llama3:8b
2. Processing 500 prompts overnight (~17 min)
3. JSON output format for downstream processing
4. 0.5s delay between requests to prevent overload
5. Temperature 0.1 for consistent classifications

DESIGN DECISIONS:
- Retry logic (3 attempts) for transient failures
- Validation of LLM output before accepting
- Progress checkpointing every 50 prompts
- Graceful shutdown on SIGINT

Author: Kuu (SE methodology)
Date: 2026-03-04
"""

import json
import requests
import signal
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
import logging
import time

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3:8b"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"
CHECKPOINT_FILE = PROCESSED_DIR / "ml_checkpoint.json"
OUTPUT_FILE = PROCESSED_DIR / "ml_classified.json"
LOG_FILE = Path(__file__).parent / "ml_classifier_v2.log"

# Processing config
BATCH_SIZE = 500          # Total prompts to process
CHECKPOINT_INTERVAL = 50  # Save progress every N prompts
REQUEST_DELAY = 0.5       # Seconds between requests
REQUEST_TIMEOUT = 45      # Seconds per request
MAX_RETRIES = 3           # Retry failed classifications

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CLASSIFICATION PROMPT (carefully designed)
# ============================================================

CLASSIFICATION_PROMPT = """You are an expert in LLM security analyzing jailbreak prompts.

Analyze this prompt and respond with ONLY valid JSON (no markdown, no explanation):

PROMPT TO ANALYZE:
---
{prompt}
---

Respond with this exact JSON structure:
{{"target_model": "<chatgpt|claude|gemini|llama|grok|mistral|generic>", "technique": "<roleplay|dan_jailbreak|encoding|multi_turn|emotional_manipulation|authority_claim|fiction_framing|technical_exploit|prompt_injection|obfuscation|novel>", "category": "<persona_based|encoding_based|social_engineering|prompt_injection|technical|other>", "sophistication": <1-5>, "novelty": <1-5>, "likely_effective": <true|false>, "one_line_summary": "<brief description>"}}"""

# ============================================================
# GLOBALS FOR GRACEFUL SHUTDOWN
# ============================================================

shutdown_requested = False
results: List[Dict] = []
processed_ids: set = set()

def signal_handler(sig, frame):
    global shutdown_requested
    logger.warning("Shutdown requested - saving checkpoint...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ============================================================
# CORE FUNCTIONS
# ============================================================

def validate_classification(data: Dict) -> bool:
    """Validate that classification output has required fields."""
    required = ['target_model', 'technique', 'sophistication', 'novelty']
    
    for field in required:
        if field not in data:
            return False
    
    # Validate ranges
    if not isinstance(data.get('sophistication'), int) or not 1 <= data['sophistication'] <= 5:
        return False
    if not isinstance(data.get('novelty'), int) or not 1 <= data['novelty'] <= 5:
        return False
    
    return True


def classify_prompt(text: str, retries: int = MAX_RETRIES) -> Optional[Dict]:
    """
    Classify a single prompt using Ollama with retry logic.
    Returns validated classification dict or None.
    """
    prompt = CLASSIFICATION_PROMPT.format(prompt=text[:1500])
    
    for attempt in range(retries):
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 300,
                }
            }, timeout=REQUEST_TIMEOUT)
            
            if resp.status_code != 200:
                logger.warning(f"Ollama returned {resp.status_code}, attempt {attempt+1}")
                continue
            
            result = resp.json()
            response_text = result.get('response', '').strip()
            
            # Extract JSON from response
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            
            if start >= 0 and end > start:
                try:
                    classification = json.loads(response_text[start:end])
                    
                    if validate_classification(classification):
                        return classification
                    else:
                        logger.debug(f"Invalid classification structure, attempt {attempt+1}")
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON parse error: {e}, attempt {attempt+1}")
            
        except requests.Timeout:
            logger.warning(f"Request timeout, attempt {attempt+1}")
        except requests.RequestException as e:
            logger.warning(f"Request error: {e}, attempt {attempt+1}")
        
        # Wait before retry
        if attempt < retries - 1:
            time.sleep(1)
    
    return None


def save_checkpoint():
    """Save current progress to checkpoint file."""
    checkpoint = {
        'timestamp': datetime.now().isoformat(),
        'processed_count': len(results),
        'processed_ids': list(processed_ids),
        'results': results
    }
    
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)
    
    logger.info(f"Checkpoint saved: {len(results)} prompts")


def load_checkpoint() -> bool:
    """Load checkpoint if exists. Returns True if checkpoint loaded."""
    global results, processed_ids
    
    if CHECKPOINT_FILE.exists():
        try:
            with open(CHECKPOINT_FILE) as f:
                checkpoint = json.load(f)
            
            results = checkpoint.get('results', [])
            processed_ids = set(checkpoint.get('processed_ids', []))
            
            logger.info(f"Loaded checkpoint: {len(results)} prompts already processed")
            return True
        except Exception as e:
            logger.warning(f"Could not load checkpoint: {e}")
    
    return False


def save_final_output():
    """Save final results."""
    output = {
        'metadata': {
            'model': MODEL,
            'total_processed': len(results),
            'completed': datetime.now().isoformat(),
            'methodology': 'SE_v2'
        },
        'classifications': results
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Final output saved: {OUTPUT_FILE}")


# ============================================================
# MAIN PROCESSING
# ============================================================

def main():
    global results, processed_ids, shutdown_requested
    
    logger.info("=" * 60)
    logger.info("LLM CLASSIFIER v2 (SE METHODOLOGY)")
    logger.info(f"Model: {MODEL}")
    logger.info(f"Batch size: {BATCH_SIZE}")
    logger.info("=" * 60)
    
    # Load checkpoint if exists
    load_checkpoint()
    
    # Load prompts to process
    top_quality_file = PROCESSED_DIR / "top_quality.json"
    if not top_quality_file.exists():
        logger.error(f"Input file not found: {top_quality_file}")
        sys.exit(1)
    
    with open(top_quality_file) as f:
        data = json.load(f)
    
    all_prompts = data.get('prompts', [])[:BATCH_SIZE]
    
    # Filter out already processed
    prompts_to_process = [p for p in all_prompts if p.get('id') not in processed_ids]
    
    logger.info(f"Total prompts: {len(all_prompts)}")
    logger.info(f"Already processed: {len(processed_ids)}")
    logger.info(f"Remaining: {len(prompts_to_process)}")
    logger.info("-" * 60)
    
    # Process prompts
    start_time = datetime.now()
    
    for i, prompt_data in enumerate(prompts_to_process):
        if shutdown_requested:
            logger.info("Shutdown requested - stopping gracefully")
            break
        
        prompt_id = prompt_data.get('id', f'unknown_{i}')
        prompt_text = prompt_data.get('text', '')
        
        # Skip if no text
        if not prompt_text or len(prompt_text) < 20:
            continue
        
        # Classify
        classification = classify_prompt(prompt_text)
        
        if classification:
            result = {
                'id': prompt_id,
                'original_source': prompt_data.get('source_repo', 'unknown'),
                'text_preview': prompt_text[:200],
                'classification': classification
            }
            results.append(result)
            processed_ids.add(prompt_id)
        else:
            logger.warning(f"Failed to classify {prompt_id}")
        
        # Progress logging
        total_done = len(results)
        if total_done % 10 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = total_done / elapsed if elapsed > 0 else 0
            remaining = len(prompts_to_process) - (i + 1)
            eta_seconds = remaining / rate if rate > 0 else 0
            logger.info(f"Progress: {total_done}/{len(all_prompts)} | "
                       f"Rate: {rate:.1f}/s | ETA: {eta_seconds/60:.1f}m")
        
        # Checkpoint
        if total_done % CHECKPOINT_INTERVAL == 0:
            save_checkpoint()
        
        # Delay between requests
        time.sleep(REQUEST_DELAY)
    
    # Final save
    save_checkpoint()
    save_final_output()
    
    # Summary
    duration = datetime.now() - start_time
    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE")
    logger.info(f"Total classified: {len(results)}")
    logger.info(f"Duration: {duration}")
    logger.info(f"Output: {OUTPUT_FILE}")
    logger.info("=" * 60)
    
    # Print stats
    if results:
        techniques = {}
        for r in results:
            t = r.get('classification', {}).get('technique', 'unknown')
            techniques[t] = techniques.get(t, 0) + 1
        
        print("\n=== TECHNIQUE DISTRIBUTION ===")
        for t, count in sorted(techniques.items(), key=lambda x: -x[1]):
            print(f"  {t}: {count}")


if __name__ == '__main__':
    main()
