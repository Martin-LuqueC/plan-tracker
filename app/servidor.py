"""Servidor local del Plan Tracker.

Entrega la página (static/index.html) y los datos del tablero en /api/datos.
La hoja de Google es la fuente de verdad: aquí solo se guarda una copia
por unos segundos para no consultar a Google en cada petición.
"""
import os
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from google_auth import servicio_sheets
from hoja import leer_pestanas  # también carga el archivo .env
from tablero import armar_tablero

PESTANAS = ["Planes", "Semanas", "Tareas", "Marcas"]
SEGUNDOS_COPIA = 10
CARPETA_STATIC = Path(__file__).resolve().parent / "static"

app = Flask(__name__, static_folder=None)

_copia = {"datos": None, "hora": 0.0}
_candado = threading.Lock()
_servicio = None


def datos_hoja(forzar=False):
    global _servicio
    with _candado:
        vigente = time.time() - _copia["hora"] < SEGUNDOS_COPIA
        if _copia["datos"] is not None and vigente and not forzar:
            return _copia["datos"]
        if _servicio is None:
            _servicio = servicio_sheets()
        datos = leer_pestanas(PESTANAS, _servicio)
        _copia.update(datos=datos, hora=time.time())
        return datos


@app.get("/")
def inicio():
    return send_from_directory(CARPETA_STATIC, "index.html")


@app.get("/static/<path:archivo>")
def estaticos(archivo):
    return send_from_directory(CARPETA_STATIC, archivo)


@app.get("/api/datos")
def api_datos():
    try:
        datos = datos_hoja(forzar=request.args.get("forzar") == "1")
        idioma = "en" if request.args.get("idioma") == "en" else "es"
        return jsonify(armar_tablero(datos, request.args.get("plan"), idioma=idioma))
    except Exception as error:  # se muestra en pantalla en vez de romper la página
        return jsonify({"error": f"No pude leer la hoja: {error}"}), 502


@app.after_request
def sin_cache(respuesta):
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


if __name__ == "__main__":
    puerto = int(os.getenv("PUERTO", "5050"))
    print(f"Plan Tracker en http://localhost:{puerto}  (Ctrl+C para cerrar)")
    app.run(host="127.0.0.1", port=puerto, debug=False)
