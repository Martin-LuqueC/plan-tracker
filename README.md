# Plan Tracker

Aplicación de escritorio para seguir planes de trabajo por semanas.
Los datos viven en la hoja de Google Sheets "Plan Tracker".

## Preparar en una computadora nueva

1. Crear el entorno: `py -3.14 -m venv .venv`
2. Instalar librerías: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Poner `credentials.json` (de Google Cloud) en esta carpeta.
4. Copiar `.env.example` como `.env` y completar `SPREADSHEET_ID`.
5. Probar la conexión: `.\.venv\Scripts\python.exe app\probar_hoja.py`
