"""Google Calendar: crea o actualiza el evento de una tarea y guarda su evento_id en la hoja.

Qué evento se crea:
- fecha y hora: evento con hora, con la duración de la tarea (60 min si no tiene).
- fecha sin hora: evento de día completo.
- sin fecha, recurrente con hora (diaria, L a V o semanal): evento que se repite
  esa semana del plan.
- si no se puede armar ninguno de los anteriores, se pide una fecha.
"""
from datetime import date, datetime, timedelta

from googleapiclient.errors import HttpError

import escritura
from escritura import ErrorDeDatos, _leer, registrar_cambio
from google_auth import servicio_calendar

CALENDARIO = "primary"
DURACION_POR_DEFECTO = 60
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
BYDAY = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]

_servicio = None
_zona = None


def _cal():
    global _servicio
    if _servicio is None:
        _servicio = servicio_calendar()
    return _servicio


def zona_horaria():
    """La zona horaria del calendario principal (la devuelve la lista de eventos)."""
    global _zona
    if _zona is None:
        r = _cal().events().list(calendarId=CALENDARIO, maxResults=1).execute()
        _zona = r.get("timeZone") or "America/New_York"
    return _zona


def _filas(pestana):
    filas = _leer(pestana)
    if not filas:
        return [], []
    columnas = [c.strip() for c in filas[0]]
    datos = [dict(zip(columnas, list(f) + [""] * (len(columnas) - len(f)))) for f in filas[1:]]
    return columnas, datos


def _numero(valor, por_defecto=0):
    try:
        return int(float(str(valor).strip()))
    except ValueError:
        return por_defecto


def _fecha_texto(d):
    return f"{DIAS[d.weekday()]} {d.day} {MESES[d.month - 1]}"


def _armar_evento(tarea, semana):
    """Devuelve (cuerpo del evento, texto corto de cuándo es)."""
    zona = zona_horaria()
    titulo = tarea.get("titulo", "").strip() or tarea.get("id", "")
    hora = tarea.get("hora", "").strip()
    minutos = _numero(tarea.get("duracion_min"), 0) or DURACION_POR_DEFECTO
    frecuencia = tarea.get("frecuencia", "").strip()

    partes = []
    for nombre, campo in (("Meta", "meta"), ("Detalle", "detalle"), ("Notas", "notas")):
        valor = tarea.get(campo, "").strip()
        if valor:
            partes.append(f"{nombre}: {valor}")
    partes.append("Creado desde Plan Tracker.")
    cuerpo = {
        "summary": titulo,
        "description": "\n\n".join(partes),
        "extendedProperties": {"private": {"plan_tracker_tarea": tarea.get("id", "")}},
    }

    try:
        fecha = date.fromisoformat(tarea.get("fecha", "").strip()) if tarea.get("fecha", "").strip() else None
    except ValueError:
        raise ErrorDeDatos("La fecha de la tarea no es válida.")

    repeticion = None
    if fecha is None:
        inicio_semana = None
        if semana:
            try:
                inicio_semana = date.fromisoformat(semana.get("inicio", "").strip())
            except ValueError:
                inicio_semana = None
        if hora and inicio_semana and frecuencia in ("diaria", "dias_habiles", "semanal"):
            if frecuencia == "diaria":
                fecha, repeticion = inicio_semana, "RRULE:FREQ=DAILY;COUNT=7"
            elif frecuencia == "dias_habiles":
                # primer día hábil de la semana y luego los demás hasta completar 5
                dias = [inicio_semana + timedelta(days=i) for i in range(7)]
                habiles = [d for d in dias if d.weekday() < 5]
                fecha = habiles[0]
                byday = ",".join(BYDAY[d.weekday()] for d in habiles)
                repeticion = f"RRULE:FREQ=WEEKLY;BYDAY={byday};COUNT={len(habiles)}"
            else:
                dia = _numero(tarea.get("dia"), -1)
                if not 0 <= dia <= 6:
                    raise ErrorDeDatos("Ponle una fecha a la tarea para agendarla.")
                fecha = next(inicio_semana + timedelta(days=i) for i in range(7)
                             if (inicio_semana + timedelta(days=i)).weekday() == dia)
        else:
            raise ErrorDeDatos("Ponle una fecha a la tarea para agendarla.")

    if hora:
        try:
            inicio = datetime.combine(fecha, datetime.strptime(hora, "%H:%M").time())
        except ValueError:
            raise ErrorDeDatos("La hora de la tarea no es válida.")
        fin = inicio + timedelta(minutes=minutos)
        cuerpo["start"] = {"dateTime": inicio.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": zona}
        cuerpo["end"] = {"dateTime": fin.strftime("%Y-%m-%dT%H:%M:%S"), "timeZone": zona}
        cuando = f"{_fecha_texto(fecha)} {hora}"
    else:
        cuerpo["start"] = {"date": fecha.isoformat()}
        cuerpo["end"] = {"date": (fecha + timedelta(days=1)).isoformat()}
        cuando = f"{_fecha_texto(fecha)}, día completo"

    if repeticion:
        cuerpo["recurrence"] = [repeticion]
        dias_texto = "todos los días" if frecuencia == "diaria" else "lunes a viernes"
        cuando = f"{dias_texto} desde el {_fecha_texto(fecha)} a las {hora}"
    else:
        cuerpo["recurrence"] = []  # al actualizar, quita una repetición anterior
    return cuerpo, cuando


def agendar(tarea_id):
    """Crea o actualiza el evento de la tarea. Devuelve el texto registrado y el enlace al evento."""
    with escritura._candado:
        _, tareas = _filas("Tareas")
        tarea = next((t for t in tareas if t.get("id", "").strip() == tarea_id), None)
        if tarea is None:
            raise ErrorDeDatos(f"No encontré la tarea {tarea_id} en la hoja.")
        _, semanas = _filas("Semanas")
        semana = next((s for s in semanas
                       if s.get("plan_id", "").strip() == tarea.get("plan_id", "").strip()
                       and _numero(s.get("numero")) == _numero(tarea.get("semana"))), None)

    cuerpo, cuando = _armar_evento(tarea, semana)
    titulo = cuerpo["summary"]
    evento_id = tarea.get("evento_id", "").strip()

    evento, accion = None, "Agendado en Calendar"
    if evento_id:
        try:
            evento = _cal().events().patch(calendarId=CALENDARIO, eventId=evento_id, body=cuerpo).execute()
            if evento.get("status") == "cancelled":  # estaba borrado: se crea de nuevo
                evento = None
            else:
                accion = "Evento actualizado en Calendar"
        except HttpError as error:
            if error.resp.status not in (404, 410):
                raise
    if evento is None:
        evento = _cal().events().insert(calendarId=CALENDARIO, body=cuerpo).execute()

    if evento["id"] != evento_id:
        escritura.guardar_evento_id(tarea_id, evento["id"])
    texto = f"{accion} ({cuando}): {titulo}"
    registrar_cambio(texto)
    return texto, evento.get("htmlLink", "")
