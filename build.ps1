# Build LocalFlow into a standalone Windows app (onedir) with PyInstaller.
#   .\build.ps1          -> CPU build (small, runs anywhere; self-heals to CPU)
#   .\build.ps1 -Gpu     -> also bundle CUDA libs for GPU (much bigger; needs the
#                           nvidia-cublas-cu12 / nvidia-cudnn-cu12 packages installed)
param([switch]$Gpu)

$ErrorActionPreference = "Stop"

python -m pip install --quiet pyinstaller

# These packages ship native DLLs / data that PyInstaller misses without --collect-all.
$args = @(
    "--noconfirm", "--clean",
    "--name", "LocalFlow",
    "--onedir",            # folder, not one .exe: faster startup, sane for big native libs
    "--console",           # keep the log window. Swap for --windowed for tray-only (no logs).
    "main.py",
    "--collect-all", "faster_whisper",
    "--collect-all", "ctranslate2",
    "--collect-all", "av",
    "--collect-all", "onnxruntime",
    "--collect-all", "sounddevice",
    "--collect-all", "pystray",
    "--collect-submodules", "pynput"
)
if ($Gpu) { $args += @("--collect-all", "nvidia") }

pyinstaller @args

# Ship config.yaml NEXT TO the exe so it stays editable (loader reads the exe folder).
Copy-Item -Force config.yaml dist\LocalFlow\config.yaml

Write-Host ""
Write-Host "Done -> dist\LocalFlow\LocalFlow.exe   (edit dist\LocalFlow\config.yaml to tweak)"
