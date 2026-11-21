"""Işıl'ın dinleyeceği 20 cümleyi denetimli akıştan üretir (OA-6 kabulü).

    cd api
    uv run python -m scripts.make_tts_samples --output ../eval/tts-samples/isil

Her hız ayrı klasöre yazılır; `liste.txt` dosya ile cümleyi eşleştirir.
"""

import argparse
import sys
from pathlib import Path

from app.config import settings
from app.tts.checked import synthesize_checked
from app.tts.client import OpenAIRealtimeTTS, TTSFailed, TTSRequest
from app.tts.transcribe import OpenAITranscriber
from scripts.sheets import utf8_output
from scripts.try_tts import SENTENCES


def main() -> None:
    utf8_output()
    parser = argparse.ArgumentParser(description="Ses örnekleri üretir (gerçek API).")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--speeds", nargs="*", type=float, default=[0.8, 0.7])
    args = parser.parse_args()

    key = settings.openai_api_key
    if key is None:
        sys.exit("OPENAI_API_KEY tanımlı değil.")
    secret = key.get_secret_value().strip()
    speech = OpenAIRealtimeTTS(api_key=secret, model=settings.tts_model, voice=settings.tts_voice)
    listener = OpenAITranscriber(api_key=secret, model=settings.transcribe_model)

    for speed in args.speeds:
        folder = args.output / f"hiz-{speed}"
        folder.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []
        attempts = 0
        cost = 0
        failed = 0
        for index, sentence in enumerate(SENTENCES, start=1):
            name = f"{index:02d}.wav"
            try:
                checked = synthesize_checked(speech, listener, TTSRequest(sentence, speed=speed))
            except TTSFailed as exc:
                print(f"HATA {speed} {sentence!r}: {exc}")
                lines.append(f"{name}\tÜRETİLEMEDİ\t{sentence}")
                failed += 1
                continue
            (folder / name).write_bytes(checked.result.audio_wav)
            lines.append(f"{name}\t{sentence}")
            attempts += checked.attempts
            cost += checked.total_cost_microusd
            if checked.attempts > 1:
                print(f"YENİDEN {speed} {sentence!r}: reddedilen {checked.rejected}")
        (folder / "liste.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(
            f"hız {speed}: {len(SENTENCES) - failed}/{len(SENTENCES)} ses, "
            f"{attempts} üretim, ${cost / 1_000_000:.4f}"
        )


if __name__ == "__main__":
    main()
