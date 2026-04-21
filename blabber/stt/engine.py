import threading
import numpy as np
from faster_whisper import WhisperModel

MODEL_SIZES = {
    "small": "small",
    "medium": "medium",
    "large": "large-v3",
}

SAMPLE_RATE = 16000


class STTEngine:
    def __init__(self, model_size: str = "small"):
        self._model_size = MODEL_SIZES.get(model_size, "small")
        self._model: WhisperModel | None = None
        self._lock = threading.Lock()

    def load(self) -> None:
        with self._lock:
            if self._model is None:
                self._model = WhisperModel(
                    self._model_size,
                    device="cpu",
                    compute_type="int8",
                )

    def unload(self) -> None:
        with self._lock:
            self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def transcribe(self, audio_bytes: bytes) -> str:
        if not audio_bytes:
            return ""
        with self._lock:
            model = self._model
            if model is None:
                return ""

        audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32)
        audio_array /= 32768.0

        segments, _ = model.transcribe(
            audio_array,
            language=None,
            beam_size=5,
            # AudioCapture already performs VAD segmentation. Running Whisper VAD
            # again can over-filter short utterances and return empty text.
            vad_filter=False,
        )
        return "".join(seg.text for seg in segments).strip()
