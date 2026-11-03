"""Gerçek API'ye gitmeyen sahte LLM istemcisi."""

from pydantic import BaseModel

from app.llm.client import LLMRequest, LLMResult
from app.llm.pricing import Usage


class FakeClient:
    def __init__(self, parsed: BaseModel | None, error: Exception | None = None) -> None:
        self.parsed = parsed
        self.error = error
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        if self.error:
            raise self.error
        return LLMResult(
            model=request.config.model,
            parsed=self.parsed,
            usage=Usage(input_tokens=300, output_tokens=120, cache_read_tokens=900),
            stop_reason="end_turn" if self.parsed else "max_tokens",
            latency_ms=850,
            raw_text=None if self.parsed else '{"is_correct": tr',
        )
