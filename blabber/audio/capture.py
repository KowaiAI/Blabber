import queue
import threading
import sounddevice as sd
import webrtcvad

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)
CHANNELS = 1


class AudioCapture:
    def __init__(self, on_speech_chunk, on_silence):
        self._on_speech_chunk = on_speech_chunk
        self._on_silence = on_silence
        self._queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None
        self._vad = webrtcvad.Vad(2)
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=FRAME_SIZE,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self) -> None:
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        if self._thread:
            self._queue.put(None)
            self._thread.join(timeout=2)
            self._thread = None

    def _audio_callback(self, indata, frames, time, status):
        if self._running:
            self._queue.put(bytes(indata))

    def _process_loop(self) -> None:
        silence_count = 0
        speech_buffer = []
        silence_threshold = int(1000 / FRAME_DURATION_MS)

        while self._running:
            try:
                frame = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if frame is None:
                break

            try:
                is_speech = self._vad.is_speech(frame, SAMPLE_RATE)
            except Exception:
                is_speech = False

            if is_speech:
                silence_count = 0
                speech_buffer.append(frame)
            else:
                if speech_buffer:
                    silence_count += 1
                    speech_buffer.append(frame)
                    if silence_count >= silence_threshold:
                        audio = b"".join(speech_buffer)
                        self._on_speech_chunk(audio)
                        speech_buffer = []
                        silence_count = 0
                        self._on_silence()
