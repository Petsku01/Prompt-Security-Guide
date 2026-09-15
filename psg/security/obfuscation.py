"""Character-level obfuscation detection for prompt_screen (Parseltongue family).

Covers the G0DM0D3 Parseltongue mechanism: 33 trigger words obfuscated via 6
character-level techniques (leetspeak, unicode homoglyphs, zero-width
insertion, mixed case, phonetic, random). Upstream:
elder-plinius/G0DM0D3 (AGPL-3.0).

Design (v12, measured on datasets/parseltongue_attacks.json = 594 prompts,
0 false positives on benign security prose):

1. ARTIFACT GATE: a word qualifies only if it carries character-level
   tampering evidence — a zero-width char, or any char outside plain ASCII
   letters (digit, leet symbol, homoglyph, fullwidth form). This is what
   keeps real English prose ('hackers', 'crackdown', 'great') from fuzzy-
   matching triggers: real words have no artifacts.
2. FOLD: NFKC -> multi-char leet tokens (|3->b, }{->h, |2->r, 124->cra...)
   -> single-char leet/homoglyph fold -> zero-width strip.
3. FUZZY MATCH: folded word within edit distance 1 (trigger len<5) or
   2 (len>=5) of a trigger, or containing the trigger.
4. VERBATIM GUARD: if the trigger appears as a case-insensitive substring
   anywhere in the raw prompt, this detector stays silent — plain prose
   about hacking is not an obfuscation signal.
5. CASE DETECTOR: an irregular-case word (hAcK, HaCK) within fuzzy distance
   of a trigger — case alone is an artifact, invisible to the fold gate.

Known limits (documented): phonetic-only transforms (hack->hak) carry no
artifact and are not detected; ~5% of heavy leetspeak/unicode composites
still evade (fold collisions inside multi-word tokens).
"""

from __future__ import annotations

import re
import string
import unicodedata

# Multi-char leet tokens — replaced BEFORE single-char folds (longest first).
_LEET_MULTI: dict[str, str] = {
    "|3": "b",
    "13": "b",
    "|)": "d",
    "|>": "d",
    "|=": "f",
    "|<": "k",
    "|{": "k",
    "|_": "l",
    "|V|": "m",
    "|\\|": "n",
    "|_|": "u",
    "|2": "r",
    "12": "r",
    "|*": "p",
    "0_": "q",
    "()_": "q",
    "7_": "z",
    "}{": "h",
    "|-|": "h",
    "\\/\\/": "w",
    "\\/": "v",
    "><": "x",
    "124": "cra",
    "()": "o",
    "/\\/": "n",
    "/\\/\\": "m",
    "`/": "y",
}

# Single-char leet + Unicode homoglyph folds (from G0DM0D3 LEET_MAP /
# UNICODE_HOMOGLYPHS, plus normalize.HOMOGLYPH_MAP coverage).
_LEET_SINGLE: dict[str, str] = {
    "а": "a",
    "ɑ": "a",
    "α": "a",
    "ạ": "a",
    "ａ": "a",
    "@": "a",
    "∂": "a",
    "λ": "a",
    "Ь": "b",
    "ḅ": "b",
    "ｂ": "b",
    "ß": "b",
    "с": "c",
    "ϲ": "c",
    "ⅽ": "c",
    "ｃ": "c",
    "¢": "c",
    "©": "c",
    "<": "c",
    "(": "c",
    "ԁ": "d",
    "ⅾ": "d",
    "ｄ": "d",
    "đ": "d",
    "е": "e",
    "ė": "e",
    "ẹ": "e",
    "ｅ": "e",
    "€": "e",
    "£": "e",
    "∑": "e",
    "ƒ": "f",
    "ｆ": "f",
    "ɡ": "g",
    "ｇ": "g",
    "&": "g",
    "9": "g",
    "6": "g",
    "һ": "h",
    "ḥ": "h",
    "ｈ": "h",
    "#": "h",
    "і": "i",
    "ι": "i",
    "ｉ": "i",
    "¡": "i",
    "1": "i",
    "!": "i",
    "ϳ": "j",
    "ｊ": "j",
    "¿": "j",
    "κ": "k",
    "ｋ": "k",
    "ӏ": "l",
    "ⅼ": "l",
    "ｌ": "l",
    "|": "l",
    "м": "m",
    "ｍ": "m",
    "µ": "m",
    "ո": "n",
    "ｎ": "n",
    "η": "n",
    "о": "o",
    "ο": "o",
    "ｏ": "o",
    "°": "o",
    "ø": "o",
    "0": "o",
    "р": "p",
    "ρ": "p",
    "ｐ": "p",
    "þ": "p",
    "ѕ": "s",
    "∫": "s",
    "$": "s",
    "5": "s",
    "τ": "t",
    "ｔ": "t",
    "†": "t",
    "⊤": "t",
    "+": "t",
    "7": "t",
    "υ": "u",
    "ｕ": "u",
    "ü": "u",
    "ν": "v",
    "ｖ": "v",
    "√": "v",
    "ѡ": "w",
    "ｗ": "w",
    "ω": "w",
    "х": "x",
    "ｘ": "x",
    "×": "x",
    "у": "y",
    "γ": "y",
    "ｙ": "y",
    "¥": "y",
    "ᴢ": "z",
    "ｚ": "z",
    "2": "z",
    "8": "b",
    "4": "a",
    "3": "e",
}

# Trigger vocabulary (G0DM0D3 DEFAULT_TRIGGERS, first 33 unique).
OBF_TRIGGERS: tuple[str, ...] = (
    "hack",
    "exploit",
    "bypass",
    "crack",
    "break",
    "attack",
    "penetrate",
    "inject",
    "manipulate",
    "override",
    "disable",
    "circumvent",
    "evade",
    "malware",
    "virus",
    "trojan",
    "payload",
    "shellcode",
    "rootkit",
    "keylogger",
    "backdoor",
    "vulnerability",
    "weapon",
    "bomb",
    "explosive",
    "poison",
    "drug",
    "synthesize",
    "jailbreak",
    "unlock",
    "root",
    "sudo",
    "admin",
)

_ZW_CHARS = "\u200b\u200c\u200d\ufeff"
_ASCII_LETTERS = frozenset(string.ascii_letters)
# Trim ONLY true punctuation — leet symbols ({(|< ...) are signal, not noise.
_TRIM_CHARS = "\"'.,!?;:—–…«»„“”"

_WORD_RE = re.compile(r"\S+")
_ALPHA_RUN_RE = re.compile(r"[A-Za-z]{3,}")
# Standard PascalCase compound (RootKit, MacBook): EVERY segment is
# Cap+lowercase — acronym-like cap runs (AdminUI's 'UI') are excluded here
# and pass through to the exact-match check instead.
_PASCALCASE_RE = re.compile(r"[A-Z][a-z]+(?:[A-Z][a-z]+)*$")

# Deterministic phonetic substitution (upstream G0DM0D3 applyPhonetic).
# Triggers whose phonetic form differs from the plain form get an exact
# second matching path in _obfuscated_trigger: 'hack'->'hak', 'crack'->'krak'
# are pure-alpha non-words no artifact gate will ever see.
def _phonetic(word: str) -> str:
    w = re.sub("ph", "f", word, flags=re.I)
    w = re.sub("ck", "k", w, flags=re.I)
    w = re.sub("x", "ks", w, flags=re.I)
    w = re.sub("qu", "kw", w, flags=re.I)
    w = re.sub("c(?=[eiy])", "s", w, flags=re.I)
    return re.sub("c", "k", w, flags=re.I)


_PHONETIC_VARIANTS: dict[str, str] = {
    t: _phonetic(t) for t in OBF_TRIGGERS if _phonetic(t) != t
}


def _fold_word(word: str) -> str:
    """De-obfuscate a single token: NFKC, multi-leet, single fold, ZW strip."""
    t = unicodedata.normalize("NFKC", word)
    for k in sorted(_LEET_MULTI, key=len, reverse=True):
        t = t.replace(k, _LEET_MULTI[k])
    t = "".join(_LEET_SINGLE.get(c, c) for c in t)
    return "".join(c for c in t if c not in _ZW_CHARS)


def _has_artifact(word: str) -> bool:
    """Word carries tampering evidence: zero-width or non-ASCII-letter char."""
    if any(c in _ZW_CHARS for c in word):
        return True
    return any(c not in _ASCII_LETTERS for c in word)


def _edit_distance(a: str, b: str) -> int:
    if abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _allowed_distance(trigger: str) -> int:
    return 1 if len(trigger) < 5 else 2


def _obfuscated_trigger(prompt: str) -> str | None:
    """Return a trigger word that only appears after de-obfuscation.

    Per-token design (Sol review 2026-09-15, all 4 findings verified; benign
    corpus 400 sentences: initial 7 FPs fixed, now 0):
    - Guard is PER TOKEN, not global: a token containing the plain trigger
      (case-insensitive substring) is skipped for that trigger, so padding a
      plain trigger word elsewhere cannot silence detection of an obfuscated
      token elsewhere in the prompt.
    - Non-ZW artifacts (digits, leet symbols, homoglyphs) must actually
      transform the token's ASCII-alpha core during folding — an appended
      emoji or stray punctuation alone never enables fuzzy matching.
    - Zero-width chars are always strong obfuscation evidence.
    - PascalCase/camelCase product names (RootKit, AdminUI) are never case
      obfuscation — case detector skips them.
    - Digit-heavy tokens (version strings, addresses: v1.12.4, Build 124,
      Route 124) are skipped — leet folds ('124'->'cra') inside them are
      coincidental, not obfuscation. A digit artifact counts only when the
      token also contains ASCII letters it could be hiding.
    """
    for raw in _WORD_RE.findall(prompt):
        word = raw.strip(_TRIM_CHARS)
        if not word:
            continue
        has_zw = any(c in _ZW_CHARS for c in word)
        word_lower = word.lower()
        # Deterministic phonetic path FIRST: pure-alpha tokens (hak, krak,
        # eksploit) carry no artifact but exactly match the upstream
        # applyPhonetic transform of a trigger. No fuzzy matching here.
        raw_alpha = "".join(c for c in word_lower if c in string.ascii_lowercase)
        if not has_zw and raw_alpha.isalpha():
            for trig, ph in _PHONETIC_VARIANTS.items():
                if raw_alpha == ph:
                    return trig
        if not has_zw and not _has_artifact(word):
            continue
        core = "".join(c for c in _fold_word(word_lower).lower() if c.isalnum())
        if not core:
            continue
        # ASCII-alpha skeleton of the raw token (ZW already excluded).
        raw_alpha = "".join(c for c in word_lower if c in string.ascii_lowercase)
        if not has_zw and core == raw_alpha:
            continue  # artifact did not transform the word (emoji, hyphen, ...)
        if not has_zw and re.search(r"\d{2,}", word_lower):
            # A digit run of 2+ is semantic (versions, addresses, dates):
            # leet folds inside it ('124'->'cra') are coincidental.
            continue
        for trig in OBF_TRIGGERS:
            if trig in word_lower:
                continue  # this token carries the trigger verbatim — plain
            if trig in core:
                return trig
            if _edit_distance(core, trig) <= _allowed_distance(trig):
                return trig
    return None


def _case_obfuscated_trigger(prompt: str) -> str | None:
    """Return a trigger whose word appears with deliberately irregular case
    (hAcK, HaCK) — case is an artifact the fold cannot see.

    Per-token verbatim guard (benign corpus 400: 'RootKit' is a product
    name whose lowercase contains 'rootkit' — plain, not obfuscated).
    Exact match only: CamelCase identifiers (AdminUI) must not fuzzy-match.
    """
    for w in _ALPHA_RUN_RE.findall(prompt):
        if w.islower() or w.istitle() or w.isupper():
            continue
        if _PASCALCASE_RE.fullmatch(w):
            continue  # standard camel/pascal compound (RootKit), not mangled
        low = w.lower()
        if low in OBF_TRIGGERS:
            return low
    return None
