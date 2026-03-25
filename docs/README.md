# Documentation Index

## CLI Feature Highlights (v4.1)

- `psg scan` supports parallel execution via `--workers` and `--rate-limit`.
- `psg eval` evaluates classifier performance from golden datasets and supports CI gating with `--fail-on-macro-f1-below`.
- `psg benchmark` runs preset suites: `jbb`, `owasp`, `obliteratus`, `full`.
- LangChain middleware is available in `psg/integrations/langchain.py` with input and output screening.

## Core docs

- [TESTING_GUIDE.md](TESTING_GUIDE.md)
- [BENCHMARKS.md](BENCHMARKS.md)
- [METHODOLOGY.md](METHODOLOGY.md)
- [LIMITATIONS.md](LIMITATIONS.md)
- [DEFENSE_STRATEGIES.md](DEFENSE_STRATEGIES.md)
- [DEFENSE_EFFECTIVENESS.md](DEFENSE_EFFECTIVENESS.md)
- [SECURITY_GUIDE.md](SECURITY_GUIDE.md)
- [REFERENCES.md](REFERENCES.md)

## Project-level docs

- [../ARCHITECTURE.md](../ARCHITECTURE.md)
- [../MIGRATION.md](../MIGRATION.md)
- [../CHANGELOG.md](../CHANGELOG.md)
- [../results/README.md](../results/README.md)
