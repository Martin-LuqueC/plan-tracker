"""Lanzador del Plan Tracker (lo usan los archivos .cmd de la carpeta del proyecto).

  pythonw app/lanzador.py            abre Plan Tracker (arranca el servidor si hace falta)
  pythonw app/lanzador.py --cerrar   apaga el servidor
  pythonw app/lanzador.py --inicio   activa o desactiva que se abra al iniciar Windows
  pythonw app/lanzador.py --escritorio  crea un acceso directo en el escritorio

Usa pythonw (sin ventana de consola), así que los avisos se muestran en un cuadro de mensaje.
"""
import ctypes
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CARPETA = Path(__file__).resolve().parent.parent
PYTHONW = CARPETA / ".venv" / "Scripts" / "pythonw.exe"
SERVIDOR = CARPETA / "app" / "servidor.py"
LANZADOR = Path(__file__).resolve()
ICONO = CARPETA / "icono.ico"
REGISTRO = CARPETA / "plan-tracker.log"
TITULO = "Plan Tracker"
NOMBRE_ACCESO = "Plan Tracker.lnk"
SEGUNDOS_ESPERA = 45

NAVEGADORES = [
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
    Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
]


def aviso(texto, error=False):
    icono = 0x10 if error else 0x40
    ctypes.windll.user32.MessageBoxW(None, texto, TITULO, icono)


def preguntar(texto):
    return ctypes.windll.user32.MessageBoxW(None, texto, TITULO, 0x04 | 0x20) == 6  # Sí / No


def puerto():
    valor = "5050"
    env = CARPETA / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            if linea.strip().startswith("PUERTO="):
                valor = linea.split("=", 1)[1].strip() or valor
    return int(valor)


def servidor_activo(p):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{p}/api/salud", timeout=1.5) as r:
            return json.load(r).get("app") == "plan-tracker"
    except Exception:
        return False


def puerto_ocupado(p):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", p)) == 0


def arrancar_servidor(p):
    registro = open(REGISTRO, "a", encoding="utf-8")
    registro.write(f"\n===== Inicio {time.strftime('%Y-%m-%d %H:%M:%S')} =====\n")
    registro.flush()
    banderas = (subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.CREATE_NO_WINDOW)
    entorno = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    subprocess.Popen([str(PYTHONW), str(SERVIDOR)], cwd=str(CARPETA), stdout=registro,
                     stderr=registro, stdin=subprocess.DEVNULL, env=entorno,
                     creationflags=banderas, close_fds=True)
    limite = time.time() + SEGUNDOS_ESPERA
    while time.time() < limite:
        if servidor_activo(p):
            return True
        time.sleep(0.5)
    return False


def abrir_ventana(p):
    url = f"http://localhost:{p}"
    for navegador in NAVEGADORES:
        if navegador.exists():
            subprocess.Popen([str(navegador), f"--app={url}"], close_fds=True)
            return
    import webbrowser
    webbrowser.open(url)


def abrir():
    p = puerto()
    if not servidor_activo(p):
        if puerto_ocupado(p):
            aviso(f"Otro programa está usando el puerto {p}.\n\n"
                  "Cambia PUERTO en el archivo .env por otro número (por ejemplo 5051) "
                  "y vuelve a abrir Plan Tracker.", error=True)
            return
        if not PYTHONW.exists():
            aviso("No encuentro el entorno de Python (.venv).\n\n"
                  "Revisa el README para prepararlo de nuevo.", error=True)
            return
        if not arrancar_servidor(p):
            aviso("El servidor no arrancó.\n\n"
                  f"Los detalles quedaron en:\n{REGISTRO}", error=True)
            return
    abrir_ventana(p)


def cerrar():
    p = puerto()
    if not servidor_activo(p):
        aviso("Plan Tracker no estaba abierto.")
        return
    try:
        pedido = urllib.request.Request(f"http://127.0.0.1:{p}/api/apagar", data=b"{}", method="POST",
                                        headers={"Content-Type": "application/json"})
        urllib.request.urlopen(pedido, timeout=3).read()
    except Exception:
        pass
    for _ in range(20):
        if not servidor_activo(p):
            aviso("Plan Tracker se cerró.\n\nPuedes cerrar también su ventana de Chrome.")
            return
        time.sleep(0.25)
    aviso("No pude cerrar el servidor. Reinicia la computadora si sigue abierto.", error=True)


def _crear_acceso(destino):
    """Crea un acceso directo .lnk usando el componente de Windows (WScript.Shell)."""
    script = (
        "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:PT_DESTINO);"
        "$s.TargetPath = $env:PT_PYTHONW; $s.Arguments = $env:PT_ARGS;"
        "$s.WorkingDirectory = $env:PT_CARPETA; $s.IconLocation = $env:PT_ICONO;"
        "$s.Description = 'Abre Plan Tracker'; $s.Save()"
    )
    entorno = dict(os.environ, PT_DESTINO=str(destino), PT_PYTHONW=str(PYTHONW),
                   PT_ARGS=f'"{LANZADOR}"', PT_CARPETA=str(CARPETA), PT_ICONO=f"{ICONO},0")
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   env=entorno, check=True, creationflags=subprocess.CREATE_NO_WINDOW)


def carpeta_inicio():
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup"


def alternar_inicio():
    acceso = carpeta_inicio() / NOMBRE_ACCESO
    if acceso.exists():
        if preguntar("Plan Tracker se abre solo al iniciar Windows.\n\n¿Quieres desactivarlo?"):
            acceso.unlink()
            aviso("Listo. Plan Tracker ya no se abrirá solo al iniciar Windows.")
    else:
        if preguntar("¿Quieres que Plan Tracker se abra solo cada vez que inicias Windows?"):
            _crear_acceso(acceso)
            aviso("Listo. Plan Tracker se abrirá solo al iniciar Windows.\n\n"
                  "Para desactivarlo, vuelve a abrir este mismo archivo.")


def crear_escritorio():
    salida = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", "[Environment]::GetFolderPath('Desktop')"],
        capture_output=True, text=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    escritorio = Path(salida.stdout.strip())
    _crear_acceso(escritorio / NOMBRE_ACCESO)
    aviso("Listo. Hay un acceso directo a Plan Tracker en tu escritorio.")


if __name__ == "__main__":
    try:
        orden = sys.argv[1] if len(sys.argv) > 1 else ""
        {"--cerrar": cerrar, "--inicio": alternar_inicio, "--escritorio": crear_escritorio}.get(orden, abrir)()
    except Exception as error:  # con pythonw no hay consola: el error se muestra en un cuadro
        aviso(f"Algo falló:\n\n{error}", error=True)
