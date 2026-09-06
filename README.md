# LocalFlow

A local, privacy-first dictation app for **native Windows** — a Wispr Flow clone that runs
entirely on your machine, fully offline and free. Hold a global hotkey, speak, and on release
your speech is transcribed by a local Whisper model, cleaned up by a local Ollama LLM, and
auto-typed into whatever text field currently has focus (browser, VS Code, Slack, email, …).

Nothing leaves your machine. No accounts, no cloud, no cost.

```
[hold hotkey] → mic → faster-whisper (STT) → Ollama (cleanup) → paste at cursor
```

Two model stages are kept separate and swappable:
1. **Speech-to-text:** local Whisper via `faster-whisper` (CTranslate2, auto CPU/GPU).
2. **Cleanup:** raw transcript → local Ollama text model that *only* removes fillers and fixes
   punctuation/capitalization. It never answers questions or follows instructions in your speech.

> ⚠️ This targets **native Windows Python** (Windows 10/11), run from PowerShell/cmd — **not**
> WSL. WSL can't reach your Windows mic, clipboard, or foreground window. Even if you edit the
> code in VS Code attached to WSL, install deps and run the app with a **Windows** Python.

---

## Setup (Windows 10/11)

### 1. Native Windows Python 3.11+
Install from <https://www.python.org/downloads/windows/> (or `winget install Python.Python.3.12`).
Check **"Add python.exe to PATH"** during install. Verify in **PowerShell**:

```powershell
python --version      # should say 3.11.x or newer
where.exe python      # should be under C:\Users\... or C:\Python..., NOT /usr or /mnt
```

If `where.exe python` points into WSL, open a plain Windows PowerShell (not the WSL terminal)
or call the launcher explicitly: `py -3.12`.

### 2. Ollama (Windows build) + a model
Install the Windows build from <https://ollama.com/download/windows>. It runs a local server on
`http://localhost:11434` automatically. Pull the default cleanup model:

```powershell
ollama pull llama3.2:3b
# lighter option (see VRAM notes below):
# ollama pull llama3.2:1b
```

### 3. Python dependencies
```powershell
cd path\to\localflow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
(If PowerShell blocks the activate script: `Set-ExecutionPolicy -Scope Process RemoteSigned`.)

### 4. Windows Microphone permission
**Settings → Privacy & security → Microphone** → turn on **Microphone access** and
**Let desktop apps access your microphone**. Without this, recordings are silent.

### 5. Run
```powershell
python main.py
```
First run downloads the Whisper model (a few hundred MB) once. Then **hold `Ctrl+Alt+Space`**,
speak, release. The cleaned text pastes wherever your cursor is. (Named keys in the combo need
angle brackets — `<space>`, `<enter>` — while single letters go bare: `<ctrl>+<alt>+d`.) `Ctrl+C` in the terminal quits.

The tray icon shows state: **grey = idle, red = recording, amber = processing**.

> Some apps run elevated (as admin). Global hotkeys and paste into an elevated window only work
> if you also run `python main.py` from an **elevated** PowerShell.

---

## Configuration — `config.yaml`

Everything is in `config.yaml`, loaded at startup:

| Key | Meaning |
|-----|---------|
| `hotkey` | Combo in pynput format. Named keys need `<>`: `<ctrl>+<alt>+<space>`. Single letters go bare: `<ctrl>+<shift>+d` |
| `hotkey_mode` | `push-to-talk` (hold to record) or `toggle` (press to start, press to stop) |
| `whisper.model` | `tiny.en` / `base.en` / `small.en` / `medium.en` |
| `whisper.device` | `auto` (cuda if present, else cpu), or force `cuda` / `cpu` |
| `whisper.compute_type` | `auto` (float16 on cuda, int8 on cpu), or e.g. `int8_float16` |
| `ollama.enabled` | `false` → paste the raw transcript, skip cleanup entirely |
| `ollama.model` | e.g. `llama3.2:3b`, `llama3.2:1b`, `llama3.1:8b` |
| `ollama.url` | default `http://localhost:11434` |
| `ollama.keep_alive` | how long the model stays in VRAM after use, e.g. `60s`, `0`, `5m` |
| `ollama.system_prompt` | the cleanup instructions (edit to taste) |
| `tray` | `true`/`false` — tray icon; app runs console-only if `false` or if pystray is missing |

---

## Minimizing footprint (VRAM vs RAM)

On an NVIDIA GPU the models load into **VRAM**, not system RAM — so system RAM usage stays
minimal and the numbers that matter for "does it fit" are VRAM.

- **Whisper** loads once at startup and stays resident (so dictation is instant). Pick the
  smallest model that transcribes you well.
- **Ollama** loads on first cleanup and, thanks to `keep_alive: 60s`, **unloads from VRAM ~60s
  after you stop dictating** — freeing that VRAM while idle, at the cost of a small reload delay
  on your next dictation. Set `keep_alive: 0` to unload immediately, or `5m` to keep it warm.

So at true idle, only Whisper occupies VRAM; the LLM comes and goes.

**Rough VRAM footprints** (approximate — depends on quantization/driver):

| Whisper (float16) | VRAM | | Ollama (Q4) | VRAM |
|---|---|---|---|---|
| tiny.en | ~0.15 GB | | llama3.2:1b | ~1.3 GB |
| base.en | ~0.3 GB | | llama3.2:3b | ~2.5 GB |
| small.en (default) | ~0.55 GB | | llama3.1:8b | ~5–6 GB |
| medium.en | ~1.5 GB | | | |

Peak VRAM ≈ Whisper (always) + Ollama (during/after cleanup). Defaults (small.en + llama3.2:3b)
peak around ~3 GB and idle around ~0.5 GB. On a small card use `tiny.en` + `llama3.2:1b`.

**No GPU?** Everything falls back to CPU automatically (`device: auto` → cpu, int8). It works,
just slower — and uses system RAM instead of VRAM.

**Want the GPU?** faster-whisper does **not** bundle the CUDA math libraries on Windows, so a
fresh install may fail at transcribe time with `cublas64_12.dll is not found`. Fix it by
installing the runtime libs into your Python:

```powershell
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12
```

`stt.py` adds their DLL folders to the search path automatically — no full CUDA Toolkit needed.
If the GPU still can't run, the app warms up at startup and **falls back to CPU on its own**
(you'll see `[stt] GPU inference unavailable ...; falling back to CPU`), so it always runs.

---

## Project layout

```
config.yaml     all tweakables
config.py       loads config.yaml
audio.py        mic capture -> 16 kHz mono numpy  (swap the recorder)
stt.py          faster-whisper transcription      (swap the STT engine)
cleanup.py      Ollama cleanup call               (swap the LLM/cleanup)
inject.py       clipboard + Ctrl+V paste          (swap the text injection)
hotkey.py       global hotkey state machine (self-check: `python hotkey.py`)
tray.py         tray icon / console state cue
main.py         wires it together + startup checks
```

Each stage is its own module so you can swap one without touching the others.

## Building a standalone .exe

`build.ps1` packages everything into `dist\LocalFlow\` with PyInstaller (onedir — a folder
with `LocalFlow.exe` plus its libraries; faster to start and far simpler than one-file for
these big native deps). Run it from your activated venv:

```powershell
.\build.ps1          # CPU build — small, runs on any Windows machine, self-heals to CPU
.\build.ps1 -Gpu     # also bundle CUDA libs (needs nvidia-cublas-cu12 / nvidia-cudnn-cu12
                     # installed first; adds ~1 GB to the output)
```

Then run `dist\LocalFlow\LocalFlow.exe`. Notes:
- `config.yaml` is copied **next to the exe** and stays editable — change the hotkey/model there.
- The Whisper model still downloads on first run into `%USERPROFILE%\.cache\huggingface`
  (kept out of the bundle to keep it small). First launch needs internet; after that it's offline.
- Ollama is a **separate** app — it must be installed and running on the target machine; it is
  not bundled. (Or ship with `ollama.enabled: false` for raw transcripts.)
- For a tray-only app with no console window, change `--console` to `--windowed` in `build.ps1`
  (you lose the log output).

## Troubleshooting

- **"Ollama not reachable"** on startup → the Ollama app/server isn't running, or the URL is
  wrong. Start Ollama, or set `ollama.enabled: false` to paste raw transcripts.
- **Nothing pastes** → check the target app isn't elevated (run the app elevated too), and that
  the app accepts `Ctrl+V`.
- **Silent / empty recordings** → check the Windows mic permission (step 4) and that the right
  input device is the Windows default.
- **Hotkey does nothing** → another app may own that combo; change `hotkey` in `config.yaml`.
- **Wrong Python** → make sure `pip install` and `python main.py` use the same **Windows** venv,
  not a WSL interpreter.
