"""Inicio de sesión con Google (OAuth de aplicación de escritorio).

La primera vez abre el navegador para que autorices el acceso.
Después guarda token.json y lo reutiliza, renovándolo solo cuando vence.
"""
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

CARPETA = Path(__file__).resolve().parent.parent
CREDENCIALES = CARPETA / "credentials.json"
TOKEN = CARPETA / "token.json"

# Permisos: leer y escribir hojas de cálculo, y crear o editar eventos del calendario.
PERMISOS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar.events",
]


def obtener_credenciales():
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), PERMISOS)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # el token ya no sirve: se vuelve a pedir autorización

    if not creds or not creds.valid:
        if not CREDENCIALES.exists():
            raise FileNotFoundError(
                f"No encuentro credentials.json en {CARPETA}. Descárgalo de Google Cloud."
            )
        flujo = InstalledAppFlow.from_client_secrets_file(str(CREDENCIALES), PERMISOS)
        print("Se abrirá el navegador para que autorices el acceso a Google...")
        creds = flujo.run_local_server(port=0, open_browser=True)

    TOKEN.write_text(creds.to_json(), encoding="utf-8")
    return creds


def servicio_sheets():
    return build("sheets", "v4", credentials=obtener_credenciales(), cache_discovery=False)


def servicio_calendar():
    return build("calendar", "v3", credentials=obtener_credenciales(), cache_discovery=False)
