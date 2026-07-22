"""generate_report의 재시도/빈 응답 처리 (가짜 클라이언트 사용, 실제 API 호출 없음)."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from google.genai import errors

from core import gemini


class _FakeModels:
    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        result = self._results.pop(0)
        if isinstance(result, Exception):
            raise result
        return SimpleNamespace(text=result)


def _call(results):
    client = SimpleNamespace(models=_FakeModels(results))
    with patch("core.gemini.time.sleep"):
        text = gemini.generate_report(
            client=client, model="m", system_prompt="s",
            life_record="lr", cover_letter="cl", command="go",
        )
    return text, client.models.calls


def test_retries_transient_error_then_succeeds():
    text, calls = _call([errors.APIError(503, {}), "보고서"])
    assert text == "보고서"
    assert calls == 2


def test_non_retryable_error_raises_immediately():
    client = SimpleNamespace(models=_FakeModels([errors.APIError(400, {}), "unreachable"]))
    with patch("core.gemini.time.sleep"), pytest.raises(errors.APIError) as excinfo:
        gemini.generate_report(
            client=client, model="m", system_prompt="s",
            life_record="lr", cover_letter="cl", command="go",
        )
    assert excinfo.value.code == 400
    assert client.models.calls == 1


def test_empty_response_retries_then_raises():
    client = SimpleNamespace(models=_FakeModels(["", "", ""]))
    with patch("core.gemini.time.sleep"), pytest.raises(gemini.EmptyResponseError):
        gemini.generate_report(
            client=client, model="m", system_prompt="s",
            life_record="lr", cover_letter="cl", command="go",
        )
    assert client.models.calls == 3
