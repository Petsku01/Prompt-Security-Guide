from __future__ import annotations

from psg.llm.client import OpenAICompatibleClient
from psg.models import AppConfig, Attack, LLMResponse
from psg.orchestrator import _process_multi_turn_attack
from psg.security.classifier import ClassificationResult


class _FakeTransport:
    def __init__(self) -> None:
        self.last_headers = None
        self.last_payload = None

    def post_json(self, _url, payload, headers=None):
        self.last_payload = payload
        self.last_headers = headers
        return {"choices": [{"message": {"content": "ok"}}]}


class _Detector:
    def classify(self, prompt: str, response: str) -> ClassificationResult:
        is_harmful = "dangerous payload" in response
        return ClassificationResult(
            is_refusal=not is_harmful,
            is_harmful=is_harmful,
            attack_successful=is_harmful,
            harm_score=0.9 if is_harmful else 0.0,
            refusal_confidence=0.9 if not is_harmful else 0.0,
            harmful_labels=["malware_code"] if is_harmful else [],
            compliance_detected=is_harmful,
            has_disclaimer=False,
            raw_text_length=len(response),
        )


def _cfg() -> AppConfig:
    return AppConfig(
        model="test-model",
        catalog_path="datasets/tiny_test.json",
        allow_insecure_http=True,
        multi_turn=True,
    )


def test_attack_model_followups_field() -> None:
    attack = Attack(id="a1", prompt="start", followups=["next", "final"])
    assert attack.followups == ["next", "final"]
    assert Attack(id="a2", prompt="only once").followups == []


def test_chat_multi_turn_builds_expected_messages_payload(monkeypatch) -> None:
    transport = _FakeTransport()
    client = OpenAICompatibleClient(
        "https://api.example.test/v1", transport, api_key="secret"
    )
    messages = [
        {"role": "user", "content": "turn1"},
        {"role": "assistant", "content": "reply1"},
    ]

    monkeypatch.setattr(
        "psg.llm.client.parse_chat_completion",
        lambda _data: LLMResponse(content="ok", raw={}),
    )
    client.chat_multi_turn(model="m", messages=messages, system_prompt="system")

    assert transport.last_headers == {"Authorization": "Bearer secret"}
    assert transport.last_payload["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "turn1"},
        {"role": "assistant", "content": "reply1"},
    ]


def test_process_multi_turn_attack_stops_when_harmful_response_detected(
    monkeypatch,
) -> None:
    cfg = _cfg()
    attack = Attack(id="a1", prompt="initial prompt", followups=["followup prompt"])
    detector = _Detector()

    class _FakeClient:
        def __init__(self) -> None:
            self.calls = []

        def chat_multi_turn(self, **kwargs):
            self.calls.append(kwargs["messages"].copy())
            if len(self.calls) == 1:
                return LLMResponse(content="safe refusal", raw={})
            return LLMResponse(content="dangerous payload", raw={})

    client = _FakeClient()
    monkeypatch.setattr("psg.orchestrator.redact_text", lambda text, _mode: text)

    result = _process_multi_turn_attack(
        cfg=cfg,
        attack=attack,
        client=client,
        detector=detector,
        system_prompt=None,
    )

    assert len(client.calls) == 2
    assert [m["content"] for m in client.calls[0]] == ["initial prompt"]
    assert [m["content"] for m in client.calls[1]] == [
        "initial prompt",
        "safe refusal",
        "followup prompt",
    ]
    assert result.flagged is True
    assert result.labels == ["malware_code"]
    assert "[multi-turn 2/2]" in result.prompt


def test_app_config_multi_turn_flag() -> None:
    assert (
        AppConfig(model="m", catalog_path="datasets/tiny_test.json").multi_turn is False
    )
    assert (
        AppConfig(
            model="m", catalog_path="datasets/tiny_test.json", multi_turn=True
        ).multi_turn
        is True
    )
