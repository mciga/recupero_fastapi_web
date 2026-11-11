"""Password di accesso alla dashboard (HTTP Basic: il browser mostra la sua finestra
di accesso e poi ricorda le credenziali per tutta la sessione).

Si attiva solo se e' impostata la variabile d'ambiente APP_PASSWORD (su Render);
in locale, senza la variabile, la dashboard resta libera come prima.
Nome utente: variabile APP_USER (predefinito "mactee").
/api/health resta libero per il controllo di Render."""
import base64
import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import Response

LIBERI = {"/api/health"}


def _credenziali_ok(header: str, utente: str, password: str) -> bool:
    if not header.lower().startswith("basic "):
        return False
    try:
        u, _, p = base64.b64decode(header[6:]).decode("utf-8").partition(":")
    except Exception:  # noqa: BLE001
        return False
    return secrets.compare_digest(u.encode(), utente.encode()) & secrets.compare_digest(p.encode(), password.encode())


def proteggi(app: FastAPI) -> None:
    password = os.getenv("APP_PASSWORD")
    if not password:
        return
    utente = os.getenv("APP_USER", "mactee")

    @app.middleware("http")
    async def _controllo_accesso(request: Request, call_next):
        if request.url.path in LIBERI or _credenziali_ok(request.headers.get("authorization", ""), utente, password):
            return await call_next(request)
        return Response("Accesso riservato", status_code=401,
                        headers={"WWW-Authenticate": 'Basic realm="MACTEE", charset="UTF-8"'})
