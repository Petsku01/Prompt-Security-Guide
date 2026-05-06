"""Main orchestrator for Auto Vector Pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import PipelineConfig, load_config, validate_environment
from .discovery import DiscoveryEngine, Source
from .generator import VectorGenerator, AttackVector
from .tester import PipelineTester, ModelTestResult
from .reporter import Reporter, PipelineReport
from .logging_config import logger


class Pipeline:
    """Main pipeline orchestrator."""

    def __init__(
        self,
        config: PipelineConfig,
        search_func: Callable | None = None,
        generate_func: Callable | None = None,
    ) -> None:
        self.config = config
        self.discovery = DiscoveryEngine(config, search_func)
        self.generator = VectorGenerator(config, generate_func)
        self.tester = PipelineTester(config)
        self.reporter = Reporter(config)

    def run_discovery(self) -> list[Source]:
        """Run discovery phase."""
        logger.info("=== DISCOVERY PHASE ===")
        sources = self.discovery.discover()
        logger.info(f"Found {len(sources)} new sources")

        if sources:
            output_path = (
                self.config.base_dir
                / f"sources_{datetime.now().strftime('%Y%m%d')}.json"
            )
            self.discovery.save_sources(sources, output_path)

        return sources

    def run_generation(self, sources: list[Source]) -> list[AttackVector]:
        """Run generation phase."""
        logger.info("=== GENERATION PHASE ===")

        if not sources:
            logger.info("No sources to generate from")
            return []

        vectors = self.generator.generate_from_sources(sources)
        logger.info(f"Generated {len(vectors)} new vectors")

        if vectors:
            output_path = (
                self.config.datasets_dir
                / f"auto_{datetime.now().strftime('%Y%m%d')}.json"
            )
            self.generator.save_vectors(vectors, output_path)
            logger.info(f"Saved vectors to {output_path}")

        return vectors

    def run_testing(
        self, vectors_path: Path, use_tmux: bool = False
    ) -> list[ModelTestResult]:
        """Run testing phase."""
        logger.info("=== TESTING PHASE ===")

        if not self.tester.check_ollama():
            logger.error("Ollama not running - skipping tests")
            return []

        if use_tmux:
            session = self.tester.run_in_tmux(vectors_path)
            logger.info(f"Tests started in tmux session: {session}")
            return []
        else:
            results = self.tester.run_all_tests(vectors_path)
            logger.info(f"Completed {len(results)} model tests")
            return results

    def run_reporting(
        self,
        sources: list[Source],
        vectors: list[AttackVector],
        results: list[ModelTestResult],
    ) -> PipelineReport:
        """Run reporting phase."""
        logger.info("=== REPORTING PHASE ===")

        report = self.reporter.create_report(sources, vectors, results)
        report_path = self.reporter.save_report(report)
        logger.info(f"Report saved to {report_path}")

        # Generate Discord message
        discord_msg = self.reporter.generate_discord_message(report)
        logger.debug(f"Discord message:\n{discord_msg}")

        return report

    def run_full(
        self,
        use_tmux: bool = False,
        skip_discovery: bool = False,
        skip_generation: bool = False,
    ) -> PipelineReport | None:
        """Run full pipeline."""
        logger.info(f"Starting Auto Vector Pipeline at {datetime.now().isoformat()}")
        logger.info(
            f"Config: {self.config.max_vectors_per_run} max vectors, {len(self.config.test_models)} models"
        )

        # Phase 1: Discovery
        sources: list[Source] = []
        if skip_discovery:
            logger.info("Skipping discovery phase (--skip-discovery)")
        else:
            sources = self.run_discovery()

        # Phase 2: Generation
        vectors: list[AttackVector] = []
        if skip_generation:
            logger.info("Skipping generation phase (--skip-generation)")
        else:
            vectors = self.run_generation(sources)

        if not vectors:
            logger.info("No new vectors generated - pipeline complete")
            return None

        # Phase 3: Testing
        vectors_path = (
            self.config.datasets_dir / f"auto_{datetime.now().strftime('%Y%m%d')}.json"
        )
        results = self.run_testing(vectors_path, use_tmux=use_tmux)

        if use_tmux:
            logger.info(
                "Testing running in background - run reporting manually when complete"
            )
            return None

        # Phase 4: Reporting
        report = self.run_reporting(sources, vectors, results)

        logger.info(
            f"=== PIPELINE COMPLETE === Flagged: {report.total_flagged}/{report.total_tests}"
        )

        return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Auto Vector Pipeline")
    parser.add_argument("--config", type=Path, help="Config file path")
    parser.add_argument("--tmux", action="store_true", help="Run tests in tmux")
    parser.add_argument(
        "--skip-discovery", action="store_true", help="Skip discovery phase"
    )
    parser.add_argument(
        "--skip-generation", action="store_true", help="Skip generation phase"
    )
    parser.add_argument(
        "--vectors", type=Path, help="Use existing vectors file for testing"
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Only run reporting on existing results",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable debug logging"
    )

    args = parser.parse_args(argv)

    if args.verbose:
        import logging

        logger.setLevel(logging.DEBUG)

    config = load_config(args.config)
    pipeline = Pipeline(config)

    if args.report_only:
        sources: list[Source] = []
        vectors: list[AttackVector] = []
        results: list[ModelTestResult] = []
        pipeline.run_reporting(sources, vectors, results)
        return 0

    if args.vectors:
        results = pipeline.run_testing(args.vectors, use_tmux=args.tmux)
        if results:
            pipeline.run_reporting([], [], results)
        return 0

    # Full pipeline
    try:
        if not args.skip_discovery:
            validate_environment(config)
        pipeline.run_full(
            use_tmux=args.tmux,
            skip_discovery=args.skip_discovery,
            skip_generation=args.skip_generation,
        )
    except RuntimeError as e:
        logger.error(str(e))
        return 2
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
