#!/bin/bash
set -e

cd /workspaces/bookish-barnacle

echo "Building Windows EXE for GUI Pro..."
echo "Install dependencies if not already installed..."
python3 -m pip install -q pyinstaller ttkbootstrap pillow 2>/dev/null || true

echo "Running PyInstaller..."
python3 -m PyInstaller AutoPromptPro.spec

echo "Build complete!"
if [ -f "dist/AutoPromptPro.exe" ]; then
    echo "✓ EXE created: dist/AutoPromptPro.exe"
    ls -lh dist/AutoPromptPro.exe
else
    echo "✗ EXE not found. Check build output above."
fi
