@echo off
rem Activa o desactiva que Plan Tracker se abra solo al iniciar Windows.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "app\lanzador.py" --inicio
