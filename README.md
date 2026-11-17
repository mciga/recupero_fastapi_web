# MACTEE – recupero materie prime strategiche (versione di novembre 2026)

Dashboard web (FastAPI + pagina HTML) per il calcolo del recupero di materie prime
dalla dismissione degli impianti (eolico, fotovoltaico, BESS).

## Online

- **Vercel** esegue il backend e serve la dashboard (`app.py`, riconosciuto da Vercel come app FastAPI,
  e `vercel.json`); a ogni push su `main` Vercel rifà il deploy.
- **Neon** ospita il database PostgreSQL (schema `recupero_novembre`).
- I dati **non** sono in questo repository: si caricano su Neon da una copia del database locale.

Variabili d'ambiente su Vercel:

| Variabile | Valore |
|---|---|
| `DATABASE_URL` | stringa di connessione di Neon (`postgresql://…?sslmode=require`) |
| `PGSCHEMA` | `recupero_novembre` |
| `APP_PASSWORD` | password di accesso alla dashboard |
| `APP_USER` | nome utente di accesso (predefinito `mactee`) |

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

Migrazione v10.2 (opex specifico per materiale, colonna `opex_spec` in `db_processi_trasformazioni`):
`db/migrazione_v10_2_opex_spec.sql`. Se `opex_spec` (EUR/t) è compilato su una riga, la massa di quel
materiale (o di quel materiale nell'assieme indicato) paga `opex_spec` al posto dell'opex del processo:
opex = (massa trattata − massa dei materiali con opex_spec) × opex_eur_ton + Σ massa × opex_spec.
Il capex non cambia. Se un materiale ha più righe basta compilarne una; con valori diversi vale la prima riga.
I sottoprocessi non hanno questa colonna.

Migrazione v10.3 (capex annualizzato con il fattore di recupero del capitale):
`db/migrazione_v10_3_capex_crf.sql` aggiunge a `db_processi` e `db_sottoprocessi` le colonne
`tasso_sconto` (predefinito 0,08) e `taglia_minima_t_anno` (soglia economica, vuota = nessun avviso);
`db/dati_v10_3_capex.sql` (solo in locale, come gli altri dati) carica i valori nuovi. Il calcolo (`_capex_taglia` in `backend/calc.py`):

```
capex impianto   = capex_eur_ton × taglia_rif × (taglia / taglia_rif)^esponente × rivalutazione
                   (senza taglia di riferimento: capex_eur_ton × taglia)
quota d'uso      = (massa trattata / taglia) × CRF,   CRF = i (1 + i)^n / [(1 + i)^n − 1]
capex attribuito = capex impianto × quota d'uso
```

`capex_eur_ton` è un'intensità di investimento (€ per t/anno di capacità). Se la taglia non è indicata
si usa la taglia di riferimento (impianto unico che riceve il flusso di più impianti); senza taglia di
riferimento, l'impianto che tratta la massa in un anno. Il calcolo segnala le taglie sotto la soglia
economica e i tempi di trattamento oltre la vita utile.

Valori caricati: BESS_LFP_IDROMET P1-P6 dalla nota sul capex dei processi LFP del 17/11/2026
(Tabella 1, base "celle", 20 000 t/anno, soglia 6 500 t/anno); eolico, fotovoltaico e sottoprocessi
riportati dai valori precedenti (costi per t trattata) dividendo per il CRF (8 %, 15 anni = 0,1168),
con taglie di riferimento di eolico e fotovoltaico da verificare.

Migrazione v10.4 (gate fee): `db/migrazione_v10_4_gate_fee.sql` aggiunge a `db_processi` la colonna
`gate_fee_eur_ton` (€ per t di macrocomponente consegnato, con segno: positivo se il proprietario paga
l'impianto di riciclo, negativo se l'impianto paga il materiale, predefinito 0). Dalla v10.4 capex, opex e gate
fee si calcolano sulla massa totale del macrocomponente in ingresso, e il margine è
ricavi dai prodotti + gate fee − costi. Nella pagina del calcolo il gate fee si modifica al clic per la singola
simulazione. `db/dati_v10_4_bess_rack.sql` (solo in locale) porta i processi BESS P1-P6 alla Tabella 2 della
nota sul capex (base "ingresso al rack", 24 240 t/anno).

Import Excel: le celle con testo vuoto o spazi valgono come celle vuote e, nei campi numerici, i numeri scritti
come testo (anche all'italiana, "7,5" o "1.234,5") diventano numeri.

I fogli `macro`, `processi_trasformazioni` e `sottoprocessi_trasformazioni` non hanno la colonna `id` (l'id
seriale resta solo nel database e nella dashboard; se nel file c'è, l'import lo ignora). Ogni riga si riconosce
dai campi che la identificano:

| Foglio | Campi chiave |
|---|---|
| `macro` | id_macro, macro_componente, assieme_dettaglio, material_id |
| `processi_trasformazioni` | id_processo, material_id, assieme_dettaglio, tipo_output, prodotto, intermedio_output, scarto |
| `sottoprocessi_trasformazioni` | id_sottoprocesso, tipo_output, prodotto, intermedio_output, scarto |

Una riga che corrisponde a una riga esistente la aggiorna (solo se cambia qualcosa), una riga nuova riceve l'id
successivo; righe ripetute nel foglio: vale l'ultima. Per cambiare un campo chiave (es. il prodotto di un'uscita)
si cancella la riga vecchia e se ne crea una nuova. La migrazione v10.5 (`db/migrazione_v10_5_trasformazioni_uniche.sql`)
impedisce nel database due trasformazioni con gli stessi campi chiave.

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
