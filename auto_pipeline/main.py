"""Main orchestrator for Auto Vector Pipeline."""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from .config import PipelineConfig, load_config
from .discovery import DiscoveryEngine, Source
from .generator import VectorGenerator, AttackVector
from .tester import TestRunner, TestResult
from .reporter import Reporter, PipelineReport


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
        self.tester = TestRunner(config)
        self.reporter = Reporter(config)
    
    def run_discovery(self) -> list[Source]:
        """Run discovery phase."""
        print("=== DISCOVERY PHASE ===")
        sources = self.discovery.discover()
        print(f"Found {len(sources)} new sources")
        
        if sources:
            output_path = self.config.base_dir / f"sources_{datetime.now().strftime('%Y%m%d')}.json"
            self.discovery.save_sources(sources, output_path)
            print(f"Saved to {output_path}")
        
        return sources
    
    def run_generation(self, sources: list[Source]) -> list[AttackVector]:
        """Run generation phase."""
        print("\n=== GENERATION PHASE ===")
        
        if not sources:
            print("No sources to generate from")
            return []
        
        vectors = self.generator.generate_from_sources(sources)
        print(f"Generated {len(vectors)} new vectors")
        
        if vectors:
            output_path = self.config.base_dir.parent / "datasets" / f"auto_{datetime.now().strftime('%Y%m%d')}.json"
            self.generator.save_vectors(vectors, output_path)
            print(f"Saved to {output_path}")
        
        return vectors
    
    def run_testing(self, vectors_path: Path, use_tmux: bool = False) -> list[TestResult]:
        """Run testing phase."""
        print("\n=== TESTING PHASE ===")
        
        if not self.tester.check_ollama():
            print("ERROR: Ollama not running - skipping tests")
            return []
        
        if use_tmux:
            session = self.tester.run_in_tmux(vectors_path)
            print(f"Tests started in tmux session: {session}")
            print("Monitor with: tmux attach -t {session}")
            return []  # Results will be available later
        else:
            results = self.tester.run_all_tests(vectors_path)
            print(f"Completed {len(results)} model tests")
            return results
    
    def run_reporting(
        self,
        sources: list[Source],
        vectors: list[AttackVector],
        results: list[TestResult],
    ) -> PipelineReport:
        """Run reporting phase."""
        print("\n=== REPORTING PHASE ===")
        
        report = self.reporter.create_report(sources, vectors, results)
        report_path = self.reporter.save_report(report)
        print(f"Report saved to {report_path}")
        
        # Generate Discord message
        discord_msg = self.reporter.generate_discord_message(report)
        print("\n--- Discord Message ---")
        print(discord_msg)
        print("--- End ---")
        
        return report
    
    def run_full(self, use_tmux: bool = False) -> PipelineReport | None:
        """Run full pipeline."""
        print(f"Starting Auto Vector Pipeline at {datetime.now().isoformat()}")
        print(f"Config: {self.config.max_vectors_per_run} max vectors, {len(self.config.test_models)} models")
        print()
        
        # Phase 1: Discovery
        sources = self.run_discovery()
        
        # Phase 2: Generation
        vectors = self.run_generation(sources)
        
        if not vectors:
            print("\nNo new vectors generated - pipeline complete")
            return None
        
        # Phase 3: Testing
        vectors_path = self.config.base_dir.parent / "datasets" / f"auto_{datetime.now().strftime('%Y%m%d')}.json"
        results = self.run_testing(vectors_path, use_tmux=use_tmux)
        
        if use_tmux:
            print("\nTesting running in background - run reporting manually when complete")
            return None
        
        # Phase 4: Reporting
        report = self.run_reporting(sources, vectors, results)
        
        print(f"\n=== PIPELINE COMPLETE ===")
        print(f"Flagged: {report.total_flagged}/{report.total_tests}")
        
        return report


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Auto Vector Pipeline")
    parser.add_argument("--config", type=Path, help="Config file path")
    parser.add_argument("--tmux", action="store_true", help="Run tests in tmux")
    parser.add_argument("--skip-discovery", action="store_true", help="Skip discovery phase")
    parser.add_argument("--skip-generation", action="store_true", help="Skip generation phase")
    parser.add_argument("--vectors", type=Path, help="Use existing vectors file for testing")
    parser.add_argument("--report-only", action="store_true", help="Only run reporting on existing results")
    
    args = parser.parse_args(argv)
    
    config = load_config(args.config)
    pipeline = Pipeline(config)
    
    if args.report_only:
        # Just generate report from existing results
        sources: list[Source] = []
        vectors: list[AttackVector] = []
        results: list[TestResult] = []  # Would need to load from files
        pipeline.run_reporting(sources, vectors, results)
        return 0
    
    if args.vectors:
        # Just run testing with existing vectors
        results = pipeline.run_testing(args.vectors, use_tmux=args.tmux)
        if results:
            pipeline.run_reporting([], [], results)
        return 0
    
    # Full pipeline
    report = pipeline.run_full(use_tmux=args.tmux)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
