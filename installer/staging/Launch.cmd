@echo off
title PluginShell
cd /d "%~dp0"
echo ==========================================================
echo   PluginShell - native plugin microkernel shell
echo ==========================================================
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python 3.10+ was not found in PATH.
  echo Please install Python and enable "Add python.exe to PATH".
  echo See README.md for details.
  echo.
  pause
  exit /b 1
)
python -c "import PySide6" >nul 2>nul
if errorlevel 1 (
  echo Installing native GUI dependency PySide6 (internet required once)...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] PySide6 installation failed.
    echo Run manually:  python -m pip install -r requirements.txt
    echo The kernel, CLI tools and tests still work without PySide6.
    echo.
    pause
    exit /b 1
  )
)
echo Starting PluginShell (empty shell until plugins are installed)...
python run.py
if errorlevel 1 (
  echo PluginShell exited with an error. See README.md for troubleshooting.
  pause
)
