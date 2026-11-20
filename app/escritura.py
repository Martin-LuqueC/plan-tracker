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
import unicodedata
from datetime import date, datetime, timedelta

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
        titulo = _escribir_campos(tarea_id, cambios)
        if set(cambios) == {"estado"}:
            nuevo = cambios["estado"]
            texto = (f"Marcado como hecho: {titulo}" if nuevo == "hecho"
                     else f"Estado {TEXTO_ESTADO[nuevo]}: {titulo}")
        else:
            nombres = ", ".join(NOMBRES_CAMPOS[c] for c in cambios)
            texto = f"Editado ({nombres}): {titulo}"
        registrar_cambio(texto)
        return texto


def guardar_evento_id(tarea_id, evento_id):
    """Guarda el id del evento de Calendar (el registro en Cambios lo hace calendario.py)."""
    with _candado:
        _escribir_campos(tarea_id, {"evento_id": str(evento_id)})


def _escribir_campos(tarea_id, cambios):
    """Escribe los campos en la fila de la tarea. Devuelve su título. Usar dentro de _candado."""
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
    return actual.get("titulo", tarea_id)


MAX_SEMANAS = 8


def _agregar_filas(pestana, filas_dict):
    """Agrega filas al final de una pestaña, poniendo cada valor en la columna con su nombre."""
    encabezado = _leer(pestana)
    columnas = [c.strip() for c in encabezado[0]] if encabezado else []
    faltan = {c for fila in filas_dict for c in fila if fila[c] != ""} - set(columnas)
    if faltan:
        raise ErrorDeDatos(f"La pestaña {pestana} no tiene las columnas: {', '.join(sorted(faltan))}")
    valores = [[fila.get(c, "") for c in columnas] for fila in filas_dict]
    _srv().spreadsheets().values().append(
        spreadsheetId=id_hoja(), range=f"'{pestana}'!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"values": valores},
    ).execute()


def crear_plan(nombre, nombre_en, inicio, semanas):
    """Crea un plan con sus semanas. Devuelve (id del plan, texto registrado en Cambios)."""
    nombre = str(nombre or "").strip()
    nombre_en = str(nombre_en or "").strip()
    if not nombre:
        raise ErrorDeDatos("Ponle un nombre al plan.")
    if len(nombre) > 80 or len(nombre_en) > 80:
        raise ErrorDeDatos("El nombre es demasiado largo (máximo 80 letras).")
    try:
        inicio = date.fromisoformat(str(inicio).strip())
    except ValueError:
        raise ErrorDeDatos("La fecha de inicio no es válida.")
    try:
        semanas = int(semanas)
    except (TypeError, ValueError):
        raise ErrorDeDatos("El número de semanas no es válido.")
    if not 1 <= semanas <= MAX_SEMANAS:
        raise ErrorDeDatos(f"El plan debe tener entre 1 y {MAX_SEMANAS} semanas.")
    fin = inicio + timedelta(days=7 * semanas - 1)

    with _candado:
        planes = _leer("Planes")
        columnas = [c.strip() for c in planes[0]] if planes else []
        if "id" not in columnas:
            raise ErrorDeDatos("La pestaña Planes no tiene la columna id.")
        ci = columnas.index("id")
        existentes = {f[ci].strip() for f in planes[1:] if len(f) > ci}
        base = "p" + inicio.strftime("%Y%m%d")
        plan_id, n = base, 2
        while plan_id in existentes:
            plan_id, n = f"{base}-{n}", n + 1

        fila_plan = {"id": plan_id, "nombre": nombre, "inicio": inicio.isoformat(),
                     "fin": fin.isoformat(), "activo": "SI"}
        if nombre_en:
            fila_plan["nombre_en"] = nombre_en
        _agregar_filas("Planes", [fila_plan])
        _agregar_filas("Semanas", [
            {"plan_id": plan_id, "numero": i + 1,
             "inicio": (inicio + timedelta(days=7 * i)).isoformat(),
             "fin": (inicio + timedelta(days=7 * i + 6)).isoformat()}
            for i in range(semanas)
        ])
        texto = (f"Plan nuevo: {nombre} ({semanas} semanas, del "
                 f"{inicio.day} {MESES[inicio.month - 1]} al {fin.day} {MESES[fin.month - 1]})")
        registrar_cambio(texto)
        return plan_id, texto


FRECUENCIAS = {"una_vez", "diaria", "dias_habiles", "semanal", "veces"}


def _slug(texto, palabras=3, largo=24):
    """'Llamar a Robert Half' -> 'llamar-a-robert'"""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    partes = re.findall(r"[a-z0-9]+", sin_tildes.lower())[:palabras]
    return "-".join(partes)[:largo].strip("-") or "tarea"


def crear_tarea(plan_id, semana, titulo, frecuencia, veces=None, dia=None, meta="", detalle=""):
    """Agrega una tarea al final de su semana. Devuelve (id de la tarea, texto registrado)."""
    plan_id = str(plan_id or "").strip()
    titulo = str(titulo or "").strip()
    frecuencia = str(frecuencia or "").strip()
    meta, detalle = str(meta or "").strip(), str(detalle or "").strip()
    if not titulo:
        raise ErrorDeDatos("Ponle un título a la tarea.")
    if len(titulo) > 120:
        raise ErrorDeDatos("El título es demasiado largo (máximo 120 letras).")
    if frecuencia not in FRECUENCIAS:
        raise ErrorDeDatos("Elige una frecuencia válida.")
    try:
        semana = int(semana)
    except (TypeError, ValueError):
        raise ErrorDeDatos("Semana no válida.")
    fila = {"plan_id": plan_id, "semana": semana, "titulo": titulo, "frecuencia": frecuencia,
            "estado": "pendiente", "meta": meta, "detalle": detalle}
    if frecuencia == "veces":
        try:
            veces = int(veces)
        except (TypeError, ValueError):
            raise ErrorDeDatos("Indica cuántas veces.")
        if not 1 <= veces <= 14:
            raise ErrorDeDatos("Las veces deben ir de 1 a 14.")
        fila["veces"] = veces
    if frecuencia == "semanal":
        try:
            dia = int(dia)
        except (TypeError, ValueError):
            raise ErrorDeDatos("Elige el día de la semana.")
        if not 0 <= dia <= 6:
            raise ErrorDeDatos("Elige el día de la semana.")
        fila["dia"] = dia

    with _candado:
        semanas = _leer("Semanas")
        cols_s = [c.strip() for c in semanas[0]] if semanas else []
        existe_semana = any(
            dict(zip(cols_s, f)).get("plan_id", "").strip() == plan_id
            and str(dict(zip(cols_s, f)).get("numero", "")).strip() == str(semana)
            for f in semanas[1:])
        if not existe_semana:
            raise ErrorDeDatos(f"No encontré la semana {semana} de ese plan en la hoja.")

        tareas = _leer("Tareas")
        cols = [c.strip() for c in tareas[0]] if tareas else []
        if "id" not in cols:
            raise ErrorDeDatos("La pestaña Tareas no tiene la columna id.")
        filas = [dict(zip(cols, f)) for f in tareas[1:]]
        ids = {f.get("id", "").strip() for f in filas}
        base = f"s{semana}-{_slug(titulo)}"
        tarea_id, n = base, 2
        while tarea_id in ids:
            tarea_id, n = f"{base}-{n}", n + 1

        ordenes = []
        for f in filas:
            if f.get("plan_id", "").strip() == plan_id and str(f.get("semana", "")).strip() == str(semana):
                try:
                    ordenes.append(int(float(f.get("orden", "0"))))
                except ValueError:
                    pass
        fila["id"] = tarea_id
        fila["orden"] = (max(ordenes) if ordenes else 0) + 10

        _agregar_filas("Tareas", [fila])
        texto = f"Tarea nueva (semana {semana}): {titulo}"
        registrar_cambio(texto)
        return tarea_id, texto


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
