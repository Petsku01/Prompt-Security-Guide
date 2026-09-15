"""Clean web-scrape junk from model profiles + report what was removed.

Removal rule (conservative): a prompt is junk if it contains web/UI debris
markers (skip to main content, cookie consent, subscribe, sign in, github
chrome, license headers, export KEY=) or is a code/pipeline snippet rather
than an attack prompt (<40 visible chars, no imperative question/request
structure). Junk rows are dropped; everything else is kept untouched.
"""
import glob
import json

JUNK_MARKERS = (
    "skip to main content",
    "cookie",
    "sign in",
    "subscribe",
    "all reactions",
    "we gratefully acknowled",
    "privacy policy",
    "terms of service",
    "©",
    "export bedrock",
    "pip install",
    "readme",
    "license",
)


def is_junk(p: dict) -> bool:
    t = (p.get("prompt") or "").strip()
    if len(t) < 40:
        return True
    low = t.lower()
    if any(m in low[:250] for m in JUNK_MARKERS):
        return True
    return False


total_removed = 0
for f in sorted(glob.glob("datasets/profiles/*_attacks.json")):
    d = json.load(open(f))
    attacks = d.get("attacks") or []
    keep, removed = [], []
    for p in attacks:
        (removed if is_junk(p) else keep).append(p)
    if removed:
        d["attacks"] = keep
        d["attack_count"] = str(len(keep))
        with open(f, "w") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        fam = d.get("model_family", "?")
        total_removed += len(removed)
        print(f"{fam:10} -{len(removed)} (jadet poistettu, {len(keep)} jaljella)")
print("YHTEENSA poistettu:", total_removed)