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

## Processi e sottoprocessi (schema v10)

Dalla v10 ogni processo occupa una sola riga e le sue trasformazioni stanno in una tabella collegata
(relazione 1 → N):

| Tabella | Contenuto |
|---|---|
| `db_processi` | una riga per processo: `id_processo`, tipologia, sotto-tecnologia, macrocomponente, tecnica, capex, opex, fasi, taglia di riferimento, esponente di scala, vita utile |
| `db_processi_trasformazioni` | una riga per uscita di ogni materiale in ingresso: `id_processo`, `material_id`, assieme, tipo di uscita, prodotto/intermedio/scarto, tre rese, reagente |
| `db_sottoprocessi` | una riga per sottoprocesso: intermedio in ingresso, tecnica, costi, taglia |
| `db_sottoprocessi_trasformazioni` | una riga per uscita del sottoprocesso |

Le trasformazioni referenziano la testata con `ON DELETE CASCADE`: eliminando un processo si eliminano
le sue righe. Nella dashboard il pulsante "N righe ▸" apre le trasformazioni di un processo; dopo la
creazione di un processo la finestra si apre da sola. Un processo senza trasformazioni non compare nel calcolo.

Nel file Excel ci sono i fogli `processi`, `processi_trasformazioni`, `sottoprocessi` e
`sottoprocessi_trasformazioni`. I file delle versioni precedenti, con un solo foglio `processi` che ha una
riga per trasformazione, sono ancora accettati: l'import li divide da solo (testata = prima riga di ogni processo).

Migrazione di un database esistente (v9 → v10), in una sola transazione:

```
psql "<connessione>" -v ON_ERROR_STOP=1 -c "SET search_path TO recupero_novembre" -f db/migrazione_v10_processi_testata.sql
```

Migrazione v10.1 (fonte delle coordinate e dell'anno di dismissione in `db_impianti`):
`db/migrazione_v10_1_impianti_fonti.sql`.

## Cruscotto territoriale

Nella sezione Calcolo economico il pulsante "Cruscotto" (tra "Da impianto" e "Intermedio acquistato")
apre il cruscotto del recupero: mappa della Puglia con selezione per provincia, cerchio o rettangolo,
metallo contenuto e recuperabile nel tempo per anno di dismissione, scenari minimo/medio/massimo,
dettaglio per macrocomponente, processo e impianto, esportazione XLSX.

I dati arrivano tutti dal database con `GET /api/cruscotto/dati` (`backend/cruscotto.py`); il calcolo
e i grafici sono in `frontend/cruscotto.js`, con le stesse regole di `MACTEE_Cruscotto_DB.html`. Gli
impianti con `fonte_coordinate = prova` hanno una posizione di prova e sulla mappa hanno il bordo tratteggiato.
`frontend/puglia_province.json`: confini provinciali semplificati (ISTAT); `frontend/vendor/xlsx.full.min.js`:
SheetJS 0.18.5 per l'esportazione, caricato solo quando serve.
