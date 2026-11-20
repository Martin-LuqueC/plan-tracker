"""Lectura de la hoja "Plan Tracker".

Cada pestaña se devuelve como una lista de diccionarios:
la primera fila de la pestaña son los nombres de las columnas.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

from google_auth import servicio_sheets

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def id_hoja():
    valor = os.getenv("SPREADSHEET_ID", "").strip()
    if not valor:
        raise RuntimeError("Falta SPREADSHEET_ID en el archivo .env")
    return valor


def leer_pestana(nombre, servicio=None):
    return leer_pestanas([nombre], servicio)[nombre]


def leer_pestanas(nombres, servicio=None):
    """Lee varias pestañas en una sola consulta a Google."""
    servicio = servicio or servicio_sheets()
    respuesta = (
        servicio.spreadsheets()
        .values()
        .batchGet(spreadsheetId=id_hoja(), ranges=[f"'{n}'" for n in nombres])
        .execute()
    )
    rangos = respuesta.get("valueRanges", [])
    return {n: _a_filas(r.get("values", [])) for n, r in zip(nombres, rangos)}


def _a_filas(filas):
    if not filas:
        return []
    columnas = [c.strip() for c in filas[0]]
    datos = []
    for fila in filas[1:]:
        if not any(str(v).strip() for v in fila):
            continue  # se saltan filas vacías
        fila = list(fila) + [""] * (len(columnas) - len(fila))
        datos.append(dict(zip(columnas, fila)))
    return datos
