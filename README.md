# MACTEE – recupero materie prime strategiche (versione di novembre 2026)

Dashboard web (FastAPI + pagina HTML) per il calcolo del recupero di materie prime
dalla dismissione degli impianti (eolico, fotovoltaico, BESS).

## Online

- **Vercel** esegue il backend e serve la dashboard (`vercel.json` + `api/index.py`);
  in alternativa **Render** (`render.yaml`).
- **Neon** ospita il database PostgreSQL (schema `recupero_novembre`).
- I dati **non** sono in questo repository: si caricano su Neon da una copia del database locale.

Variabili d'ambiente su Render:

| Variabile | Valore |
|---|---|
| `DATABASE_URL` | stringa di connessione di Neon (`postgresql://…?sslmode=require`) |
| `PGSCHEMA` | `recupero_novembre` |
| `APP_PASSWORD` | password di accesso alla dashboard |
| `APP_USER` | nome utente di accesso (predefinito `mactee`) |

Comando di avvio: `uvicorn main:app --app-dir backend --host 0.0.0.0 --port $PORT`

## In locale

Senza `DATABASE_URL` il backend usa `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
e `PGSCHEMA` del file `.env` (vedi `.env.example`); senza `APP_PASSWORD` non chiede la password.

```
uvicorn main:app --app-dir backend --reload --port 8000
```
