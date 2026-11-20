@echo off
rem Apaga el servidor de Plan Tracker (por ejemplo, despues de actualizar el programa).
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "app\lanzador.py" --cerrar
