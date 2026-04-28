"""Text normalization for obfuscation detection.

Normalizes text to catch common evasion techniques:
- Leetspeak: k3ylogg3r → keylogger
- Unicode homoglyphs: Cyrillic/Greek lookalikes → ASCII
- Base64: embedded encoded segments → decoded
"""

import base64
import binascii
import re
import unicodedata
from typing import Optional


# Leetspeak translation map
LEETSPEAK_MAP = {
    "0": "o",
    "1": "i",
    "2": "z",  # Sometimes used for z
    "3": "e",
    "4": "a",
    "5": "s",
    "6": "g",
    "7": "t",
    "8": "b",
    "9": "g",
    "@": "a",
    "$": "s",
    "!": "i",
    "|": "l",
    "+": "t",
}

# Common Unicode homoglyphs (Cyrillic, Greek, etc. that look like Latin)
HOMOGLYPH_MAP = {
    # Cyrillic
    "а": "a",  # Cyrillic а
    "е": "e",  # Cyrillic е
    "о": "o",  # Cyrillic о
    "р": "p",  # Cyrillic р
    "с": "c",  # Cyrillic с
    "у": "y",  # Cyrillic у
    "х": "x",  # Cyrillic х
    "А": "A",  # Cyrillic А
    "В": "B",  # Cyrillic В
    "Е": "E",  # Cyrillic Е
    "К": "K",  # Cyrillic К
    "М": "M",  # Cyrillic М
    "Н": "H",  # Cyrillic Н
    "О": "O",  # Cyrillic О
    "Р": "P",  # Cyrillic Р
    "С": "C",  # Cyrillic С
    "Т": "T",  # Cyrillic Т
    "Х": "X",  # Cyrillic Х
    # Greek
    "α": "a",  # Greek alpha
    "ο": "o",  # Greek omicron
    "ε": "e",  # Greek epsilon
    # Special characters
    "ı": "i",  # Turkish dotless i
    "ł": "l",  # Polish l with stroke
    "ñ": "n",  # Spanish ñ (for completeness)
}

# Base64 pattern: at least 8 chars, valid base64 alphabet, optional padding
BASE64_PATTERN = re.compile(
    r"(?<![A-Za-z0-9+/=])"  # Not preceded by base64 chars
    r"([A-Za-z0-9+/]{8,}={0,2})"  # 8+ chars with optional padding
    r"(?![A-Za-z0-9+/=])",  # Not followed by base64 chars
    re.ASCII,
)


def translate_leetspeak(text: str) -> str:
    """Convert leetspeak to standard ASCII.

    Args:
        text: Input text possibly containing leetspeak

    Returns:
        Text with leetspeak characters converted to letters

    Example:
        >>> translate_leetspeak("k3ylogg3r")
        'keylogger'
    """
    result = []
    for char in text:
        result.append(LEETSPEAK_MAP.get(char, char))
    return "".join(result)


def translate_homoglyphs(text: str) -> str:
    """Convert Unicode homoglyphs to ASCII equivalents.

    Args:
        text: Input text possibly containing homoglyphs

    Returns:
        Text with homoglyphs converted to ASCII

    Example:
        >>> translate_homoglyphs("kеyloggеr")  # Cyrillic е
        'keylogger'
    """
    result = []
    for char in text:
        result.append(HOMOGLYPH_MAP.get(char, char))
    return "".join(result)


def _try_decode_base64(s: str) -> Optional[str]:
    """Attempt to decode a base64 string.

    Returns decoded text if valid UTF-8, None otherwise.
    """
    try:
        # Add padding if needed
        padding = 4 - (len(s) % 4)
        if padding != 4:
            s = s + "=" * padding

        decoded = base64.b64decode(s, validate=True)
        # Only return if it's valid UTF-8 text (not binary)
        text = decoded.decode("utf-8")
        # Only return if it looks like actual text (mostly printable)
        if text and sum(c.isprintable() or c.isspace() for c in text) / len(text) > 0.8:
            return text
    except (ValueError, UnicodeDecodeError, binascii.Error):
        pass
    return None


def decode_base64_segments(text: str) -> str:
    """Find and decode base64-encoded segments in text.

    Args:
        text: Input text possibly containing base64 segments

    Returns:
        Text with base64 segments decoded (if valid UTF-8)

    Example:
        >>> decode_base64_segments("Run a2V5bG9nZ2Vy script")
        'Run keylogger script'
    """

    def replace_match(match: re.Match) -> str:
        encoded = match.group(1)
        decoded = _try_decode_base64(encoded)
        if decoded:
            return decoded
        return encoded  # Keep original if not valid base64 text

    return BASE64_PATTERN.sub(replace_match, text)


def normalize_text(text: str) -> str:
    """Normalize text for security classification.

    Steps: NFKC unicode normalization, homoglyph translation (Cyrillic/Greek → Latin),
    leetspeak translation, base64 segment decoding.
    """
    if not text:
        return text

    # Step 1: Unicode NFKC normalization
    # Converts compatibility characters to canonical form
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Base64 decoding FIRST (before leetspeak corrupts it)
    text = decode_base64_segments(text)

    # Step 3: Homoglyph translation
    text = translate_homoglyphs(text)

    # Step 4: Leetspeak translation (last, most aggressive)
    text = translate_leetspeak(text)

    return text


def normalize_for_classification(text: str) -> tuple[str, str]:
    """Normalize text and return both original and normalized versions.

    Useful for classification where you want to check the normalized
    version but report the original.

    Args:
        text: Input text

    Returns:
        Tuple of (original_text, normalized_text)
    """
    return (text, normalize_text(text))
