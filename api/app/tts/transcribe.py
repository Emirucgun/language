"""Üretilen sesi metne çevirir: ses ile ekrandaki metnin uyumunun bağımsız denetimi.

Modelin kendi dökümüne güvenilmez; sesi ayrı bir model dinler.
"""

import httpx

from app.tts.client import TTSFailed

URL = "https://api.openai.com/v1/audio/transcriptions"
TIMEOUT_S = 60.0


class OpenAITranscriber:
    def __init__(self, *, api_key: str, model: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.Client(timeout=TIMEOUT_S)

    def transcribe(self, audio_wav: bytes) -> str:
        try:
            response = self._client.post(
                URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                data={"model": self._model},
                files={"file": ("speech.wav", audio_wav, "audio/wav")},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TTSFailed(f"{type(exc).__name__}: {exc}") from exc
        return str(response.json()["text"])
