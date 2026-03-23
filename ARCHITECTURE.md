# Architecture

## Runtime layers

1. **CLI layer** (`psg.cli`)  
   Parses args, validates config, invokes orchestrator.
2. **Orchestration layer** (`psg.orchestrator`)  
   Loads catalog, runs attack loop, aggregates summary.
3. **LLM transport layer** (`psg.llm.*`)  
   Handles API calls, retries, schema validation.
4. **Security/reporting layer** (`psg.security`, `psg.reporting`)  
   Classifies responses, redacts sensitive fragments, writes reports.

## Data flow

`catalog JSON -> attack execution -> detection/classification -> checkpoint/report artifacts`

## Legacy boundary

`legacy/` contains v2 implementations retained only for migration support.
No new features should be added there.

## Artifacts policy

- `results/` is runtime output (ignored except samples)
- Large historical projects are moved to `archive/deprecated/`
