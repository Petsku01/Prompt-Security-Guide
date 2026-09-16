"""Audit follow-up 2026-09-16: judge_key_binding origin/key policy matrix.

The P0 fix module had ~36% coverage with the actual origin policy (the
lines that decide which credential crosses which boundary) completely
unlocked. These tests lock the full matrix.
"""

import pytest

from psg.security.judge_key_binding import (
    _DEFAULT_PORTS,
    JudgeKeyBindingError,
    _origin,
    resolve_judge_api_key,
)


def test_default_ports_defined_once_at_module_level():
    # regression lock: _DEFAULT_PORTS was accidentally defined twice
    import psg.security.judge_key_binding as jkb

    assert jkb._DEFAULT_PORTS == {"http": 80, "https": 443}
    assert _DEFAULT_PORTS is jkb._DEFAULT_PORTS


class TestOrigin:
    def test_explicit_ports(self):
        assert _origin("http://h:8080/v1") == ("http", "h", 8080)

    def test_default_ports_derived(self):
        assert _origin("https://h/v1") == ("https", "h", 443)
        assert _origin("http://h/v1") == ("http", "h", 80)

    def test_host_lowercased(self):
        assert _origin("https://Example.COM/v1") == ("https", "example.com", 443)

    def test_missing_scheme_raises(self):
        with pytest.raises(JudgeKeyBindingError, match="missing scheme"):
            _origin("example.com/v1")

    def test_missing_host_raises(self):
        with pytest.raises(JudgeKeyBindingError, match="missing scheme or host"):
            _origin("https:///v1")

    def test_invalid_port_raises(self):
        with pytest.raises(JudgeKeyBindingError, match="unparseable"):
            _origin("https://h:notaport/")

    def test_trailing_dot_host_is_kept_verbatim(self):
        # documented behavior check: FQDN trailing dot is NOT stripped by
        # _origin — document that as distinct-origin behavior (conservative)
        scheme, host, port = _origin("https://api.example.com./v1")
        assert host == "api.example.com."


class TestResolveMatrix:
    def test_explicit_judge_key_wins(self):
        assert (
            resolve_judge_api_key(
                api_key="sk-model",
                judge_api_key="sk-judge",
                base_url="https://model.test/v1",
                judge_url="https://elsewhere.test/v1",
            )
            == "sk-judge"
        )

    def test_no_model_key_no_leak(self):
        assert (
            resolve_judge_api_key(
                api_key=None,
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url="https://elsewhere.test/v1",
            )
            is None
        )

    def test_same_endpoint_sends_model_key(self):
        assert (
            resolve_judge_api_key(
                api_key="sk-model",
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url=None,
            )
            == "sk-model"
        )

    def test_same_origin_sends_model_key(self):
        assert (
            resolve_judge_api_key(
                api_key="sk-model",
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url="https://model.test/v1/judge",
            )
            == "sk-model"
        )

    def test_same_origin_different_explicit_port_is_different_origin(self):
        with pytest.raises(JudgeKeyBindingError, match="refusing"):
            resolve_judge_api_key(
                api_key="sk-model",
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url="https://model.test:8443/v1",
            )

    def test_different_origin_raises(self):
        with pytest.raises(JudgeKeyBindingError, match="refusing to send"):
            resolve_judge_api_key(
                api_key="sk-model",
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url="https://judge.test/v1",
            )

    def test_scheme_change_is_different_origin(self):
        with pytest.raises(JudgeKeyBindingError, match="refusing"):
            resolve_judge_api_key(
                api_key="sk-model",
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url="http://model.test/v1",
            )

    def test_error_message_contains_no_key_material(self):
        with pytest.raises(JudgeKeyBindingError) as ei:
            resolve_judge_api_key(
                api_key="sk-SECRET-VALUE",
                judge_api_key=None,
                base_url="https://model.test/v1",
                judge_url="https://judge.test/v1",
            )
        msg = str(ei.value)
        assert "sk-SECRET-VALUE" not in msg
        assert "model.test" in msg and "judge.test" in msg