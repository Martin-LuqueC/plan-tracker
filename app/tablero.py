"""Cálculos del tablero: arma, a partir de las pestañas de la hoja,
todo lo que la pantalla necesita mostrar para un plan, en español o inglés."""
from datetime import date, timedelta

TEXTOS = {
    "es": {
        "letras": ["L", "M", "M", "J", "V", "S", "D"],
        "dias": ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"],
        "meses": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
        "una_vez": "1 vez",
        "diaria": "diaria",
        "dias_habiles": "L a V",
        "semanal_dia": "cada {dia}",
        "semanal": "1 por semana",
        "veces": "{n} veces",
        "empieza_manana": "Empieza mañana",
        "empieza_en": "Empieza en {n} días",
        "terminado": "Plan terminado",
        "semana_dia": "Semana {s}, día {d} de 7",
        "vacia": "La pestaña Planes está vacía.",
    },
    "en": {
        "letras": ["M", "T", "W", "T", "F", "S", "S"],
        "dias": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
        "meses": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "una_vez": "once",
        "diaria": "daily",
        "dias_habiles": "Mon to Fri",
        "semanal_dia": "every {dia}",
        "semanal": "once a week",
        "veces": "{n} times",
        "empieza_manana": "Starts tomorrow",
        "empieza_en": "Starts in {n} days",
        "terminado": "Plan finished",
        "semana_dia": "Week {s}, day {d} of 7",
        "vacia": "The Planes tab is empty.",
    },
}
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


def fecha_corta(f, idioma="es"):
    if not f:
        return ""
    mes = TEXTOS[idioma]["meses"][f.month - 1]
    return f"{mes} {f.day}" if idioma == "en" else f"{f.day} {mes}"


def rango_texto(inicio, fin, idioma="es"):
    if not inicio or not fin:
        return ""
    meses = TEXTOS[idioma]["meses"]
    if idioma == "en":
        if inicio.month == fin.month:
            return f"{meses[inicio.month - 1]} {inicio.day} to {fin.day}"
        return f"{fecha_corta(inicio, 'en')} to {fecha_corta(fin, 'en')}"
    if inicio.month == fin.month:
        return f"{inicio.day} al {fin.day} {meses[fin.month - 1]}"
    return f"{fecha_corta(inicio)} al {fecha_corta(fin)}"


def frecuencia_texto(t, idioma="es"):
    tx = TEXTOS[idioma]
    f = t.get("frecuencia", "").strip()
    if f in ("una_vez", "diaria", "dias_habiles"):
        return tx[f]
    if f == "semanal":
        dia = a_numero(t.get("dia"), -1)
        return tx["semanal_dia"].format(dia=tx["dias"][dia]) if 0 <= dia <= 6 else tx["semanal"]
    if f == "veces":
        n = a_numero(t.get("veces"), 0)
        return tx["veces"].format(n=n) if n != 1 else tx["una_vez"]
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


def traducido(fila, campo, idioma):
    """En inglés usa la columna campo_en si tiene texto; si no, la original."""
    if idioma == "en":
        valor = str(fila.get(f"{campo}_en", "")).strip()
        if valor:
            return valor
    return fila.get(campo, "")


def armar_tablero(datos, plan_id=None, hoy=None, idioma="es"):
    tx = TEXTOS[idioma]
    hoy = hoy or date.today()
    planes = datos["Planes"]
    if not planes:
        return {"error": tx["vacia"]}

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
    # si ya terminó, la última. "estado_plan" dice cuál de los tres casos es.
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
        dias = [ini + timedelta(days=i) for i in range(7)] if ini else []

        tareas, hechas, total = [], 0, 0
        for t in sorted((t for t in tareas_plan if a_numero(t.get("semana")) == numero),
                        key=lambda t: a_numero(t.get("orden"), 999)):
            tid = t.get("id", "").strip()
            recurrente = t.get("frecuencia", "").strip() in RECURRENTES
            meta = meta_semanal(t)
            marcadas = {d for d in dias if d in marcas.get(tid, set())}
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
                "frecuencia": frecuencia_texto(t, idioma),
                "recurrente": recurrente,
                "estado": estado,
                "completa": cumplidas >= meta,
                "cumplidas": cumplidas,
                "meta_semanal": meta,
                "dias": [{"fecha": d.isoformat(),
                          "letra": tx["letras"][d.weekday()],
                          "nombre": f"{tx['dias'][d.weekday()]} {fecha_corta(d, idioma)}",
                          "marcado": d in marcadas,
                          "toca": d.weekday() in esperados}
                         for d in dias] if recurrente else [],
                "meta": t.get("meta", ""),
                "detalle": t.get("detalle", ""),
                "notas": t.get("notas", ""),
                "fecha": t.get("fecha", ""),
                "fecha_texto": fecha_corta(a_fecha(t.get("fecha")), idioma),
                "hora": t.get("hora", ""),
                "duracion_min": t.get("duracion_min", ""),
                "evento_id": t.get("evento_id", ""),
            })

        semanas.append({
            "numero": numero,
            "rango": rango_texto(ini, fin, idioma),
            "enfoque": traducido(s, "enfoque", idioma),
            "nota": traducido(s, "nota", idioma),
            "actual": numero == actual,
            "tareas": tareas,
            "avance": round(100 * hechas / total) if total else 0,
        })

    # Texto de la barra superior
    sem_actual = next((s for s in semanas if s["actual"]), None)
    if estado_plan == "por_empezar":
        inicio = a_fecha(plan.get("inicio")) or a_fecha(semanas_hoja[0].get("inicio"))
        faltan = (inicio - hoy).days
        texto_dia = tx["empieza_manana"] if faltan == 1 else tx["empieza_en"].format(n=faltan)
    elif estado_plan == "terminado":
        texto_dia = tx["terminado"]
    else:
        ini = a_fecha(next(s for s in semanas_hoja if a_numero(s.get("numero")) == actual).get("inicio"))
        texto_dia = tx["semana_dia"].format(s=actual, d=(hoy - ini).days + 1)

    return {
        "hoy": hoy.isoformat(),
        "idioma": idioma,
        "plan": {"id": pid, "nombre": traducido(plan, "nombre", idioma),
                 "color": plan.get("color", "").strip().lower() or "carolina"},
        "planes": [{"id": p.get("id", ""), "nombre": traducido(p, "nombre", idioma),
                    "activo": p.get("activo", "").strip().upper() == "SI",
                    "color": p.get("color", "").strip().lower() or "carolina"} for p in planes],
        "estado_plan": estado_plan,
        "texto_dia": texto_dia,
        "semana_actual": actual,
        "avance_semana": sem_actual["avance"] if sem_actual else 0,
        "semanas": semanas,
    }
