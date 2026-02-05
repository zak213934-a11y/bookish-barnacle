# Build a Windows EXE for Genv3 v6.5.1 (Tkinter GUI)
# Run this from the extracted project folder in PowerShell.

$ErrorActionPreference = 'Stop'

if (-not (Test-Path .\anime_prompt_generator_gui_pro.py)) {
  Write-Host "ERROR: Run this script from the folder that contains anime_prompt_generator_gui_pro.py" -ForegroundColor Red
  exit 1
}

if (-not (Test-Path .\.venv)) {
  py -m venv .venv
}

. .\.venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -U pyinstaller

# Optional: modern theme support (won't break if missing at runtime)
python -m pip install -U ttkbootstrap 2>$null

# Build using the spec (bundles ./data)
pyinstaller .\Genv3_win.spec

Write-Host "Done. EXE is in .\dist\Genv3.exe" -ForegroundColor Green
