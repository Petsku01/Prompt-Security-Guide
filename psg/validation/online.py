from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

import requests

DEFAULT_TIMEOUT_SECONDS = 5.0
_USER_AGENT = "PromptSecurityGuide/4.x validation"


def validate_url(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bool:
    return _validate_url_cached(url, float(timeout))


@lru_cache(maxsize=2048)
def _validate_url_cached(url: str, timeout: float) -> bool:
    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
    except requests.RequestException:
        return False
    return 200 <= response.status_code < 400


def validate_doi(doi: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> bool:
    return _validate_doi_cached(doi.strip(), float(timeout))


@lru_cache(maxsize=2048)
def _validate_doi_cached(doi: str, timeout: float) -> bool:
    encoded = quote(doi, safe="")
    url = f"https://api.crossref.org/works/{encoded}"
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
        )
    except requests.RequestException:
        return False
    return 200 <= response.status_code < 400


def clear_validation_cache() -> None:
    _validate_url_cached.cache_clear()
    _validate_doi_cached.cache_clear()
