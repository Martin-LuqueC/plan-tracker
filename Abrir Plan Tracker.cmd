@echo off
rem Abre Plan Tracker: arranca el servidor si hace falta y abre la ventana.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "app\lanzador.py"
