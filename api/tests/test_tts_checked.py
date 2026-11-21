"""Denetimli ses üretimi: gerçek denemede görülen örneklerle."""

import pytest

from app.tts.checked import MAX_ATTEMPTS, speech_ok, synthesize_checked
from app.tts.client import TTSFailed, TTSRequest, TTSResult
from app.tts.pricing import Usage


@pytest.mark.parametrize(
    ("text", "transcript", "heard"),
    [
        ("My name is Elif.", "My name is Elif.", "My name is Elif."),
        # Doğru ses, dinleyen farklı yazıyor:
        ("I get up at seven thirty.", "I get up at seven thirty.", "I get up at 7:30."),
        ("We're going home.", "We're going home.", "We are going home."),
        ("I didn't go.", "I didn't go.", "I did not go."),
        ("My name is Elif.", "My name is Elif.", "My name is Alif."),
        (
            "It's twenty-five degrees today.",
            "It's twenty-five degrees today.",
            "It's 25 degrees today.",
        ),
    ],
)
def test_good_speech_passes(text: str, transcript: str, heard: str) -> None:
    assert speech_ok(text, transcript, heard)


@pytest.mark.parametrize(
    ("text", "transcript", "heard"),
    [
        # Modelin kendi cümlesi:
        ("What is your name?", "Hi there! I'm ChatGPT, how can I help?", "Hi there, I'm ChatGPT."),
        # Başına eklenen cümle:
        (
            "She doesn't like coffee.",
            "Alright, I'll say that slowly and clearly. She doesn't like coffee.",
            "All right, I'll say that slowly and clearly. She doesn't like coffee.",
        ),
        # Model doğru okuduğunu söylüyor, ses başka:
        ("She doesn't like coffee.", "She doesn't like coffee.", "He plays football every day."),
        ("Yes, I do.", "Yes, I do.", "Yes, I do. Thank you very much for asking."),
        ("Yes, I do.", None, "Yes, I do."),
    ],
)
def test_wrong_speech_is_rejected(text: str, transcript: str | None, heard: str) -> None:
    assert not speech_ok(text, transcript, heard)


class Speech:
    def __init__(self, transcripts: list[str]) -> None:
        self.transcripts = iter(transcripts)

    def synthesize(self, request: TTSRequest) -> TTSResult:
        return TTSResult(
            model="m",
            audio_wav=next(self.transcripts).encode(),
            duration_ms=1000,
            transcript=None,
            usage=Usage(),
            cost_microusd=100,
            latency_ms=1,
        )


class EchoSpeech(Speech):
    def synthesize(self, request: TTSRequest) -> TTSResult:
        result = super().synthesize(request)
        text = result.audio_wav.decode()
        return TTSResult(
            result.model, result.audio_wav, 1000, text, result.usage, result.cost_microusd, 1
        )


class Listener:
    def transcribe(self, audio_wav: bytes) -> str:
        return audio_wav.decode()


def test_bad_speech_is_regenerated_and_every_attempt_is_paid() -> None:
    speech = EchoSpeech(["Hi there, how can I help you today?", "What is your name?"])
    checked = synthesize_checked(speech, Listener(), TTSRequest("What is your name?"))
    assert checked.attempts == 2
    assert checked.total_cost_microusd == 200
    assert checked.heard == "What is your name?"
    assert checked.rejected == ("Hi there, how can I help you today?",)


def test_gives_up_after_the_limit() -> None:
    speech = EchoSpeech(["Hello there my friend how are you"] * MAX_ATTEMPTS)
    with pytest.raises(TTSFailed):
        synthesize_checked(speech, Listener(), TTSRequest("What is your name?"))
