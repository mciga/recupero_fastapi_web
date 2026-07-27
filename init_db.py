import os
from sqlalchemy import create_engine, text

db_url = os.environ["DATABASE_URL"].replace("postgres://", "postgresql://", 1)
engine = create_engine(db_url)

def run_sql_file(path):
    with open(path) as f:
        content = f.read()
    # Rimuove i commenti SQL (righe che iniziano con --)
    lines = [line for line in content.splitlines() if not line.strip().startswith("--")]
    sql = "\n".join(lines)
    # Splitta per ; ed esegue ogni istruzione
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt + ";"))
    print(f"✓ Eseguito {path}")

if __name__ == "__main__":
    run_sql_file("db/01_schema.sql")
    run_sql_file("db/02_seed_data.sql")
    print("Database inizializzato con successo.")
