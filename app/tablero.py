"""Cálculos del tablero: arma, a partir de las pestañas de la hoja,
todo lo que la pantalla necesita mostrar para un plan."""
from datetime import date, timedelta

LETRAS = ["L", "M", "M", "J", "V", "S", "D"]
DIAS_NOMBRE = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
RECURRENTES = {"diaria", "dias_habiles", "semanal", "veces"}


def a_fecha(texto):
    try:
        return date.fromisoformat(str(texto).strip()[:10])
    except ValueError:
        return None


def a_numero(valor, por_defecto=0):
    try:
        return int(float(str(valor).strip()))
    except ValueError:
        return por_defecto


def fecha_corta(f):
    return f"{f.day} {MESES[f.month - 1]}" if f else ""


def rango_texto(inicio, fin):
    if not inicio or not fin:
        return ""
    if inicio.month == fin.month:
        return f"{inicio.day} al {fin.day} {MESES[fin.month - 1]}"
    return f"{fecha_corta(inicio)} al {fecha_corta(fin)}"


def frecuencia_texto(t):
    f = t.get("frecuencia", "").strip()
    if f == "una_vez":
        return "1 vez"
    if f == "diaria":
        return "diaria"
    if f == "dias_habiles":
        return "L a V"
    if f == "semanal":
        dia = a_numero(t.get("dia"), -1)
        return f"cada {DIAS_NOMBRE[dia]}" if 0 <= dia <= 6 else "1 por semana"
    if f == "veces":
        n = a_numero(t.get("veces"), 0)
        return f"{n} veces" if n != 1 else "1 vez"
    return f


def meta_semanal(t):
    """Cuántas veces hay que cumplir la tarea en la semana."""
    f = t.get("frecuencia", "").strip()
    return {
        "diaria": 7,
        "dias_habiles": 5,
        "semanal": 1,
        "veces": max(a_numero(t.get("veces"), 1), 1),
    }.get(f, 1)


def dias_esperados(t):
    """Qué días de la semana (0 lunes a 6 domingo) se espera cumplir.
    Sirve para atenuar en pantalla los días que no tocan."""
    f = t.get("frecuencia", "").strip()
    if f == "dias_habiles":
        return [0, 1, 2, 3, 4]
    if f == "semanal":
        dia = a_numero(t.get("dia"), -1)
        return [dia] if 0 <= dia <= 6 else list(range(7))
    return list(range(7))


def armar_tablero(datos, plan_id=None, hoy=None):
    hoy = hoy or date.today()
    planes = datos["Planes"]
    if not planes:
        return {"error": "La pestaña Planes está vacía."}

    plan = next((p for p in planes if p.get("id") == plan_id), None)
    if plan is None:
        activos = [p for p in planes if p.get("activo", "").strip().upper() == "SI"]
        plan = activos[0] if activos else planes[0]
    pid = plan.get("id", "").strip()

    marcas = {}
    for m in datos["Marcas"]:
        f = a_fecha(m.get("fecha"))
        if f:
            marcas.setdefault(m.get("tarea_id", "").strip(), set()).add(f)

    semanas_hoja = sorted(
        (s for s in datos["Semanas"] if s.get("plan_id", "").strip() == pid),
        key=lambda s: a_numero(s.get("numero")),
    )
    tareas_plan = [t for t in datos["Tareas"] if t.get("plan_id", "").strip() == pid]

    # Semana actual: la que contiene hoy. Si el plan no empezó, la primera;
    # si ya terminó, la última. "estado" dice cuál de los tres casos es.
    actual, estado_plan = None, "en_curso"
    for s in semanas_hoja:
        ini, fin = a_fecha(s.get("inicio")), a_fecha(s.get("fin"))
        if ini and fin and ini <= hoy <= fin:
            actual = a_numero(s.get("numero"))
    if actual is None and semanas_hoja:
        primera_ini = a_fecha(semanas_hoja[0].get("inicio"))
        if primera_ini and hoy < primera_ini:
            actual, estado_plan = a_numero(semanas_hoja[0].get("numero")), "por_empezar"
        else:
            actual, estado_plan = a_numero(semanas_hoja[-1].get("numero")), "terminado"

    semanas = []
    for s in semanas_hoja:
        numero = a_numero(s.get("numero"))
        ini, fin = a_fecha(s.get("inicio")), a_fecha(s.get("fin"))
        dias = []
        if ini:
            for i in range(7):
                d = ini + timedelta(days=i)
                dias.append({"fecha": d.isoformat(), "letra": LETRAS[d.weekday()],
                             "nombre": f"{DIAS_NOMBRE[d.weekday()]} {fecha_corta(d)}",
                             "hoy": d == hoy, "pasado": d < hoy})

        tareas, hechas, total = [], 0, 0
        for t in sorted((t for t in tareas_plan if a_numero(t.get("semana")) == numero),
                        key=lambda t: a_numero(t.get("orden"), 999)):
            tid = t.get("id", "").strip()
            recurrente = t.get("frecuencia", "").strip() in RECURRENTES
            meta = meta_semanal(t)
            marcadas = [d["fecha"] for d in dias if a_fecha(d["fecha"]) in marcas.get(tid, set())]
            estado = t.get("estado", "").strip() or "pendiente"
            if recurrente:
                cumplidas = meta if estado == "hecho" else min(len(marcadas), meta)
            else:
                cumplidas = 1 if estado == "hecho" else 0
            hechas += cumplidas
            total += meta
            esperados = dias_esperados(t)
            tareas.append({
                "id": tid,
                "titulo": t.get("titulo", ""),
                "frecuencia": frecuencia_texto(t),
                "recurrente": recurrente,
                "estado": estado,
                "completa": cumplidas >= meta,
                "cumplidas": cumplidas,
                "meta_semanal": meta,
                "dias": [{"fecha": d["fecha"], "letra": d["letra"],
                          "marcado": d["fecha"] in marcadas,
                          "toca": a_fecha(d["fecha"]).weekday() in esperados}
                         for d in dias] if recurrente else [],
                "meta": t.get("meta", ""),
                "detalle": t.get("detalle", ""),
                "notas": t.get("notas", ""),
                "fecha": t.get("fecha", ""),
                "fecha_texto": fecha_corta(a_fecha(t.get("fecha"))),
                "hora": t.get("hora", ""),
                "duracion_min": t.get("duracion_min", ""),
                "evento_id": t.get("evento_id", ""),
            })

        semanas.append({
            "numero": numero,
            "rango": rango_texto(ini, fin),
            "enfoque": s.get("enfoque", ""),
            "nota": s.get("nota", ""),
            "actual": numero == actual,
            "dias": dias,
            "tareas": tareas,
            "avance": round(100 * hechas / total) if total else 0,
        })

    # Texto de la barra superior
    sem_actual = next((s for s in semanas if s["actual"]), None)
    if estado_plan == "por_empezar":
        inicio = a_fecha(plan.get("inicio")) or a_fecha(semanas_hoja[0].get("inicio"))
        faltan = (inicio - hoy).days
        texto_dia = "Empieza mañana" if faltan == 1 else f"Empieza en {faltan} días"
    elif estado_plan == "terminado":
        texto_dia = "Plan terminado"
    else:
        ini = a_fecha(next(s for s in semanas_hoja if a_numero(s.get("numero")) == actual).get("inicio"))
        texto_dia = f"Semana {actual}, día {(hoy - ini).days + 1} de 7"

    return {
        "hoy": hoy.isoformat(),
        "plan": {"id": pid, "nombre": plan.get("nombre", "")},
        "planes": [{"id": p.get("id", ""), "nombre": p.get("nombre", "")} for p in planes],
        "estado_plan": estado_plan,
        "texto_dia": texto_dia,
        "semana_actual": actual,
        "avance_semana": sem_actual["avance"] if sem_actual else 0,
        "semanas": semanas,
    }
