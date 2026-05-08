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
from .logging_config import logger


@dataclass
class ModelTestResult:
    """Result from a single model test."""

    model: str
    total: int
    succeeded: int
    failed: int
    flagged: int
    duration_seconds: float
    output_path: Path
    techniques: dict[str, int] | None = None

    def __post_init__(self) -> None:
        if self.techniques is None:
            self.techniques = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "total": self.total,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "flagged": self.flagged,
            "duration_seconds": self.duration_seconds,
            "output_path": str(self.output_path),
            "techniques": self.techniques or {},
        }


class PipelineTester:
    """Runner for jailbreak tests using tmux."""

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.session_name = "auto_test"

    def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            result = subprocess.run(
                [
                    "curl",
                    "-s",
                    "-o",
                    "/dev/null",
                    "-w",
                    "%{http_code}",
                    f"{self.config.ollama_base_url}/api/tags",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip() == "200"
        except Exception as exc:
            logger.debug("Ollama health check failed: %s", exc)
            return False

    def get_available_models(self) -> list[str]:
        """Get list of models available in Ollama."""
        try:
            result = subprocess.run(
                ["curl", "-s", f"{self.config.ollama_base_url}/api/tags"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return [m["name"] for m in data.get("models", [])]
        except subprocess.TimeoutExpired:
            logger.warning("Ollama model list request timed out")
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON from Ollama: %s", e)
        except Exception as e:
            logger.error("Failed to get models: %s", e)
        return []

    def run_test(
        self,
        vectors_path: Path,
        model: str,
        output_prefix: str,
    ) -> ModelTestResult | None:
        """Run test for a single model."""
        timestamp = datetime.now().strftime("%Y%m%d")
        model_safe = model.replace(":", "_")

        output_base = (
            self.config.results_dir / f"{output_prefix}_{model_safe}_{timestamp}"
        )

        cmd = [
            self.config.python_executable,
            "-m",
            "psg",
            "--catalog",
            str(vectors_path),
            "--model",
            model,
            "--allow-insecure-http",
            "--timeout",
            str(self.config.test_timeout),
            "--checkpoint",
            f"{output_base}.jsonl",
            "--json-report",
            f"{output_base}.json",
            "--text-report",
            f"{output_base}.txt",
        ]

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=self.config.project_root,
                capture_output=True,
                text=True,
                timeout=self.config.test_timeout * 3,  # 3x multiplier (was 100x)
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

            if total == 0:
                logger.warning(
                    "Test for %s returned total=0 — possibly silent failure; skipping",
                    model,
                )
                return None

            return ModelTestResult(
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
            logger.error("Error testing %s: %s", model, e)
            return None

    def run_all_tests(
        self,
        vectors_path: Path,
        output_prefix: str = "auto",
    ) -> list[ModelTestResult]:
        """Run tests on all configured models."""
        if not self.check_ollama():
            logger.error("Ollama not running")
            return []

        available = set(self.get_available_models())
        results: list[ModelTestResult] = []

        for model in self.config.test_models:
            if model not in available:
                logger.warning("SKIP: %s not available", model)
                continue

            logger.info("Testing: %s", model)
            result = self.run_test(vectors_path, model, output_prefix)
            if result is None:
                logger.warning("SKIP: %s — run_test returned None (possible silent failure)", model)
                continue
            results.append(result)
            logger.info("  Done: %s/%s flagged", result.flagged, result.total)

        return results

    def run_in_tmux(
        self,
        vectors_path: Path,
        output_prefix: str = "auto",
    ) -> str:
        """Start tests in tmux session. Returns session name."""
        result_dir = shlex.quote(str(self.config.results_dir))
        script = f'''
cd {shlex.quote(str(self.config.project_root))}
for MODEL in {" ".join(shlex.quote(m) for m in self.config.test_models)}; do
    MODEL_SAFE=$(echo $MODEL | tr ':' '_')
    echo "Testing: $MODEL"
    {shlex.quote(self.config.python_executable)} -m psg \\
        --catalog {shlex.quote(str(vectors_path))} \\
        --model "$MODEL" \\
        --allow-insecure-http \\
        --timeout {self.config.test_timeout} \\
        --checkpoint "{result_dir}/{output_prefix}_${{MODEL_SAFE}}.jsonl" \\
        --json-report "{result_dir}/{output_prefix}_${{MODEL_SAFE}}.json" \\
        --text-report "{result_dir}/{output_prefix}_${{MODEL_SAFE}}.txt"
done
echo "=== ALL TESTS COMPLETE ==="
'''

        script_path = self.config.base_dir / "run_auto_test.sh"
        with open(script_path, "w") as f:
            f.write(script)
        script_path.chmod(0o755)

        # Start tmux session
        subprocess.run(
            [
                "tmux",
                "new-session",
                "-d",
                "-s",
                self.session_name,
                f"bash {script_path}",
            ]
        )

        return self.session_name


if __name__ == "__main__":
    from .config import load_config

    config = load_config()
    runner = PipelineTester(config)

    if runner.check_ollama():
        logger.info("Ollama running. Available models: %s", runner.get_available_models())
    else:
        logger.warning("Ollama not running")
