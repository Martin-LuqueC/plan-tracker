"""Prueba de la fase 2: muestra en consola las tareas de la semana 1 del plan activo."""
from google_auth import servicio_sheets
from hoja import leer_pestana

FRECUENCIA_CORTA = {
    "una_vez": "1 vez",
    "diaria": "diaria",
    "dias_habiles": "L a V",
    "semanal": "semanal",
}


def frecuencia_texto(tarea):
    frecuencia = tarea.get("frecuencia", "").strip()
    if frecuencia == "veces":
        return f"{tarea.get('veces', '?')} veces"
    return FRECUENCIA_CORTA.get(frecuencia, frecuencia or "?")


def numero(valor, por_defecto=0):
    try:
        return int(float(str(valor).strip()))
    except ValueError:
        return por_defecto


def main():
    servicio = servicio_sheets()
    planes = leer_pestana("Planes", servicio)
    tareas = leer_pestana("Tareas", servicio)

    activos = [p for p in planes if p.get("activo", "").strip().upper() == "SI"]
    plan = activos[0] if activos else (planes[0] if planes else None)
    if not plan:
        print("La pestaña Planes está vacía.")
        return

    print(f"\nPlan: {plan.get('nombre')}  ({plan.get('inicio')} a {plan.get('fin')})")
    print(f"Pestañas leídas: {len(planes)} planes, {len(tareas)} tareas en total\n")

    semana1 = [
        t for t in tareas
        if t.get("plan_id", "").strip() == plan.get("id", "").strip()
        and numero(t.get("semana")) == 1
    ]
    semana1.sort(key=lambda t: numero(t.get("orden"), 999))

    print(f"Semana 1: {len(semana1)} tareas")
    print("-" * 60)
    for t in semana1:
        print(f"  [{t.get('estado', ''):9}] {t.get('titulo', '')}  ({frecuencia_texto(t)})")
    print("-" * 60)
    print("Conexión con Google Sheets funcionando.")


if __name__ == "__main__":
    main()
