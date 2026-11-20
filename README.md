# Plan Tracker

Aplicación de escritorio para seguir planes de trabajo por semanas.
Los datos viven en la hoja de Google Sheets "Plan Tracker".

## Uso diario

- **Abrir Plan Tracker.cmd**: doble clic para abrir. Arranca el servidor si hace falta
  (sin ventana de consola) y abre la ventana de Chrome. Si ya estaba abierto, solo abre otra ventana.
- **Cerrar Plan Tracker.cmd**: apaga el servidor. Úsalo después de actualizar el programa
  y luego vuelve a abrirlo para que tome la versión nueva.
- **Arrancar con Windows.cmd**: activa o desactiva que Plan Tracker se abra solo al iniciar Windows.
- Si algo falla, los detalles quedan en `plan-tracker.log`.

## Preparar en una computadora nueva

1. Crear el entorno: `py -3.14 -m venv .venv`
2. Instalar librerías: `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`
3. Poner `credentials.json` (de Google Cloud) en esta carpeta. El proyecto de Google Cloud
   necesita activadas la API de Google Sheets y la API de Google Calendar.
4. Copiar `.env.example` como `.env` y completar `SPREADSHEET_ID`.
5. Probar la conexión: `.\.venv\Scripts\python.exe app\probar_hoja.py`
6. Abrir con `Abrir Plan Tracker.cmd`.
