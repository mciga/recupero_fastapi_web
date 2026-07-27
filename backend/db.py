"""Connessione a Postgres. Legge le credenziali da variabili d'ambiente o da
un file .env nella cartella del progetto."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

try:
    from dotenv import load_dotenv
    # db.py è in backend/, .env è nella root → parent.parent
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

SCHEMA = "recupero_materie"


def get_engine() -> Engine:
    # Render fornisce DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        return create_engine(db_url, pool_pre_ping=True)

    # Fallback locale
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "recupero_materie")
    user = os.getenv("PGUSER", "recupero_user")
    password = os.getenv("PGPASSWORD", "recupero_pass")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)


ENGINE = get_engine()
