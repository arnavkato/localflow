"""LocalFlow — hold a hotkey, speak, get cleaned text pasted at your cursor.

Pipeline on stop: Whisper transcribe -> Ollama cleanup -> paste at cursor.
"""
import threading

import httpx

import config as config_mod
from audio import Recorder, SAMPLE_RATE
from cleanup import Cleaner
from hotkey import HotkeyHandler
from inject import paste
from stt import Transcriber
from tray import Status

MIN_SAMPLES = int(SAMPLE_RATE * 0.3)  # ignore recordings shorter than 0.3s


def warn_if_ollama_down(o):
    if not o["enabled"]:
        return
    try:
        httpx.get(o["url"].rstrip("/") + "/api/tags", timeout=3).raise_for_status()
    except Exception as e:
        print(f"[warn] Ollama not reachable at {o['url']}: {e}")
        print("[warn] start it (run `ollama serve` or launch the Ollama app), "
              "or set ollama.enabled: false in config.yaml to paste raw transcripts")


def main():
    cfg = config_mod.load()
    status = Status(cfg.get("tray", True))
    warn_if_ollama_down(cfg["ollama"])

    recorder = Recorder()
    w = cfg["whisper"]
    transcriber = Transcriber(w["model"], w.get("device", "auto"), w.get("compute_type", "auto"))
    o = cfg["ollama"]
    cleaner = (
        Cleaner(o["url"], o["model"], o["system_prompt"], o.get("keep_alive", "60s"))
        if o["enabled"] else None
    )

    def on_start():
        status.set("recording")
        recorder.start()

    def process(audio):
        try:
            if audio.size < MIN_SAMPLES:
                print("[skip] recording too short / silent")
                return
            status.set("processing")
            text = transcriber.transcribe(audio)
            if not text:
                print("[skip] empty transcript")
                return
            if cleaner is not None:
                try:
                    text = cleaner.clean(text) or text
                except Exception as e:
                    print(f"[warn] cleanup failed, pasting raw transcript: {e}")
            print(f"[paste] {text!r}")
            paste(text)
        except Exception as e:
            print(f"[error] pipeline failed: {e}")
        finally:
            status.set("idle")

    def on_stop():
        audio = recorder.stop()
        threading.Thread(target=process, args=(audio,), daemon=True).start()

    hk = HotkeyHandler(cfg["hotkey"], cfg["hotkey_mode"], on_start, on_stop)
    hk.start()
    verb = "press to start/stop" if cfg["hotkey_mode"] == "toggle" else "hold to talk"
    print(f"[ready] {cfg['hotkey']} ({cfg['hotkey_mode']}) — {verb}. Ctrl+C to quit.")
    status.set("idle")
    try:
        status.run()  # blocks: tray loop, or wait-forever if tray disabled
    except KeyboardInterrupt:
        print("\n[bye]")


if __name__ == "__main__":
    main()
