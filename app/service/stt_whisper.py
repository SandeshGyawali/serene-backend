from __future__ import annotations

import os
import shutil
from functools import lru_cache


@lru_cache(maxsize=4)
def _get_model(model_name: str):
    import whisper
    return whisper.load_model(model_name)


def transcribe_audio_file(audio_path: str, model_name: str = "base") -> str:
    """
    Convert a local audio file to text using OpenAI Whisper (local).

    - Input: local file path (wav, mp3, webm, etc.)
    - Return: transcription text
    - Uses ffmpeg under the hood for audio decoding/loading.
    """
    if not audio_path or not isinstance(audio_path, str):
        raise ValueError("audio_path must be a non-empty string")

    if not os.path.exists(audio_path):
        raise FileNotFoundError(audio_path)

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg not found on PATH. Install ffmpeg to enable audio decoding for Whisper."
        )

    import whisper

    # Force ffmpeg-based loading to validate decode path early.
    _ = whisper.load_audio(audio_path)

    model = _get_model(model_name)
    result = model.transcribe(audio_path, fp16=False)
    text = (result.get("text") or "").strip()

    print(text)
    return text
