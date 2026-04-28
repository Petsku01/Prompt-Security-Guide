"""Tests for text normalization (obfuscation detection)."""

from psg.security.normalize import (
    normalize_text,
    translate_leetspeak,
    translate_homoglyphs,
    decode_base64_segments,
    normalize_for_classification,
)


class TestLeetspeakTranslation:
    """Test leetspeak → ASCII conversion."""

    def test_basic_leetspeak(self):
        assert translate_leetspeak("k3ylogg3r") == "keylogger"

    def test_malware_variants(self):
        assert translate_leetspeak("m4lw4r3") == "malware"
        assert translate_leetspeak("p4ssw0rd") == "password"
        assert translate_leetspeak("h4ck3r") == "hacker"

    def test_mixed_case(self):
        # Leetspeak map is lowercase only, so 3→e not 3→E
        assert translate_leetspeak("K3YLOGG3R") == "KeYLOGGeR"

    def test_numbers_at_symbol(self):
        assert translate_leetspeak("r00t@dm1n") == "rootadmin"

    def test_preserves_normal_text(self):
        assert translate_leetspeak("hello world") == "hello world"
        assert (
            translate_leetspeak("Python 3.12") == "Python e.iz"
        )  # Numbers translate (2→z)

    def test_special_chars(self):
        assert translate_leetspeak("pa$$word") == "password"
        assert translate_leetspeak("v!ru$") == "virus"


class TestHomoglyphTranslation:
    """Test Unicode homoglyph → ASCII conversion."""

    def test_cyrillic_e(self):
        # Cyrillic е looks like Latin e
        assert translate_homoglyphs("kеyloggеr") == "keylogger"

    def test_cyrillic_a_o(self):
        # Cyrillic а and о
        assert translate_homoglyphs("mаlwаrе") == "malware"

    def test_cyrillic_uppercase(self):
        assert translate_homoglyphs("ВАNК") == "BANK"  # В=B, А=A, К=K

    def test_greek_letters(self):
        assert translate_homoglyphs("pαssword") == "password"  # Greek alpha

    def test_preserves_normal_text(self):
        assert translate_homoglyphs("hello world") == "hello world"
        assert translate_homoglyphs("keylogger") == "keylogger"

    def test_mixed_scripts(self):
        # Mix of Cyrillic and Latin
        text = "kеylоggеr"  # е and о are Cyrillic
        assert translate_homoglyphs(text) == "keylogger"


class TestBase64Decoding:
    """Test base64 segment detection and decoding."""

    def test_decode_keylogger(self):
        # "keylogger" in base64
        assert decode_base64_segments("a2V5bG9nZ2Vy") == "keylogger"

    def test_decode_malware(self):
        # "malware" in base64
        assert decode_base64_segments("bWFsd2FyZQ==") == "malware"

    def test_embedded_in_text(self):
        text = "Run the a2V5bG9nZ2Vy script now"
        assert decode_base64_segments(text) == "Run the keylogger script now"

    def test_preserves_non_base64(self):
        # Too short or invalid
        assert decode_base64_segments("hello") == "hello"
        assert decode_base64_segments("abc123") == "abc123"

    def test_preserves_binary_base64(self):
        # Base64 that decodes to binary (not UTF-8) should be preserved
        # This is random bytes that won't decode to valid UTF-8
        text = "////AAAA////BBBB"
        result = decode_base64_segments(text)
        # Should preserve original if it decodes to binary
        assert "////" in result or "AAAA" in result

    def test_multiple_segments(self):
        # Multiple base64 segments
        text = "First a2V5bG9nZ2Vy then bWFsd2FyZQ=="
        result = decode_base64_segments(text)
        assert "keylogger" in result
        assert "malware" in result


class TestNormalizeText:
    """Test full normalization pipeline."""

    def test_leetspeak_normalization(self):
        assert normalize_text("k3ylogg3r") == "keylogger"
        assert normalize_text("m4lw4r3") == "malware"

    def test_homoglyph_normalization(self):
        assert normalize_text("kеyloggеr") == "keylogger"  # Cyrillic е

    def test_base64_normalization(self):
        assert normalize_text("a2V5bG9nZ2Vy") == "keylogger"

    def test_combined_obfuscation(self):
        # Leetspeak + homoglyphs
        text = "k3ylоgg3r"  # 3→e, о is Cyrillic
        result = normalize_text(text)
        assert result == "keylogger"

    def test_preserves_normal_text(self):
        normal = "This is a normal security discussion about firewalls."
        # Should be mostly unchanged (numbers might translate)
        result = normalize_text(normal)
        assert "security" in result
        assert "firewalls" in result

    def test_empty_string(self):
        assert normalize_text("") == ""

    def test_none_handling(self):
        # Should handle empty gracefully
        assert normalize_text("") == ""

    def test_unicode_normalization(self):
        # NFKC should normalize things like ﬁ → fi
        assert "fi" in normalize_text("ﬁle")  # ﬁ ligature

    def test_real_world_evasion(self):
        """Test realistic evasion attempts."""
        # Someone trying to get keylogger code
        assert "keylogger" in normalize_text("write a k3yl0gg3r")
        assert "keylogger" in normalize_text("create kеyloggеr")  # Cyrillic
        assert "keylogger" in normalize_text("build a2V5bG9nZ2Vy")


class TestNormalizeForClassification:
    """Test the tuple-returning helper."""

    def test_returns_both(self):
        original = "k3ylogg3r"
        orig, norm = normalize_for_classification(original)
        assert orig == "k3ylogg3r"
        assert norm == "keylogger"

    def test_normal_text(self):
        text = "hello world"
        orig, norm = normalize_for_classification(text)
        assert orig == text
        assert norm == text


class TestEdgeCases:
    """Test edge cases and potential issues."""

    def test_long_text(self):
        """Should handle long text without issues."""
        long_text = "normal text " * 1000
        result = normalize_text(long_text)
        assert len(result) > 0

    def test_only_numbers(self):
        """Numbers alone shouldn't cause issues."""
        result = normalize_text("12345")
        assert result == "izeas"  # All translate (2→z)

    def test_special_characters_preserved(self):
        """Special chars that aren't in maps should be preserved."""
        result = normalize_text("hello@world.com")
        assert "world" in result
        assert ".com" in result

    def test_newlines_preserved(self):
        """Whitespace should be preserved."""
        text = "line1\nline2\ttab"
        result = normalize_text(text)
        assert "\n" in result
        assert "\t" in result

    def test_url_handling(self):
        """URLs should be mostly preserved."""
        url = "https://example.com/path"
        result = normalize_text(url)
        assert "example" in result
        assert "path" in result
