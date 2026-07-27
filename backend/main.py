"""Entry point dell'applicazione FastAPI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import text

from routers import tables, calcolo, excel
from db import ENGINE, SCHEMA

app = FastAPI(title="Recupero materie prime strategiche - API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    except Exception as e:
        return {"status": "errore", "database": str(e)}


def _run_sql_file(rel_path: str):
    path = Path(__file__).resolve().parent.parent / rel_path
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    # Rimuove righe di commento SQL
    lines = [line for line in raw.splitlines() if not line.strip().startswith("--")]
    sql = "\n".join(lines)
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with ENGINE.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt + ";"))
    return {"file": rel_path, "statements": len(statements)}


@app.get("/api/setup")
def setup_database():
    """Inizializza il database (schema + dati seed). Sicuro da chiamare più volte."""
    try:
        with ENGINE.connect() as conn:
            conn.exec_driver_sql(f"SET search_path TO {SCHEMA}")
            conn.execute(text(f"SELECT 1 FROM {SCHEMA}.db_prodotti LIMIT 1"))
            return {"status": "already_initialized", "message": "Database già popolato."}
    except Exception:
        pass  # tabelle non esistenti, procedi con setup
    
    try:
        r1 = _run_sql_file("db/01_schema.sql")
        r2 = _run_sql_file("db/02_seed_data.sql")
        return {"status": "ok", "schema": r1, "seed": r2}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")
