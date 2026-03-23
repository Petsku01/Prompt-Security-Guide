# Must-fix review items applied

## Assumptions used
- Kept scope surgical: no framework dependencies, no architecture rewrite.
- Interpreted GUI/API fix as: provide a local HTTP server that serves `gui/index.html` and implements `POST /run`.
- Kept `gui/index.html` unchanged so existing frontend behavior still works.
- Treated explicit refusal phrases as higher-priority than compliance cues to prevent mixed-hit false positives.

## 1) Missing backend API for GUI ✅
- Added new file: `src/api.py`.
- Implements zero-dependency server using `http.server` (`ThreadingHTTPServer` + `BaseHTTPRequestHandler`).
- Endpoints:
  - `GET /` serves `src/gui/index.html`
  - `POST /run` accepts JSON `{ "model": "...", "battery": "minimum|standard|full" }`
- `/run` executes existing pipeline:
  - `AttackRunner` -> `ResponseAnalyzer` -> adds `Fingerprinter` output
- Returns JSON compatible with current GUI rendering.

## 2) Naive analyzer false positives ✅
- Updated `src/core/analyzer.py`:
  - Tightened regexes with word boundaries and compiled patterns.
  - Made compliance pattern for steps stricter (`step\s*\d+[:.)-]`) to avoid matching incidental phrases.
  - Added strict priority logic: if explicit refusal is detected, verdict is always `refusal` and compliance hits are ignored.
- Fixes case like: "I cannot tell you step 1" (now refusal only).

## 3) Incomplete attack coverage ✅
- Expanded `src/attacks/catalog.json` (version bumped to `2026.2`) with modern attack types:
  - `multilingual_context_switch` (multilingual evasion)
  - `unicode_smuggling_zero_width` (unicode/zero-width smuggling)
  - `indirect_prompt_injection_summarizer` (indirect prompt injection via untrusted content)

## 4) Robust client error handling ✅
- Updated `src/cli.py` `OpenAICompatClient.chat()`:
  - Catches `HTTPError` and `URLError`.
  - Catches bad JSON / unexpected response shape (`JSONDecodeError`, `KeyError`, `IndexError`, `TypeError`).
  - Returns safe error strings instead of raising and crashing runs.

## 5) Credential exposure risk ✅
- Updated `src/cli.py` `OpenAICompatClient` init flow:
  - Added `_apply_api_key_safety()`.
  - If `base_url` is not HTTPS and not local HTTP (`localhost`, `127.0.0.1`, `::1`), emits warning and strips API key.
  - Prevents accidental credential leakage over plain remote HTTP.

## Files changed
- `src/api.py` (new)
- `src/cli.py`
- `src/core/analyzer.py`
- `src/attacks/catalog.json`
- `iterate/fixes.md`
