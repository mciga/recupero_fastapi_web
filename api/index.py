"""Punto di ingresso per Vercel: espone l'app FastAPI di backend/main.py.
Tutte le richieste (pagina e /api/...) sono inviate qui da vercel.json."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from main import app  # noqa: E402,F401
