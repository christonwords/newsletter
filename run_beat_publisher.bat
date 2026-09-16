@echo off
setlocal
cd /d "%~dp0"
python tools\beat_publisher\app.py
if errorlevel 1 pause
