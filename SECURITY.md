# Security Policy

## Threat Model

PSG is a **defensive-testing** tool. This section documents what PSG does and
does not protect against so users can integrate it with realistic expectations.

### Components and trust boundaries

```
┌──────────────┐   stdin/argv    ┌──────────────────────────┐
│  operator    │ ───────────────▶│  psg CLI / psg serve     │
└──────────────┘                 └──────────────────────────┘
                                            │
                                            │ HTTP
                                            ▼
                                 ┌──────────────────────────┐
                                 │  target LLM endpoint     │
                                 │  (OpenAI-compatible API) │
                                 └──────────────────────────┘
                                            ▲
                                            │ HTTP (optional)
                                            │
                                 ┌──────────────────────────┐
                                 │  judge LLM endpoint      │
                                 └──────────────────────────┘
```

The CLI and server both trust:
- **The operator** (command-line args, config files on disk).
- **The catalog JSON** they load from `datasets/`.
- **Their own Python environment** (`pip install -e .`).

They do **not** trust:
- **Model responses.** Every response is treated as untrusted data, subject
  to classification before any reporting/rendering.
- **The network path** to the target / judge endpoint. Transport validates
  TLS through `requests`; SSRF protection blocks private/loopback/link-local
  targets by default (`psg/validation/network.py`).
- **Third-party catalogs.** `load_catalog()` only extracts `prompt`, `id`,
  `metadata`, and `followups`; it does not `eval()` or execute anything.

### What PSG protects against

| Threat                                       | Control in PSG |
|----------------------------------------------|---|
| Exfiltration of the target host via `--base-url` | `validate_url()` blocks private/loopback/link-local IPs and non-http(s) schemes; requires `--allow-insecure-http` to hit `http://` targets. |
| Credential leakage in reports                | `redact_text()` rewrites Anthropic / OpenAI / GitHub / Slack / Google / Stripe / Bearer / generic-assignment formats before anything is written to disk. |
| Canary-token leakage in model output         | `DefenseLayer` normalizes both the needle and haystack before comparison; multi-token reports include every leaked canary. |
| Silent classifier failure                    | `RunSummary.detector_failures` counts UNKNOWN verdicts; `psg scan` returns exit code 5 when ≥10% of attacks were unclassifiable. |
| Unauthenticated access to `psg serve`        | `--api-key` / `PSG_SERVE_API_KEY` requires `X-API-Key` on all routes except `/health`. Constant-time comparison. |
| External exposure of `psg serve`             | Default bind is `127.0.0.1`. `--allow-public` required for `0.0.0.0`, with stderr warning. |
| Oversized request DOS on `psg serve`         | 64 KiB request-body cap via middleware. |
| Rate-limit evasion on target API             | Transport honors `Retry-After` on 429 (capped 60 s). Token-bucket rate limiter on parallel workers (`--rate-limit`). |
| Supply-chain substitution (HF model)         | `WildGuardClassifier` pins the HuggingFace model revision. |
| Replay / caching of attacker content         | Per-call random delimiters in the LLM judge prompt prevent a response from closing the request/response block and injecting instructions to the judge. |

### What PSG does **not** protect against

| Out of scope                                  | Mitigation to consider |
|-----------------------------------------------|---|
| The target model being genuinely jailbroken. PSG detects the attempt; it does not fix the model. | RLHF / safety fine-tuning on the target. |
| Adversarial content that is classification-evasive but still harmful. The detector is a heuristic + LLM judge, not a proof. | Treat `flagged=False` as a signal, not a guarantee; add human review. |
| DNS rebinding / TOCTOU between SSRF validation and the actual fetch. | Run PSG in a network environment that cannot reach internal services. |
| A compromised judge endpoint issuing forged "SAFE" verdicts. | Use a trusted judge; cross-check with the keyword detector via `--ensemble-mode any`. |
| Operator-supplied prompts that are themselves harmful. | Review `datasets/` entries; PSG executes what you feed it. |
| Side-channel exfiltration from model output (e.g. Unicode steganography). | Enable strict redaction (`--redaction strict`) and review raw outputs. |
| Plug-in / extension code loaded via entry points or `custom_detectors`. These run in-process with full privileges. | Only install plug-ins you trust. |

### Fail-open vs. fail-closed defaults

| Component                                       | Default | Rationale |
|-------------------------------------------------|---------|-----------|
| LangChain `PSGGuardMiddleware` classifier error | **fail-closed** (raises) | A security middleware that fails open defeats its purpose. Opt in with `fail_open=True`. |
| LLM judge UNKNOWN verdict                       | surfaced as `detector_failed=True` | Never silently green-lights a scan. Operator sees the count. |
| Server `/health` on classifier failure          | returns 503 | Load balancer can pull a broken instance out of rotation. |
| Server `/screen` without `--api-key`            | no auth required | Operator opt-in; when a key *is* set, auth is strictly enforced. |
| Transport on 4xx (non-429)                      | raises immediately | Client bugs should fail loudly, not silently retry. |
| Transport on 5xx / 429                          | retries with backoff / Retry-After | Normal transient-fault handling. |

### Audit touchpoints

If you are auditing a deployment:
- Run `psg eval --golden <your-golden.json>` to pin classifier performance.
  F1 < 0.85 indicates the detector is drifting against your baseline.
- Check `psg scan`'s final line for `detector_failures=N`; N > 0 means
  some attacks had no confident verdict.
- `bandit -r psg/ -ll` and `pip-audit --strict .` are part of CI; re-run
  them after any dependency change.

## Reporting Vulnerabilities

### In This Repository

If you discover a security vulnerability in this repository's code or tooling:

1. **Do not** open a public issue.
2. Use **GitHub Security Advisories** (private report) in this repository.
3. If private advisories are unavailable, open an issue with minimal detail and request a private contact channel.
4. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

Target response time: within 72 hours.

### In External Systems

This repository is for **defensive and educational research**.
If you discover a vulnerability in an external AI system:

1. Follow responsible disclosure practices
2. Contact the affected vendor's security team
3. Allow reasonable patching time (typically 90 days)
4. Avoid public disclosure before remediation

## Scope

### In Scope

- Security issues in tools and scripts in this repository
- Vulnerable defaults or unsafe behaviors in included examples
- Documentation errors that could cause unsafe use

### Out of Scope

- Vulnerabilities in third-party/commercial AI services
- Feature requests
- General AI security discussions (use Discussions)

## Security Updates

Security fixes are:

1. Committed to `main`
2. Noted in `CHANGELOG.md`
3. Published via Security Advisory when appropriate

## Responsible Use

- Use this project only on systems you own or are authorized to test.
- Follow applicable laws and regulations.
- Do not use these techniques to cause harm.

---

*Last updated: April 2026 (v5.0.0 release)*
