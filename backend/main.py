from sqlalchemy import text
from fastapi import HTTPException
from db import SCHEMA


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
