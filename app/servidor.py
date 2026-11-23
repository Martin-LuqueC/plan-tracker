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

from calendario import agendar
from escritura import (ErrorDeDatos, actualizar_tarea, cambiar_color, crear_plan, crear_tarea,
                       marcar_dia)
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


def _olvidar_copia():
    with _candado:
        _copia["hora"] = 0.0


def _pedido_json():
    # Solo se aceptan pedidos JSON: así otra página web no puede escribir en tu hoja.
    if not request.is_json:
        return None
    return request.get_json(silent=True) or {}


@app.post("/api/tarea/<tarea_id>")
def api_tarea(tarea_id):
    cuerpo = _pedido_json()
    if cuerpo is None:
        return jsonify({"error": "Pedido no válido."}), 400
    try:
        texto = actualizar_tarea(tarea_id, cuerpo.get("cambios", {}))
    except ErrorDeDatos as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"No pude guardar en la hoja: {error}"}), 502
    finally:
        _olvidar_copia()
    return jsonify({"ok": True, "cambio": texto})


@app.post("/api/marca")
def api_marca():
    cuerpo = _pedido_json()
    if cuerpo is None:
        return jsonify({"error": "Pedido no válido."}), 400
    try:
        texto = marcar_dia(str(cuerpo.get("tarea_id", "")).strip(), cuerpo.get("fecha", ""),
                           bool(cuerpo.get("marcado")))
    except ErrorDeDatos as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"No pude guardar en la hoja: {error}"}), 502
    finally:
        _olvidar_copia()
    return jsonify({"ok": True, "cambio": texto})


@app.post("/api/tarea/<tarea_id>/agendar")
def api_agendar(tarea_id):
    if _pedido_json() is None:
        return jsonify({"error": "Pedido no válido."}), 400
    try:
        texto, enlace = agendar(tarea_id)
    except ErrorDeDatos as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"No pude agendar en Calendar: {error}"}), 502
    finally:
        _olvidar_copia()
    return jsonify({"ok": True, "cambio": texto, "enlace": enlace})


@app.post("/api/plan")
def api_plan():
    cuerpo = _pedido_json()
    if cuerpo is None:
        return jsonify({"error": "Pedido no válido."}), 400
    try:
        plan_id, texto = crear_plan(cuerpo.get("nombre"), cuerpo.get("nombre_en"),
                                    cuerpo.get("inicio"), cuerpo.get("semanas"), cuerpo.get("color"))
    except ErrorDeDatos as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"No pude crear el plan en la hoja: {error}"}), 502
    finally:
        _olvidar_copia()
    return jsonify({"ok": True, "plan_id": plan_id, "cambio": texto})


@app.post("/api/plan/<plan_id>/color")
def api_color(plan_id):
    cuerpo = _pedido_json()
    if cuerpo is None:
        return jsonify({"error": "Pedido no válido."}), 400
    try:
        texto = cambiar_color(plan_id, cuerpo.get("color"))
    except ErrorDeDatos as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"No pude guardar el color en la hoja: {error}"}), 502
    finally:
        _olvidar_copia()
    return jsonify({"ok": True, "cambio": texto})


@app.post("/api/tarea")
def api_tarea_nueva():
    cuerpo = _pedido_json()
    if cuerpo is None:
        return jsonify({"error": "Pedido no válido."}), 400
    try:
        tarea_id, texto = crear_tarea(
            cuerpo.get("plan_id"), cuerpo.get("semana"), cuerpo.get("titulo"),
            cuerpo.get("frecuencia"), cuerpo.get("veces"), cuerpo.get("dia"),
            cuerpo.get("meta"), cuerpo.get("detalle"))
    except ErrorDeDatos as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"No pude crear la tarea en la hoja: {error}"}), 502
    finally:
        _olvidar_copia()
    return jsonify({"ok": True, "tarea_id": tarea_id, "cambio": texto})


@app.get("/api/salud")
def api_salud():
    # El lanzador pregunta aquí si Plan Tracker ya está corriendo
    return jsonify({"app": "plan-tracker"})


@app.post("/api/apagar")
def api_apagar():
    if _pedido_json() is None:
        return jsonify({"error": "Pedido no válido."}), 400
    # Responde primero y se apaga medio segundo después
    threading.Timer(0.5, os._exit, args=(0,)).start()
    return jsonify({"ok": True})


@app.after_request
def sin_cache(respuesta):
    respuesta.headers["Cache-Control"] = "no-store"
    return respuesta


if __name__ == "__main__":
    puerto = int(os.getenv("PUERTO", "5050"))
    print(f"Plan Tracker en http://localhost:{puerto}  (Ctrl+C para cerrar)")
    app.run(host="127.0.0.1", port=puerto, debug=False)
