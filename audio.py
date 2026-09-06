"""Mic capture -> a single float32 numpy array at 16 kHz mono (what Whisper wants)."""
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._frames = []
        self._stream = None

    def start(self):
        self._frames = []
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._cb,
        )
        self._stream.start()

    def _cb(self, indata, frames, time_info, status):
        self._frames.append(indata.copy())

    def stop(self):
        """Stop capture and return the recorded audio (1-D float32, may be empty)."""
        if self._stream is None:
            return np.zeros(0, dtype="float32")
        self._stream.stop()
        self._stream.close()
        self._stream = None
        if not self._frames:
            return np.zeros(0, dtype="float32")
        return np.concatenate(self._frames, axis=0).flatten()
