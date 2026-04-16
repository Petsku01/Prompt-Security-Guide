# Migrating from PSG 4.x to 5.0

v5 is a remediation release. It **hardens defaults**, **tightens detection**,
and **removes dead code**. Most users will see fewer false positives, a safer
server, and a new exit code on unreliable scans. Scripted integrations may
need small updates; this guide lists every user-visible change.

## TL;DR — upgrade checklist

- [ ] If you run `psg serve`: add `--allow-public` if you were relying on
      the 0.0.0.0 default, and set `PSG_SERVE_API_KEY` or `--api-key`.
- [ ] If you parse `psg scan`'s exit code: handle exit code **5** (scan
      completed but detector unreliable for ≥10% of attacks).
- [ ] If you parse `psg scan`'s final line: it now includes
      `detector_failures=N`.
- [ ] If you use LangChain `PSGGuardMiddleware`: the classifier-error
      default is now **fail-closed** (raises). Add `fail_open=True` to
      restore the old behavior.
- [ ] If your CI pins F1: the current baseline on the expanded golden
      set is 0.9231. Re-run `psg eval` and update your threshold.
- [ ] If you parse `RunSummary` or `AttemptResult` JSON: three new
      fields exist. Existing fields are unchanged.

## Defaults changed

### `psg serve`

| Field                    | 4.x                 | 5.0                                      |
|--------------------------|---------------------|------------------------------------------|
| Bind address             | `0.0.0.0`           | `127.0.0.1`                              |
| `--allow-public` flag    | —                   | Required to bind all interfaces          |
| API key auth             | —                   | `--api-key` / `PSG_SERVE_API_KEY` (opt-in) |
| Request body size limit  | unlimited           | 64 KiB; `--max-request-bytes` to override |
| `/health` liveness       | static `"ok"`       | exercises classifier; 503 on failure     |
| `_metrics` thread safety | racy                | lock-guarded                              |

If you deploy `psg serve` on a shared host, you probably want:

```bash
psg serve --allow-public --api-key "$(openssl rand -hex 32)"
```

### `psg scan` exit codes

```
0  success
1  unexpected error / report writing failed
2  configuration error
3  catalog error
4  LLM error
5  (NEW) scan completed but ≥10% of attacks had unreliable classification
```

CI integrations that treat non-zero as "scan broken" continue to work,
but you can now distinguish "scan failed" from "scan unreliable".

### `psg scan` output line

```diff
- Done. total=50 succeeded=48 failed=2 flagged=12 duration=34.21s
+ Done. total=50 succeeded=48 failed=2 flagged=12 detector_failures=0 duration=34.21s
```

### LangChain middleware

```python
from psg.integrations.langchain import PSGGuardMiddleware

# 4.x — classifier errors silently passed through
middleware = PSGGuardMiddleware(threshold=0.5)

# 5.0 — classifier errors raise PSGSecurityException
# To restore old behavior:
middleware = PSGGuardMiddleware(threshold=0.5, fail_open=True)
```

## Classifier changes

### Score rebalanced on known false-positive classes

v5 introduces two new scoring gates in `calculate_harm_score`:

- **Gate 3.5** — harmful keywords with no action signals cap at 0.3 so a
  response that merely *discusses* a harmful topic is not flagged.
- **Gate 3.6** — defensive-framing cap (OWASP/NIST/CISA references,
  *"class of attack"*, *"at a conceptual level"*, *"without covering how
  to …"*) also caps at 0.3.

Practical impact on classification (42-example golden set):

| Metric    | v4.3.0 (20 ex) | v5.0.0 (42 ex) |
|-----------|---------------|----------------|
| Accuracy  | 95.00%        | 95.24%         |
| Precision | 100.00%       | 92.31%         |
| Recall    | 90.00%        | 92.31%         |
| **F1**    | **0.9474**    | **0.9231**     |

F1 dropped slightly because the expanded set includes harder, more
realistic cases. Precision dropped but recall rose. If you set a custom
`--fail-on-macro-f1-below`, 0.85 is the recommended gate.

### EnsembleDetector is now a real ensemble

`--ensemble-mode` (default `any`):

- **`any`** — always run both detectors; flag if either flags. NEW DEFAULT.
- **`and`** — flag only when both agree. Higher precision.
- **`short_circuit`** — old behavior (skip judge once keyword flags).

If you were relying on the performance characteristics of the old
`ensemble` (which short-circuited), set `--ensemble-mode short_circuit`.

### LLM judge prompt and parser

- Delimiter format changed from `<request>…</request>` to
  `<request-{random-hex}>…</request-{random-hex}>`. Only matters if you
  cached judge prompts somewhere.
- `max_tokens` raised from 8 to 32.
- Parser accepts *"Verdict: SAFE"*, *"Answer: HARMFUL because …"*. It
  rejects negated (*"not harmful"*) and ambiguous (*"SAFE and HARMFUL"*)
  outputs as UNKNOWN.

### Redaction patterns expanded

`RedactionMode.PARTIAL` now covers Anthropic, OpenAI (classic / project /
service-account), AWS access + secret, GitHub classic/fine-grained,
Slack, Google API key, Stripe, generic JWT, Bearer headers, and generic
`api_key=…` assignments. Credentials are now redacted **before** email
/ phone so the phone regex does not fragment digit-rich tokens.

## Data model changes

`AttemptResult` gained three fields (all with defaults; no breaking
change to JSON consumers):

```python
@dataclass
class AttemptResult:
    # ...existing fields...
    detector_failed: bool = False        # (v5)
    attack_mode: str = "single"           # (v5)
    turns: list[ConversationTurn] | None = None  # (v5)
```

`RunSummary` gained one field:

```python
@dataclass
class RunSummary:
    # ...existing fields...
    detector_failures: int = 0  # (v5)
```

New dataclass:

```python
@dataclass
class ConversationTurn:
    turn_number: int
    user_message: str
    assistant_response: str
    attack_successful: bool | None = None
    harm_score: float | None = None
```

When a scan uses `--attack-mode crescendo` or `--attack-mode many-shot`,
each `AttemptResult.turns` holds the full dialogue. Single-turn attacks
carry `turns=None`. This is how you now get per-turn data out of the
multi-turn modes — the previous behavior flattened everything into a
single-line `labels=["crescendo_turn_N"]`.

## Removed / moved internals

None of these are public API, but they are common monkeypatch targets:

| 4.x                                         | 5.0                                           |
|---------------------------------------------|-----------------------------------------------|
| `psg.orchestrator.redact_text`              | `psg.execution.single_turn.redact_text` (or `psg.execution.multi_turn.redact_text`) |
| `psg.orchestrator._process_multi_turn_attack` | `psg.execution.multi_turn._process_multi_turn_attack` |
| `psg.orchestrator._classify_attack_response` | `psg.execution.single_turn._classify_attack_response` |
| `psg.orchestrator._run_attacks_sequential`  | inlined into `_run_attacks` (direct dispatch to `_run_attacks_sequential_impl`) |
| `psg.orchestrator._run_attacks_parallel`    | inlined into `_run_attacks` |
| `psg.automation.validation.validate_url`    | `psg.validation.network.validate_url` (old path still re-exports for compat) |
| `psg.execution.single_turn._process_attack(redactor=…)` | parameter removed |
| `psg.execution.single_turn._process_attack(process_multi_turn_attack_fn=…)` | parameter removed |
| `psg.execution.single_turn._process_attack(classify_attack_response_fn=…)` | parameter removed |
| `psg.execution.multi_turn._process_multi_turn_attack(redactor=…)` | parameter removed |
| `psg.execution.multi_turn._process_multi_turn_attack(classify_attack_response_fn=…)` | parameter removed |

The removed injection parameters had no non-test caller. Tests that
used `psg.orchestrator.redact_text` as a monkeypatch target must switch
to `psg.execution.single_turn.redact_text`.

## Configuration changes

```python
# AppConfig gained two fields (both with backwards-compatible defaults):
class AppConfig:
    # ...
    ensemble_mode: str = "any"       # (v5) — was hardcoded "short_circuit"
    # (redaction_mode, attack_mode, etc. unchanged)
```

```bash
# New CLI flags
psg scan --ensemble-mode {any|and|short_circuit}
psg serve --allow-public
psg serve --api-key <secret>
psg serve --max-request-bytes 65536
```

## Rate limiter semantics

The `--rate-limit` flag's *contract* is unchanged ("this many requests
per second"), but the *implementation* changed from a min-interval gate
to a proper token bucket with configurable burst capacity (default
`max(1, rate)`). For workloads with `--workers > 1`, throughput should
go **up** in v5 — the old gate serialized all workers through one lock.

If you have a test that measured pairwise intervals between requests,
update it to measure the total elapsed time over the full run instead.
The bucket allows an initial burst.

## Bandit / pip-audit

CI now runs both. If you fork PSG and maintain your own CI:

```yaml
- name: Bandit
  run: bandit -r psg/ -ll
- name: pip-audit
  run: pip-audit --strict .
```

Current v5 state: both report zero issues.

## Test harness

If you author tests, switch to the new spec-bound fixtures:

```python
def test_my_feature(mock_detector, mock_llm_client):
    # Fixtures are Mock(spec_set=...), so calling a non-existent method
    # raises AttributeError instead of silently returning a MagicMock.
    ...
```

Defined in `tests/conftest.py`. This is how the C1/C2 interface bugs
would now be caught in CI.

## Moved artifacts

| File                             | Status         |
|----------------------------------|----------------|
| `coverage.json`                  | untracked + gitignored |
| `datasets/auto_*.json`           | untracked + gitignored (pipeline writes to `artifacts/`) |
| `datasets/new_vectors_*.json`    | untracked + gitignored |
| `psg/automation/sources_*.json`  | untracked + gitignored |
| `scripts/test_*.py`              | renamed to `scripts/run_*.py` (they aren't pytest tests) |
| `datasets/benchmark_presets.json` | **new** — formerly hardcoded in `psg/benchmark.py` |
| `datasets/fabrication_indicators.json` | **new** — formerly hardcoded regexes in `psg/security/classifier.py` |
| `eval/baseline_v4.3.0.json`      | **new** — regression anchor |

## If something breaks

1. Check `CHANGELOG.md` for the specific phase that introduced the change.
2. Consult this migration guide.
3. File an issue with your PSG version, command line, and the error.

Most v5 breaking changes are opt-outable via flags (`--allow-public`,
`--ensemble-mode short_circuit`, `fail_open=True`). The changes that
cannot be opted out of are the data-model additions (safe — only
additions, with defaults) and the monkeypatch target moves (three import
path updates documented above).
