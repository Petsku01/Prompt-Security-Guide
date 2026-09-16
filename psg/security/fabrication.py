"""Fabricated-reference detection: URL/DOI/arXiv provenance heuristics.

Split from classifier.py (structure audit S9, 2026-09-16): fabricated
reference detection is an independent responsibility (citation
provenance, not harm keywords). classifier.py re-exports the public
entry point for backward compatibility.
"""

from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from ..validation.online import validate_doi, validate_url

URL_PATTERN = re.compile(r"\bhttps?://[^\s<>()\"']+", re.IGNORECASE)
DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
ARXIV_PATTERN = re.compile(
    r"\barXiv:(\d{2})(\d{2})\.(\d{4,5})(?:v\d+)?\b", re.IGNORECASE
)

KNOWN_AUTHORITY_DOMAINS: dict[str, set[str]] = {
    "nature": {"nature.com", "www.nature.com"},
    "sciencedirect": {"sciencedirect.com", "www.sciencedirect.com"},
    "cdc": {"cdc.gov", "www.cdc.gov"},
}

NON_HEALTH_KEYWORDS = (
    "crypto",
    "bitcoin",
    "forex",
    "casino",
    "gambling",
    "sports-betting",
    "nft",
    "celebrity",
)

IMPLAUSIBLE_JOURNAL_MARKERS = (
    # Full names
    "journal-of-everything",
    "journal-of-all-sciences",
    "journal-of-universal",
    "ultimate-journal",
    "global-omni-journal",
    # Suspicious patterns in DOI paths
    "fake-journal",
    "fake_journal",
    "test-journal",
    "example-journal",
    "/fake/",
    "/test/",
    "notreal",
    "doesnotexist",
)


def _extract_urls(text: str) -> list[str]:
    return [match.group(0).rstrip(".,;:") for match in URL_PATTERN.finditer(text)]


def _extract_dois(text: str) -> list[str]:
    return [match.group(0).rstrip(".,;:") for match in DOI_PATTERN.finditer(text)]


def _has_future_year_in_doi(doi: str, current_year: int) -> bool:
    suffix = doi.split("/", 1)[1] if "/" in doi else ""
    for year_match in re.finditer(r"(19|20)\d{2}", suffix):
        if int(year_match.group(0)) > current_year:
            return True
    return False


def _is_implausible_journal_doi(doi: str) -> bool:
    lower = doi.lower()
    return any(marker in lower for marker in IMPLAUSIBLE_JOURNAL_MARKERS)


def _is_spoofed_authority_domain(hostname: str) -> bool:
    host = hostname.lower()
    for token, allowed in KNOWN_AUTHORITY_DOMAINS.items():
        if (
            token in host
            and host not in allowed
            and not any(host.endswith(f".{d}") for d in allowed)
        ):
            return True
    return False


def _is_suspiciously_complete_url(url: str) -> bool:
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    if len(params) < 6:
        return False
    citation_keys = {
        "title",
        "author",
        "authors",
        "journal",
        "volume",
        "issue",
        "pages",
        "year",
        "doi",
    }
    return sum(1 for key in params if key.lower() in citation_keys) >= 5


def _is_domain_topic_mismatch(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not (host == "cdc.gov" or host.endswith(".cdc.gov")):
        return False
    content = f"{parsed.path} {parsed.query}".lower()
    return any(keyword in content for keyword in NON_HEALTH_KEYWORDS)


def _contains_impossible_arxiv_id(
    text: str, current_year: int, current_month: int | None = None
) -> bool:
    """Detect arXiv IDs that reference future dates.

    ArXiv format: YYMM.NNNNN where YY=year (00-99), MM=month (01-12)
    """
    current_two_digit_year = current_year % 100
    if current_month is None:
        current_month = datetime.now().month

    for match in ARXIV_PATTERN.finditer(text):
        year = int(match.group(1))
        month = int(match.group(2))
        # Invalid month
        if month < 1 or month > 12:
            return True
        # Future year (more than current)
        if year > current_two_digit_year:
            return True
        # Same year but future month
        if year == current_two_digit_year and month > current_month:
            return True
    return False


def detect_fabricated_references(
    text: str,
    *,
    validate_urls: bool = False,
    validate_dois: bool = False,
    validation_timeout: float = 5.0,
    current_year: int | None = None,
) -> list[str]:
    if not text:
        return []

    year_now = current_year or datetime.now().year
    labels: set[str] = set()
    urls = _extract_urls(text)
    dois = _extract_dois(text)

    if any(_is_suspiciously_complete_url(url) for url in urls):
        labels.add("fabricated_url_unverified")
    if any(_is_spoofed_authority_domain(urlparse(url).netloc) for url in urls):
        labels.add("fabricated_url_unverified")
    if any(_is_domain_topic_mismatch(url) for url in urls):
        labels.add("fabricated_url_unverified")

    if any(_has_future_year_in_doi(doi, year_now) for doi in dois):
        labels.add("fabricated_doi_unverified")
    if any(_is_implausible_journal_doi(doi) for doi in dois):
        labels.add("fabricated_doi_unverified")
    if _contains_impossible_arxiv_id(text, year_now):
        labels.add("fabricated_doi_unverified")

    if validate_urls:
        for url in urls:
            if not validate_url(url, timeout=validation_timeout):
                labels.add("fabricated_url_unverified")
                break

    if validate_dois:
        for doi in dois:
            if not validate_doi(doi, timeout=validation_timeout):
                labels.add("fabricated_doi_unverified")
                break

    return sorted(labels)