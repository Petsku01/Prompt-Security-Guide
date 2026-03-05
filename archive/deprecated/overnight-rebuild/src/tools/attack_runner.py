#!/usr/bin/env python3
"""
Attack Runner - Execute Attacks with Resilience
================================================

ASSUMPTIONS:
1. Ollama is installed and can be started with 'ollama serve'
2. Target models are available locally
3. Network is stable (localhost only)
4. Checkpoints are written atomically

POTENTIAL CONCERNS:
1. Ollama may run out of memory with large models
2. Some prompts may cause very long responses
3. Checkpoint file could become large

Author: Kuu (SE methodology)
Date: 2026-03-04
"""

import json
import requests
import subprocess
import time
import signal
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional
from datetime import datetime
import logging

from smart_selector import Attack
from llm_judge import judge, JudgeResult

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

OLLAMA_URL = "http://localhost:11434"
GENERATE_URL = f"{OLLAMA_URL}/api/generate"
TAGS_URL = f"{OLLAMA_URL}/api/tags"

REQUEST_TIMEOUT = 60  # Seconds per request
REQUEST_DELAY = 1.0   # Seconds between requests
MAX_RETRIES = 3
CHECKPOINT_INTERVAL = 10

# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class AttackResult:
    """Result of a single attack."""
    attack_id: str
    prompt: str
    technique: str
    response: str
    verdict: str  # SAFE, UNSAFE, AMBIGUOUS
    confidence: float
    judge_method: str
    response_time_ms: int
    timestamp: str
    error: Optional[str] = None


# ============================================================
# OLLAMA MANAGEMENT
# ============================================================

def check_ollama() -> bool:
    """Check if Ollama is running."""
    try:
        resp = requests.get(TAGS_URL, timeout=5)
        return resp.status_code == 200
    except:
        return False


def start_ollama() -> bool:
    """Attempt to start Ollama."""
    logger.info("Attempting to start Ollama...")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(5)
        return check_ollama()
    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        return False


def ensure_ollama_running() -> bool:
    """Ensure Ollama is running, start if needed."""
    if check_ollama():
        return True
    
    logger.warning("Ollama not running, attempting to start...")
    if start_ollama():
        logger.info("Ollama started successfully")
        return True
    
    logger.error("Could not start Ollama")
    return False


def check_model_available(model: str) -> bool:
    """Check if a model is available."""
    try:
        resp = requests.get(TAGS_URL, timeout=5)
        if resp.status_code == 200:
            models = [m['name'] for m in resp.json().get('models', [])]
            # Check exact match or prefix match
            return any(model in m or m.startswith(model.split(':')[0]) 
                      for m in models)
    except:
        pass
    return False


# ============================================================
# CHECKPOINT MANAGEMENT
# ============================================================

class CheckpointManager:
    """Manages checkpoint saving and loading."""
    
    def __init__(self, checkpoint_path: Path):
        self.path = checkpoint_path
        self.results: List[AttackResult] = []
        self.completed_ids: set = set()
    
    def load(self) -> bool:
        """Load existing checkpoint. Returns True if loaded."""
        if self.path.exists():
            try:
                with open(self.path) as f:
                    data = json.load(f)
                self.completed_ids = set(data.get('completed_ids', []))
                self.results = [
                    AttackResult(**r) for r in data.get('results', [])
                ]
                logger.info(f"Loaded checkpoint: {len(self.results)} results")
                return True
            except Exception as e:
                logger.warning(f"Could not load checkpoint: {e}")
        return False
    
    def save(self):
        """Save current state to checkpoint."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'completed_ids': list(self.completed_ids),
            'results': [asdict(r) for r in self.results]
        }
        
        # Atomic write
        temp_path = self.path.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2)
        temp_path.rename(self.path)
    
    def add_result(self, result: AttackResult):
        """Add a result and save if interval reached."""
        self.results.append(result)
        self.completed_ids.add(result.attack_id)
        
        if len(self.results) % CHECKPOINT_INTERVAL == 0:
            self.save()
            logger.info(f"Checkpoint saved: {len(self.results)} results")


# ============================================================
# ATTACK EXECUTION
# ============================================================

def send_prompt(model: str, prompt: str, retries: int = MAX_RETRIES) -> tuple:
    """
    Send a prompt to the model.
    Returns (response_text, response_time_ms, error).
    """
    for attempt in range(retries):
        try:
            start = time.time()
            
            resp = requests.post(GENERATE_URL, json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 512
                }
            }, timeout=REQUEST_TIMEOUT)
            
            elapsed_ms = int((time.time() - start) * 1000)
            
            if resp.status_code == 200:
                result = resp.json()
                return result.get('response', ''), elapsed_ms, None
            else:
                logger.warning(f"Request failed: {resp.status_code}")
                
        except requests.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
        except Exception as e:
            logger.warning(f"Error on attempt {attempt + 1}: {e}")
        
        # Check Ollama still running
        if not check_ollama():
            ensure_ollama_running()
        
        time.sleep(2)  # Wait before retry
    
    return "", 0, "Max retries exceeded"


# ============================================================
# MAIN RUNNER
# ============================================================

# Graceful shutdown support
shutdown_requested = False

def signal_handler(sig, frame):
    global shutdown_requested
    logger.warning("Shutdown requested...")
    shutdown_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_attacks(
    model: str,
    attacks: List[Attack],
    checkpoint_file: Path,
    progress_callback=None
) -> List[AttackResult]:
    """
    Run attacks against a model.
    
    Args:
        model: Model name to test
        attacks: List of attacks to run
        checkpoint_file: Path for checkpoint file
        progress_callback: Optional callback(current, total)
        
    Returns:
        List of AttackResult objects
    """
    global shutdown_requested
    
    # Ensure Ollama running
    if not ensure_ollama_running():
        logger.error("Cannot run attacks: Ollama not available")
        return []
    
    # Check model available
    if not check_model_available(model):
        logger.error(f"Model {model} not available")
        return []
    
    # Load checkpoint
    checkpoint = CheckpointManager(checkpoint_file)
    checkpoint.load()
    
    # Filter already completed
    remaining = [a for a in attacks if a.id not in checkpoint.completed_ids]
    logger.info(f"Running {len(remaining)} attacks ({len(checkpoint.results)} already done)")
    
    # Run attacks
    for i, attack in enumerate(remaining):
        if shutdown_requested:
            logger.info("Shutting down gracefully...")
            break
        
        # Progress
        if progress_callback:
            progress_callback(i + len(checkpoint.results), len(attacks))
        
        # Send prompt
        response, response_time, error = send_prompt(model, attack.prompt)
        
        # Judge response
        if error:
            result = AttackResult(
                attack_id=attack.id,
                prompt=attack.prompt[:500],
                technique=attack.technique,
                response="",
                verdict="ERROR",
                confidence=0.0,
                judge_method="error",
                response_time_ms=0,
                timestamp=datetime.now().isoformat(),
                error=error
            )
        else:
            judge_result = judge(attack.prompt, response)
            result = AttackResult(
                attack_id=attack.id,
                prompt=attack.prompt[:500],
                technique=attack.technique,
                response=response[:1000],
                verdict=judge_result.verdict,
                confidence=judge_result.confidence,
                judge_method=judge_result.method,
                response_time_ms=response_time,
                timestamp=datetime.now().isoformat()
            )
        
        checkpoint.add_result(result)
        
        # Log progress
        logger.info(f"[{i+1}/{len(remaining)}] {attack.technique}: {result.verdict}")
        
        # Delay between requests
        time.sleep(REQUEST_DELAY)
    
    # Final save
    checkpoint.save()
    
    return checkpoint.results


# ============================================================
# TESTING
# ============================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=== Attack Runner Test ===\n")
    
    # Check Ollama
    print(f"Ollama running: {check_ollama()}")
    
    if ensure_ollama_running():
        print("Ollama ready")
        
        # Quick test
        response, time_ms, error = send_prompt("llama3:8b", "Hello, who are you?")
        if error:
            print(f"Error: {error}")
        else:
            print(f"Response ({time_ms}ms): {response[:100]}...")
