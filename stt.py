"""Local speech-to-text via faster-whisper (CTranslate2 backend, auto CPU/GPU).

On Windows the CUDA math libs (cuBLAS/cuDNN) are not in the ctranslate2 wheel. If you
`pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`, we add their DLL folders to the search
path here. If the GPU still can't run, we warm up at startup and fall back to CPU cleanly.
"""
import glob
import os
import site
import sys

import ctranslate2
import numpy as np
from faster_whisper import WhisperModel


def _add_cuda_dll_dirs():
    """Let ctranslate2 find cuBLAS/cuDNN from the nvidia-*-cu12 pip packages, whether
    running from source (site-packages) or from a PyInstaller exe (_internal / _MEIPASS)."""
    if not sys.platform.startswith("win"):
        return
    roots = []
    try:
        roots += list(site.getsitepackages()) + [site.getusersitepackages()]
    except Exception:
        pass
    if getattr(sys, "frozen", False):
        roots += [getattr(sys, "_MEIPASS", ""),
                  os.path.join(os.path.dirname(sys.executable), "_internal")]
    for root in roots:
        for binp in glob.glob(os.path.join(root, "nvidia", "*", "bin")):
            try:
                os.add_dll_directory(binp)
            except OSError:
                pass


def _resolve(device, compute_type):
    if device == "auto":
        device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    return device, compute_type


class Transcriber:
    def __init__(self, model, device="auto", compute_type="auto"):
        _add_cuda_dll_dirs()
        device, compute_type = _resolve(device, compute_type)
        self.model = self._load(model, device, compute_type)

    def _load(self, model, device, compute_type):
        print(f"[stt] loading '{model}' on {device} ({compute_type}) ...")
        m = WhisperModel(model, device=device, compute_type=compute_type)
        try:
            # Warm up: this forces the CUDA libs (cuBLAS/cuDNN) to load NOW, so a missing
            # DLL fails here at startup instead of mid-dictation. Also speeds the first real run.
            list(m.transcribe(np.zeros(16000, dtype="float32"), language="en")[0])
        except Exception as e:
            if device == "cuda":
                print(f"[stt] GPU inference unavailable ({e}); falling back to CPU")
                return self._load(model, "cpu", "int8")
            raise
        print("[stt] ready")
        return m

    def transcribe(self, audio):
        # beam_size=1 (greedy) + vad_filter (skip silence) = noticeably faster, negligible
        # accuracy loss for dictation. condition_on_previous_text=False avoids drift on short clips.
        segments, _ = self.model.transcribe(
            audio, language="en", beam_size=1, vad_filter=True,
            condition_on_previous_text=False,
        )
        return " ".join(s.text.strip() for s in segments).strip()
