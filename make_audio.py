"""Synthesize every narration segment with Kokoro-82M (voice af_heart).

Writes audio/<key>.wav and audio/durations.json. Model files come from the
kokoro-onnx release (an ONNX export of hexgrad/Kokoro-82M):
  kokoro-v1.0.onnx and voices-v1.0.bin, looked up in $KOKORO_DIR (default /opt/kokoro).
"""
import json
import os
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

from narration import SEGMENTS

ROOT = Path(__file__).parent
OUT = ROOT / "audio"
MODEL_DIR = Path(os.environ.get("KOKORO_DIR", "/opt/kokoro"))


def main():
    OUT.mkdir(exist_ok=True)
    tts = Kokoro(str(MODEL_DIR / "kokoro-v1.0.onnx"), str(MODEL_DIR / "voices-v1.0.bin"))
    durations = {}
    for key, text in SEGMENTS.items():
        samples, sr = tts.create(text, voice="af_heart", speed=1.0, lang="en-us")
        sf.write(OUT / f"{key}.wav", samples, sr)
        durations[key] = round(len(samples) / sr, 3)
        print(f"{key:14s} {durations[key]:6.2f}s")
    (OUT / "durations.json").write_text(json.dumps(durations, indent=2))
    print(f"total {sum(durations.values()) / 60:.2f} min")


if __name__ == "__main__":
    main()
