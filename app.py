"""Punto di ingresso per Vercel (riconoscimento automatico di FastAPI: file app.py con la variabile app).
Espone l'app FastAPI di backend/main.py; in locale si usa invece uvicorn main:app --app-dir backend."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from main import app  # noqa: E402,F401
