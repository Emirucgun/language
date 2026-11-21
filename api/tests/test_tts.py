"""Ses istemcisi: Realtime olay akışı sahte, gerçek ağ yok."""

import base64
import io
import json
import wave
from typing import Any

import httpx
import pytest

from app.tts.client import (
    OpenAIRealtimeTTS,
    TTSFailed,
    TTSRequest,
    audio_matches,
    to_wav,
)
from app.tts.pricing import Usage, cost_microusd
from app.tts.transcribe import OpenAITranscriber

MODEL = "gpt-realtime-2.1-mini"
PCM = b"\x01\x00" * 24_000  # 1 saniye


def _done(status: str = "completed", transcript: str = "My name is Elif.") -> dict[str, Any]:
    return {
        "type": "response.done",
        "response": {
            "status": status,
            "output": [{"content": [{"transcript": transcript}]}],
            "usage": {
                "input_token_details": {"text_tokens": 100},
                "output_token_details": {"text_tokens": 50, "audio_tokens": 1000},
            },
        },
    }


def _delta(pcm: bytes) -> dict[str, Any]:
    return {"type": "response.output_audio.delta", "delta": base64.b64encode(pcm).decode()}


class FakeSocket:
    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = iter(events)
        self.sent: list[dict[str, Any]] = []

    def __enter__(self) -> FakeSocket:
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def send(self, message: str) -> None:
        self.sent.append(json.loads(message))

    def recv(self, timeout: float) -> str:
        event = next(self.events, None)
        if event is None:
            raise TimeoutError
        return json.dumps(event)


def _client(socket: FakeSocket) -> OpenAIRealtimeTTS:
    return OpenAIRealtimeTTS(
        api_key="test", model=MODEL, voice="marin", connector=lambda *a, **k: socket
    )


def test_audio_chunks_are_joined_into_a_wav() -> None:
    half = len(PCM) // 2
    socket = FakeSocket(
        [{"type": "session.created"}, _delta(PCM[:half]), _delta(PCM[half:]), _done()]
    )
    result = _client(socket).synthesize(TTSRequest("My name is Elif."))

    assert result.duration_ms == 1000
    assert result.transcript == "My name is Elif."
    with wave.open(io.BytesIO(result.audio_wav)) as file:
        assert (file.getframerate(), file.getnchannels()) == (24_000, 1)
        assert file.readframes(file.getnframes()) == PCM


def test_cost_comes_from_reported_usage() -> None:
    result = _client(FakeSocket([_delta(PCM), _done()])).synthesize(TTSRequest("x"))
    assert result.usage == Usage(100, 50, 1000)
    assert result.cost_microusd == round(100 * 0.6 + 50 * 2.4 + 1000 * 20)
    assert cost_microusd("unknown-model", result.usage) is None


def test_request_reads_the_text_out_of_band() -> None:
    socket = FakeSocket([_delta(PCM), _done()])
    _client(socket).synthesize(TTSRequest("Open the door.", style="Speak slowly.", speed=0.8))

    session, response = socket.sent
    assert session["session"]["audio"]["output"]["voice"] == "marin"
    assert session["session"]["audio"]["output"]["speed"] == 0.8
    assert response["response"]["conversation"] == "none"  # sohbet geçmişi yok
    assert response["response"]["input"] == []
    assert response["response"]["instructions"].endswith("Open the door.")
    assert "Speak slowly." in response["response"]["instructions"]


def test_speed_is_left_out_by_default() -> None:
    socket = FakeSocket([_delta(PCM), _done()])
    _client(socket).synthesize(TTSRequest("x"))
    assert "speed" not in socket.sent[0]["session"]["audio"]["output"]


@pytest.mark.parametrize(
    "events",
    [
        [{"type": "error", "error": {"message": "rate limit"}}],
        [_delta(PCM), _done(status="failed")],
        [_done()],  # ses yok
        [_delta(PCM)],  # bitiş gelmedi: zaman aşımı
    ],
)
def test_failures_raise_tts_failed(events: list[dict[str, Any]]) -> None:
    with pytest.raises(TTSFailed):
        _client(FakeSocket(events)).synthesize(TTSRequest("x"))


def test_connection_error_raises_tts_failed() -> None:
    def refuse(*_: object, **__: object) -> None:
        raise OSError("bağlantı yok")

    client = OpenAIRealtimeTTS(api_key="t", model=MODEL, voice="marin", connector=refuse)
    with pytest.raises(TTSFailed):
        client.synthesize(TTSRequest("x"))


@pytest.mark.parametrize(
    ("heard", "same"),
    [
        ("my name is elif", True),
        ("My name is Elif.", True),
        ("My name's Elif.", False),
        ("Hello, my name is Elif.", False),
        (None, False),
    ],
)
def test_audio_match_ignores_only_punctuation_and_case(heard: str | None, same: bool) -> None:
    assert audio_matches("My name is Elif.", heard) is same


def test_wav_header_is_valid_for_transcription() -> None:
    with wave.open(io.BytesIO(to_wav(PCM))) as file:
        assert file.getsampwidth() == 2


def test_transcriber_sends_the_file_and_reads_the_text() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"text": "My name is Elif."})

    transcriber = OpenAITranscriber(
        api_key="t",
        model="gpt-transcribe",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert transcriber.transcribe(to_wav(PCM)) == "My name is Elif."
    assert b"gpt-transcribe" in seen[0].read()


def test_transcriber_error_raises_tts_failed() -> None:
    transcriber = OpenAITranscriber(
        api_key="t",
        model="gpt-transcribe",
        client=httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(500))),
    )
    with pytest.raises(TTSFailed):
        transcriber.transcribe(to_wav(PCM))
