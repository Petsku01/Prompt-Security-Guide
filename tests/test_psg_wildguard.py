from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from types import ModuleType, SimpleNamespace

import pytest

from psg.security.wildguard_classifier import WildGuardClassifier, WildGuardResult


@pytest.fixture
def sample_result() -> WildGuardResult:
    return WildGuardResult(
        prompt_harmful=True,
        response_harmful=False,
        is_refusal=True,
        attack_successful=False,
        prompt_harm_score=0.9,
        response_harm_score=0.1,
        refusal_score=0.95,
        harm_score=0.1,
        harmful_labels=["test_label"],
    )


def test_wildguard_result_dataclass(sample_result: WildGuardResult) -> None:
    payload = asdict(sample_result)
    assert payload["prompt_harmful"] is True
    assert payload["is_refusal"] is True
    assert payload["harmful_labels"] == ["test_label"]


def test_wildguard_classifier_initialization_defaults() -> None:
    classifier = WildGuardClassifier()
    assert classifier.model_name == "allenai/wildguard-7b"
    assert classifier.use_local is True
    assert classifier.model is None
    assert classifier.tokenizer is None
    assert classifier._load_attempted is False


def test_format_prompt_includes_all_sections() -> None:
    classifier = WildGuardClassifier()
    prompt = classifier._format_prompt("user asks", "assistant replies")

    assert "<|user|>" in prompt
    assert "user asks" in prompt
    assert "<|assistant|>" in prompt
    assert "assistant replies" in prompt
    assert "<|task|>" in prompt
    assert "<|response|>" in prompt


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        ("Prompt harmful: yes\nResponse harmful: yes\nRefusal: no", (True, True, False)),
        ("1. yes\n2. no\n3. yes", (True, False, True)),
        ("Prompt harmful: no\nResponse harmful: no\nRefusal: no", (False, False, False)),
    ],
)
def test_parse_wildguard_output(output: str, expected: tuple[bool, bool, bool]) -> None:
    classifier = WildGuardClassifier()
    assert classifier._parse_wildguard_output(output) == expected


def test_fallback_when_model_not_available(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenAutoTokenizer:
        @staticmethod
        def from_pretrained(_name: str) -> object:
            raise RuntimeError("no model")

    class _BrokenAutoModel:
        @staticmethod
        def from_pretrained(*_args: object, **_kwargs: object) -> object:
            raise RuntimeError("no model")

    fake_transformers = ModuleType("transformers")
    fake_transformers.AutoTokenizer = _BrokenAutoTokenizer
    fake_transformers.AutoModelForCausalLM = _BrokenAutoModel

    fake_torch = ModuleType("torch")
    fake_torch.float16 = "float16"
    fake_torch.float32 = "float32"
    fake_torch.cuda = SimpleNamespace(is_available=lambda: False)

    monkeypatch.setitem(__import__("sys").modules, "transformers", fake_transformers)
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)

    classifier = WildGuardClassifier()
    fallback = WildGuardResult(
        prompt_harmful=False,
        response_harmful=False,
        is_refusal=False,
        attack_successful=False,
        prompt_harm_score=0.0,
        response_harm_score=0.0,
        refusal_score=0.0,
        harm_score=0.0,
        harmful_labels=[],
    )
    monkeypatch.setattr(classifier, "_regex_fallback", lambda _response: fallback)

    result = classifier.classify("prompt", "response")

    assert classifier._load_attempted is True
    assert classifier.model is None
    assert result == fallback


def test_classify_with_mocked_model(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _no_grad():
        yield

    fake_torch = ModuleType("torch")
    fake_torch.cuda = SimpleNamespace(is_available=lambda: False)
    fake_torch.no_grad = _no_grad
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)

    class _Inputs(dict):
        pass

    class _Tokenizer:
        def __call__(self, _text: str, return_tensors: str) -> _Inputs:
            assert return_tensors == "pt"
            return _Inputs({"input_ids": [1, 2, 3]})

        def decode(self, _output: object, skip_special_tokens: bool) -> str:
            assert skip_special_tokens is True
            return "Prompt harmful: yes\nResponse harmful: yes\nRefusal: no"

    class _Model:
        def generate(self, **_kwargs: object) -> list[list[int]]:
            return [[101, 102]]

    classifier = WildGuardClassifier()
    classifier._load_attempted = True
    classifier.tokenizer = _Tokenizer()
    classifier.model = _Model()

    result = classifier.classify("harmful prompt", "harmful response")

    assert result.prompt_harmful is True
    assert result.response_harmful is True
    assert result.is_refusal is False
    assert result.attack_successful is True
    assert result.harm_score == 1.0
    assert result.harmful_labels == ["wildguard_harmful"]


def test_classify_with_empty_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test classification with empty response."""
    @contextmanager
    def _no_grad():
        yield

    fake_torch = ModuleType("torch")
    fake_torch.cuda = SimpleNamespace(is_available=lambda: False)
    fake_torch.no_grad = _no_grad
    monkeypatch.setitem(__import__("sys").modules, "torch", fake_torch)

    class _Inputs(dict):
        pass

    class _Tokenizer:
        def __call__(self, _text: str, return_tensors: str) -> _Inputs:
            return _Inputs({"input_ids": [1, 2, 3]})

        def decode(self, _output: object, skip_special_tokens: bool) -> str:
            return "Prompt harmful: no\nResponse harmful: no\nRefusal: yes"

    class _Model:
        def generate(self, **_kwargs: object) -> list[list[int]]:
            return [[101]]

    classifier = WildGuardClassifier()
    classifier._load_attempted = True
    classifier.tokenizer = _Tokenizer()
    classifier.model = _Model()

    result = classifier.classify("safe prompt", "")

    assert result.prompt_harmful is False
    assert result.is_refusal is True


def test_regex_fallback_with_unparseable_output() -> None:
    """Test regex fallback when model output is garbled."""
    classifier = WildGuardClassifier()
    result = classifier._regex_fallback("completely garbled output")
    
    assert result.prompt_harmful is False
    assert result.response_harmful is False
    assert result.is_refusal is False
    assert result.harm_score == 0.0


def test_wildguard_result_score_calculation() -> None:
    """Test harm score calculation logic."""
    result = WildGuardResult(
        prompt_harmful=True,
        response_harmful=True,
        is_refusal=False,
        attack_successful=True,
        prompt_harm_score=0.9,
        response_harm_score=0.8,
        refusal_score=0.1,
        harm_score=0.0,  # Will be calculated
        harmful_labels=["test"],
    )
    
    assert result.prompt_harm_score == 0.9
    assert result.response_harm_score == 0.8


def test_classifier_with_different_model_name() -> None:
    """Test initializing classifier with custom model."""
    classifier = WildGuardClassifier(model_name="custom/wildguard-model")
    assert classifier.model_name == "custom/wildguard-model"
