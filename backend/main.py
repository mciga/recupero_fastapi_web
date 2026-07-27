"""Entry point dell'applicazione FastAPI.

Avvio locale (sviluppo):  uvicorn main:app --reload --port 8000
Avvio in Docker:          vedi ../Dockerfile e ../docker-compose.yml
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # per gli import "flat" (db, crud, calc, schemas)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import tables, calcolo, excel
from db import ENGINE

app = FastAPI(title="Recupero materie prime strategiche - API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend servito dallo stesso processo: CORS permissivo va bene per uso locale
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tables.router)
app.include_router(calcolo.router)
app.include_router(excel.router)


@app.get("/api/health")
def health():
    try:
        with ENGINE.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "ok", "database": "connesso"}
    except Exception as e:  # noqa: BLE001
        return {"status": "errore", "database": str(e)}


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
