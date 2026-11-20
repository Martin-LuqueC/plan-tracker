"""Escritura en la hoja "Plan Tracker".

Reglas:
- Las filas se buscan leyendo la hoja en ese momento (no la copia guardada),
  para no escribir en la fila equivocada si Claude cambió algo desde un chat.
- Las columnas se ubican por su nombre en la fila 1, no por su posición.
- Los valores se escriben tal cual (RAW), para que Google no convierta
  fechas u horas a otro formato.
- Cada cambio se registra en la pestaña Cambios.
"""
import re
import threading
from datetime import date, datetime

from google_auth import servicio_sheets
from hoja import id_hoja

ESTADOS = {"pendiente", "en_curso", "hecho"}
CAMPOS_EDITABLES = {"estado", "detalle", "notas", "fecha", "hora", "duracion_min"}
NOMBRES_CAMPOS = {
    "estado": "estado", "detalle": "detalle", "notas": "notas",
    "fecha": "fecha", "hora": "hora", "duracion_min": "duración",
}
TEXTO_ESTADO = {"pendiente": "pendiente", "en_curso": "en curso", "hecho": "hecho"}
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

_candado = threading.Lock()  # una escritura a la vez
_servicio = None
_ids_pestanas = {}


class ErrorDeDatos(ValueError):
    """Un dato no válido o una tarea que no existe: se le muestra al usuario."""


def _srv():
    global _servicio
    if _servicio is None:
        _servicio = servicio_sheets()
    return _servicio


def _letra(indice):
    """0 -> A, 25 -> Z, 26 -> AA"""
    letras = ""
    indice += 1
    while indice:
        indice, resto = divmod(indice - 1, 26)
        letras = chr(65 + resto) + letras
    return letras


def _leer(pestana):
    r = _srv().spreadsheets().values().get(spreadsheetId=id_hoja(), range=f"'{pestana}'").execute()
    return r.get("values", [])


def _id_pestana(nombre):
    if nombre not in _ids_pestanas:
        info = _srv().spreadsheets().get(
            spreadsheetId=id_hoja(), fields="sheets.properties(sheetId,title)"
        ).execute()
        for hoja in info["sheets"]:
            _ids_pestanas[hoja["properties"]["title"]] = hoja["properties"]["sheetId"]
    return _ids_pestanas[nombre]


def _validar(campo, valor):
    valor = str(valor if valor is not None else "").strip()
    if campo == "estado" and valor not in ESTADOS:
        raise ErrorDeDatos(f"Estado no válido: {valor}")
    if campo == "fecha" and valor:
        try:
            date.fromisoformat(valor)
        except ValueError:
            raise ErrorDeDatos(f"Fecha no válida: {valor}")
    if campo == "hora" and valor and not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", valor):
        raise ErrorDeDatos(f"Hora no válida: {valor}")
    if campo == "duracion_min" and valor:
        if not valor.isdigit() or int(valor) > 24 * 60:
            raise ErrorDeDatos(f"Duración no válida: {valor}")
        return int(valor)
    return valor


def registrar_cambio(texto, origen="app"):
    fila = [datetime.now().strftime("%Y-%m-%d %H:%M"), origen, texto]
    _srv().spreadsheets().values().append(
        spreadsheetId=id_hoja(), range="'Cambios'!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": [fila]},
    ).execute()


def actualizar_tarea(tarea_id, cambios):
    """Cambia campos de una tarea. Devuelve el texto registrado en Cambios."""
    cambios = {c: _validar(c, v) for c, v in cambios.items() if c in CAMPOS_EDITABLES}
    if not cambios:
        raise ErrorDeDatos("No hay nada que guardar.")

    with _candado:
        filas = _leer("Tareas")
        if not filas:
            raise ErrorDeDatos("La pestaña Tareas está vacía.")
        columnas = [c.strip() for c in filas[0]]
        if "id" not in columnas:
            raise ErrorDeDatos("La pestaña Tareas no tiene la columna id.")
        col_id = columnas.index("id")

        numero_fila, actual = None, None
        for i, fila in enumerate(filas[1:], start=2):
            if len(fila) > col_id and fila[col_id].strip() == tarea_id:
                numero_fila, actual = i, dict(zip(columnas, fila))
                break
        if numero_fila is None:
            raise ErrorDeDatos(f"No encontré la tarea {tarea_id} en la hoja.")

        datos = []
        for campo, valor in cambios.items():
            if campo not in columnas:
                raise ErrorDeDatos(f"La pestaña Tareas no tiene la columna {campo}.")
            celda = f"'Tareas'!{_letra(columnas.index(campo))}{numero_fila}"
            datos.append({"range": celda, "values": [[valor]]})
        _srv().spreadsheets().values().batchUpdate(
            spreadsheetId=id_hoja(),
            body={"valueInputOption": "RAW", "data": datos},
        ).execute()

        titulo = actual.get("titulo", tarea_id)
        if set(cambios) == {"estado"}:
            nuevo = cambios["estado"]
            texto = (f"Marcado como hecho: {titulo}" if nuevo == "hecho"
                     else f"Estado {TEXTO_ESTADO[nuevo]}: {titulo}")
        else:
            nombres = ", ".join(NOMBRES_CAMPOS[c] for c in cambios)
            texto = f"Editado ({nombres}): {titulo}"
        registrar_cambio(texto)
        return texto


def marcar_dia(tarea_id, fecha, marcado):
    """Agrega o quita la fila de Marcas para ese día. Devuelve el texto registrado."""
    try:
        dia = date.fromisoformat(str(fecha).strip())
    except ValueError:
        raise ErrorDeDatos(f"Fecha no válida: {fecha}")
    fecha = dia.isoformat()

    with _candado:
        tareas = _leer("Tareas")
        columnas_t = [c.strip() for c in tareas[0]] if tareas else []
        if "id" not in columnas_t:
            raise ErrorDeDatos("La pestaña Tareas no tiene la columna id.")
        ci, ct = columnas_t.index("id"), columnas_t.index("titulo") if "titulo" in columnas_t else None
        fila_tarea = next((f for f in tareas[1:] if len(f) > ci and f[ci].strip() == tarea_id), None)
        if fila_tarea is None:
            raise ErrorDeDatos(f"No encontré la tarea {tarea_id} en la hoja.")
        titulo = fila_tarea[ct] if ct is not None and len(fila_tarea) > ct else tarea_id

        marcas = _leer("Marcas")
        columnas = [c.strip() for c in marcas[0]] if marcas else []
        if "tarea_id" not in columnas or "fecha" not in columnas:
            raise ErrorDeDatos("La pestaña Marcas necesita las columnas tarea_id y fecha.")
        c_id, c_fecha = columnas.index("tarea_id"), columnas.index("fecha")
        filas_iguales = [
            i for i, fila in enumerate(marcas[1:], start=1)  # índice desde 0 contando el encabezado
            if len(fila) > max(c_id, c_fecha)
            and fila[c_id].strip() == tarea_id and fila[c_fecha].strip()[:10] == fecha
        ]

        dia_texto = f"{DIAS[dia.weekday()]} {dia.day} {MESES[dia.month - 1]}"
        if marcado:
            if filas_iguales:
                return None  # ya estaba marcado: no se duplica
            fila = [""] * len(columnas)
            fila[c_id], fila[c_fecha] = tarea_id, fecha
            _srv().spreadsheets().values().append(
                spreadsheetId=id_hoja(), range="'Marcas'!A1",
                valueInputOption="RAW", insertDataOption="INSERT_ROWS",
                body={"values": [fila]},
            ).execute()
            texto = f"Día marcado ({dia_texto}): {titulo}"
        else:
            if not filas_iguales:
                return None  # ya estaba desmarcado
            hoja_id = _id_pestana("Marcas")
            # se borran de abajo hacia arriba para que no se corran los números de fila
            pedidos = [{"deleteDimension": {"range": {
                "sheetId": hoja_id, "dimension": "ROWS", "startIndex": i, "endIndex": i + 1}}}
                for i in sorted(filas_iguales, reverse=True)]
            _srv().spreadsheets().batchUpdate(spreadsheetId=id_hoja(), body={"requests": pedidos}).execute()
            texto = f"Día desmarcado ({dia_texto}): {titulo}"

        registrar_cambio(texto)
        return texto
