# PSG Gap Analysis and Improvement Roadmap (2026-03-24)

## Brutally Honest Current State

PSG is a solid **batch scanner CLI** with a pragmatic dataset workflow, but it is not yet a full security platform.

What is real today:
- Single-process CLI scan engine (`python -m psg scan`)
- OpenAI-compatible model transport with retries and SSRF guardrails
- Detector modes: keyword, llm-judge, ensemble
- Basic reporting (`report.json`, `report.txt`, `defense_report.txt`)
- Valuable dataset curation effort (OWASP 2025, JailbreakBench subset, auto-discovered vectors)
- Daily automation pipeline for discovery/generation/testing (mostly internal tooling style)

What is missing relative to positioning:
- No runtime API product mode (request-time screening endpoint)
- No plugin/extension architecture for custom probes/detectors/reporters
- No true parallel/distributed multi-model execution in core runtime
- No continuous monitoring loop with alerting/SIEM-native outputs in core product
- No first-class LangChain/LlamaIndex middleware package
- No visual dashboard in active runtime (only text/json reports)
- No standardized benchmark runner with confidence intervals in shipped CLI
- Defense guidance exists but was historically descriptive, not actionable by default
- No automated remediation loop (policy update suggestions, CI guardrails, auto-ticketing)

## Competitor Gap Matrix (PSG vs Garak/Rebuff/LLM Guard/Lakera)

Legend: `Strong` = clearly present, `Partial` = limited/manual, `Gap` = not first-class.

| Capability | PSG | NVIDIA Garak | Rebuff | LLM Guard | Lakera Guard |
|---|---|---|---|---|---|
| Real-time API mode | Gap | Partial | Partial | Partial | Strong |
| Plugin architecture | Gap | Strong | Partial | Partial | Strong (managed platform controls) |
| Multi-model testing | Partial | Strong | Gap | Partial | Strong |
| Continuous monitoring | Partial (automation scripts) | Partial | Partial | Partial | Strong |
| LangChain/LlamaIndex integration | Gap | Partial | Partial | Partial | Strong/partner integrations |
| Visual dashboards | Gap | Partial | Partial | Gap | Strong |
| Standard benchmark workflows | Partial | Strong | Gap | Partial | Partial |
| Defense recommendations | Partial (now improved) | Partial | Partial | Partial | Strong (policy-centric UX) |
| Automated remediation | Gap | Gap | Gap | Gap | Partial |

### Specific strategic delta
- Versus **Garak**: PSG lacks breadth/depth of probe ecosystem and extension model.
- Versus **Rebuff**: PSG is broader, but lacks lightweight drop-in app middleware ergonomics.
- Versus **LLM Guard**: PSG has stronger attack catalog posture, weaker runtime guard integration story.
- Versus **Lakera**: PSG cannot currently compete on managed, real-time enterprise observability.

## PSG Unique Strengths (Ownable)

1. **Attack intelligence velocity**: practical daily vector discovery pipeline already exists.
2. **Red-team-first workflow**: easier to run offensive-style evaluations than many defensive-only tools.
3. **Open, inspectable stack**: transparent datasets and classifier logic.
4. **Low-friction local model testing**: strong Ollama-oriented workflows.
5. **Defensive testing niche**: can own “continuous jailbreak regression testing for local/open models” if productized.

## 10 High-Impact Improvements (Prioritized by Impact/Effort)

| Priority | Improvement | Why it matters | Effort |
|---|---|---|---|
| 1 | Add runtime screening API (`psg serve`) with sync/async `/screen` endpoint | Converts PSG from offline tool to production guardrail building block | M |
| 2 | Ship LangChain/LlamaIndex middleware adapters | Immediate adoption lift in real app stacks | S |
| 3 | Implement plugin interfaces for probes/detectors/reporters | Unblocks ecosystem and enterprise customization | M |
| 4 | Add parallel execution in core orchestrator (`--workers`, `--models`) | Massive throughput gains for benchmarking and CI | M |
| 5 | Standard benchmark command (`psg benchmark`) with JBB/OWASP presets + confidence intervals | Credible competitive claims and reproducible scorecards | M |
| 6 | Build HTML dashboard report artifact with trend charts | Better stakeholder communication and decision speed | M |
| 7 | Add continuous monitoring mode (scheduled runs + delta alerts) | Moves from one-off tests to ongoing risk management | M |
| 8 | Add policy-specific defense recommendation engine (rule-driven) | Shortens time from finding to mitigation | S |
| 9 | Add CI/CD “security gate” action (fail build on threshold regression) | Makes PSG operationally enforceable | S |
| 10 | Add remediation playbooks with auto-generated patch suggestions for system prompts/filters | Differentiates PSG from scanner-only competitors | L |

## Improvement Roadmap

## Quick Wins (This Week)

1. **Defense recommendations in reports** (shipped in this change)
- Add prioritized, actionable remediation guidance based on observed failures.
- Success metric: every defense report contains at least one concrete action.

2. **LangChain adapter (minimal package)**
- `PSGGuardMiddleware` for request/response checks.
- Success metric: demo app integration in <15 lines.

3. **CI regression gate command**
- `psg eval --golden datasets/classifier_golden.json --fail-on-macro-f1-below 0.85`
- Success metric: ready for GitHub Actions usage.

4. **Parallel scan flag in orchestrator**
- `--workers N` for attack-level concurrency.
- Success metric: 2-4x speedup on standard catalog.

5. **Benchmark preset command scaffold**
- `psg benchmark --preset jbb --model ...`
- Success metric: one-command standardized run.

## Near-Term (2-6 Weeks)

1. Runtime API server (`psg serve`) with auth and structured policy responses.
2. Plugin system (`entry_points`) for custom detectors/probes.
3. HTML report with trend visualization from historical results.
4. Multi-model matrix execution + comparative output artifact.
5. Alerting adapters (Slack/Discord/webhook) for regression deltas.

## Moonshots (3-6 Months)

1. **Continuous Security Control Plane**
- Persistent project model, trend analytics, policy baselines, severity queues.

2. **Auto-remediation pipeline**
- Recommend prompt/policy/filter patches; optional PR generation for policy repos.

3. **Adaptive adversarial generation loop**
- Agentic attack mutation engine that prioritizes unexplored failure surfaces.

4. **Enterprise governance layer**
- Team RBAC, audit logs, signed reports, SIEM-native exports, compliance packs.

## Positioning Recommendation

Do not try to out-Lakera Lakera on managed runtime first.
Own the category: **"open continuous jailbreak regression platform for model teams"**,
then expand to runtime guard APIs once integration ergonomics are strong.
