"""Testing module using tmux for background execution."""
from __future__ import annotations

import json
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import PipelineConfig


@dataclass
class TestResult:
    """Result from a single model test."""
    model: str
    total: int
    succeeded: int
    failed: int
    flagged: int
    duration_seconds: float
    output_path: Path
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "flagged": self.flagged,
            "duration_seconds": self.duration_seconds,
            "output_path": str(self.output_path),
        }


class TestRunner:
    """Runner for jailbreak tests using tmux."""
    
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.session_name = "auto_test"
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        import subprocess
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                 f"{self.config.ollama_base_url}/api/tags"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "200"
        except Exception:
            return False
    
    def get_available_models(self) -> list[str]:
        """Get list of models available in Ollama."""
        import subprocess
        import json
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.config.ollama_base_url}/api/tags"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []
    
    def run_test(
        self,
        vectors_path: Path,
        model: str,
        output_prefix: str,
    ) -> TestResult | None:
        """Run test for a single model."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_safe = model.replace(":", "_")
        
        output_base = self.config.results_dir / f"{output_prefix}_{model_safe}_{timestamp}"
        
        cmd = [
            "/usr/bin/python3", "-m", "jailbreak_tester",
            "--catalog", str(vectors_path),
            "--model", model,
            "--allow-insecure-http",
            "--timeout", str(self.config.test_timeout),
            "--checkpoint", f"{output_base}.jsonl",
            "--json-report", f"{output_base}.json",
            "--text-report", f"{output_base}.txt",
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.config.base_dir.parent,
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout * 100,  # Allow for many tests
            )
            duration = time.time() - start_time
            
            # Parse output for stats
            output = result.stdout
            total = succeeded = failed = flagged = 0
            
            for line in output.split("\n"):
                if "total=" in line:
                    parts = line.split()
                    for part in parts:
                        if part.startswith("total="):
                            total = int(part.split("=")[1])
                        elif part.startswith("succeeded="):
                            succeeded = int(part.split("=")[1])
                        elif part.startswith("failed="):
                            failed = int(part.split("=")[1])
                        elif part.startswith("flagged="):
                            flagged = int(part.split("=")[1])
            
            return TestResult(
                model=model,
                total=total,
                succeeded=succeeded,
                failed=failed,
                flagged=flagged,
                duration_seconds=duration,
                output_path=Path(f"{output_base}.txt"),
            )
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"Error testing {model}: {e}")
            return None
    
    def run_all_tests(
        self,
        vectors_path: Path,
        output_prefix: str = "auto",
    ) -> list[TestResult]:
        """Run tests on all configured models."""
        if not self.check_ollama():
            print("ERROR: Ollama not running")
            return []
        
        available = set(self.get_available_models())
        results: list[TestResult] = []
        
        for model in self.config.test_models:
            if model not in available:
                print(f"SKIP: {model} not available")
                continue
            
            print(f"Testing: {model}")
            result = self.run_test(vectors_path, model, output_prefix)
            if result:
                results.append(result)
                print(f"  Done: {result.flagged}/{result.total} flagged")
        
        return results
    
    def run_in_tmux(
        self,
        vectors_path: Path,
        output_prefix: str = "auto",
    ) -> str:
        """Start tests in tmux session. Returns session name."""
        script = f'''
cd {self.config.base_dir.parent}
for MODEL in {' '.join(shlex.quote(m) for m in self.config.test_models)}; do
    MODEL_SAFE=$(echo $MODEL | tr ':' '_')
    echo "Testing: $MODEL"
    python3 -m jailbreak_tester \\
        --catalog {shlex.quote(str(vectors_path))} \\
        --model "$MODEL" \\
        --allow-insecure-http \\
        --timeout {self.config.test_timeout} \\
        --checkpoint "results/{output_prefix}_${{MODEL_SAFE}}.jsonl" \\
        --json-report "results/{output_prefix}_${{MODEL_SAFE}}.json" \\
        --text-report "results/{output_prefix}_${{MODEL_SAFE}}.txt"
done
echo "=== ALL TESTS COMPLETE ==="
'''
        
        script_path = self.config.base_dir / "run_auto_test.sh"
        with open(script_path, "w") as f:
            f.write(script)
        script_path.chmod(0o755)
        
        # Start tmux session
        subprocess.run([
            "tmux", "new-session", "-d", "-s", self.session_name,
            f"bash {script_path}"
        ])
        
        return self.session_name


if __name__ == "__main__":
    from .config import load_config
    
    config = load_config()
    runner = TestRunner(config)
    
    if runner.check_ollama():
        print(f"Ollama running. Available models: {runner.get_available_models()}")
    else:
        print("Ollama not running")
