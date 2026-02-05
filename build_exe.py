#!/usr/bin/env python3
"""
Build script for AutoPromptPro Windows EXE using PyInstaller
"""
import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a shell command and report status"""
    print(f"\n{'='*60}")
    print(f"→ {description}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {description} failed with code {e.returncode}")
        return False

def main():
    os.chdir('/workspaces/bookish-barnacle')
    
    print("╔════════════════════════════════════════════════════════╗")
    print("║   Building Windows EXE: AutoPromptPro                  ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    # Dependencies should already be installed
    if run_command(
        "python3 -m PyInstaller AutoPromptPro.spec",
        "Building EXE with PyInstaller"
    ):
        if os.path.exists("dist/AutoPromptPro.exe"):
            # Get file size
            size = os.path.getsize("dist/AutoPromptPro.exe") / (1024*1024)
            print(f"\n✓ SUCCESS: EXE created at dist/AutoPromptPro.exe ({size:.1f} MB)")
            return 0
        else:
            print("\n✗ FAILED: EXE was not created. Check build output above.")
            return 1
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main())
