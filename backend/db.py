"""Connessione a Postgres. Legge le credenziali da variabili d'ambiente o da
un file .env nella cartella del progetto (stesso schema del docker-compose)."""
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# schema Postgres con le tabelle: "recupero_materie" di default; la versione di novembre usa
# "recupero_novembre" (impostato nel file .env) per non toccare i dati della versione precedente
SCHEMA = os.getenv("PGSCHEMA", "recupero_materie")


def get_engine() -> Engine:
    # online (Render + Neon): stringa di connessione di Neon nella variabile DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # i provider danno postgres:// o postgresql://, SQLAlchemy vuole postgresql+psycopg2://
        for prefisso in ("postgres://", "postgresql://"):
            if db_url.startswith(prefisso):
                db_url = "postgresql+psycopg2://" + db_url[len(prefisso):]
        # Neon spegne il database quando non e' usato: pool_pre_ping scarta le connessioni chiuse
        return create_engine(db_url, pool_pre_ping=True, pool_recycle=240)

    # in locale: parametri del file .env
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "recupero_materie")
    user = os.getenv("PGUSER", "recupero_user")
    password = os.getenv("PGPASSWORD", "recupero_pass")
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}"
    return create_engine(url, pool_pre_ping=True)


ENGINE = get_engine()
