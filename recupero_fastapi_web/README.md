# Recupero materie prime strategiche — FastAPI + Postgres

Applicazione completa: database Postgres persistente + API REST (FastAPI) +
dashboard web con **un unico schema del processo cliccabile**, da tre punti
di partenza possibili (impianto, dati manuali, o materiale già acquistato)
fino ai prodotti finali, passando per un numero variabile di livelli di
lavorazione degli intermedi. Testata end-to-end prima di ogni consegna.

> **Se stai aggiornando da una versione precedente**: lo schema è cambiato
> profondamente (bilancio di massa a due stadi con conversione
> stechiometrica, tabella `db_intermedi_composizione` nuova, `db_prodotti`
> con 3 colonne nuove, "sottoprodotto" rinominato "intermedio" ovunque) —
> non è compatibile con un database delle versioni precedenti. Vanno
> rieseguiti `01_schema.sql` e `02_seed_data.sql` da zero (vedi "Per
> ricreare il database da zero" più sotto). Se avevi già modificato i dati,
> esportali prima in Excel dalla dashboard.

## Il modello economico in breve

```
Impianto --[macroprocesso]--> Macrocomponente (sempre scomposto)
         --[processo, se attivato]--> Prodotto (terminale)
                                       e/o
                                       Intermedio --[sottoprocesso]--> Prodotto
                                                                        e/o
                                                                        Intermedio --[...]--> ...
```

- **Macroprocesso**: trasforma l'impianto nei suoi macrocomponenti. Più
  macroprocessi alternativi per lo stesso macrocomponente sono possibili
  (es. le pale eoliche: "smontaggio e trasporto" / "solo disassemblaggio" /
  "taglio in sito") — si scelgono con un menu direttamente nello schema.
- **Macrocomponente**: sempre scomposto. Puoi venderlo così com'è, oppure
  attivarlo e scegliere un **processo**.
- **Processo**: applicato a un macrocomponente attivato. La sua uscita può
  essere un **prodotto** (terminale, venduto al prezzo corrente) o un
  **intermedio** (es. le celle di una BESS trasformate in black mass, "BM").
- **Intermedio**: può essere venduto as-is oppure lavorato oltre con un
  **sottoprocesso** — che a sua volta produce prodotti e/o altri intermedi,
  **ricorsivamente, a profondità qualsiasi**, finché ogni ramo non termina
  in un prodotto.

**Filosofia dei prezzi**: ogni prodotto, intermedio e macrocomponente
venduto as-is ha un prezzo di listino nel database, **usato automaticamente
fin da subito** — l'analisi economica è sempre attiva, non serve impostare
nulla. Cliccando su una card puoi rivalutare quel prezzo specifico: dopo la
conferma, l'intero calcolo si aggiorna. Le card con un prezzo rivalutato
dall'utente hanno un **bordo dorato** per distinguerle da quelle a prezzo di
listino.

**Bilanci di massa — a due stadi, sempre**: quando un prodotto (elemento o
composto) ha un "elemento di confronto" con un contenuto noto per l'input in
corso — in `db_macro` se l'input è un macrocomponente, in
`db_intermedi_composizione` se l'input è un intermedio (es. BM, MHP) — si
applica il bilancio a due stadi:

```
massa_elemento_in_ingresso = massa_input × %contenuto
massa_elemento_recuperata  = massa_elemento_in_ingresso × %efficienza (recupero_pct)
massa_prodotto             = massa_elemento_recuperata / peso_molare_elemento
                              / parametro_equivalenza × peso_molare_prodotto
```

Il prodotto può essere l'elemento stesso (nessuna conversione: parametro di
equivalenza 1) oppure un composto (es. LiOH, CoSO₄, convertito via masse
molari). Se il prodotto non ha un contenuto noto per quell'input (es. un
materiale strutturale come il rame nella cablatura), o l'uscita è un altro
intermedio (una miscela non ha una formula chimica univoca), si ricade sul
modello diretto: `massa_uscita = massa_input × %resa`.

**"Elemento non estratto"**: per ogni elemento tracciato (con un contenuto
noto) non completamente recuperato dalle uscite elencate, una card
tratteggiata mostra quanto ne resta nel residuo (massa contenuta − massa
recuperata) — un valore per ciascun elemento, non più un unico complemento
al 100% della massa in ingresso.

## Le 9 tabelle

| Tabella | Contenuto |
|---|---|
| `db_impianti` | Anagrafica: tipologia, sotto tecnologia, potenza, anni, ubicazione |
| `db_prodotti` | Materiali terminali: elementi puri e composti, con peso molare, elemento di confronto e parametro di equivalenza per la conversione stechiometrica |
| `db_macro` | Contenuto elementare per macrocomponente (dato di ingresso al bilancio a due stadi) |
| `db_intermedi_composizione` | Contenuto elementare per intermedio (es. BM, MHP) — stessa funzione di `db_macro` ma per un intermedio |
| `db_macro_processi` | Macroprocessi che trasformano l'impianto in un macrocomponente (capex/opex/prezzo di vendita) |
| `db_processi` | Processi applicati a un macrocomponente: uscita prodotto o intermedio |
| `db_intermedi` | Materiali intermedi (es. BM, MHP): vendibili o lavorabili oltre |
| `db_sottoprocessi` | Lavorazioni applicate a un intermedio: uscita prodotto o altro intermedio (catena ricorsiva) |
| `db_indici_rivalutazione` | Indici (es. ISTAT) per rivalutare i costi all'anno di dismissione |

## Struttura del progetto

```
recupero_fastapi/
├── docker-compose.yml       # Postgres + API in un solo "docker compose up"
├── Dockerfile                # immagine dell'API
├── .env.example               # solo se avvii l'API senza Docker
├── requirements.txt
├── db/
│   ├── 01_schema.sql           # le 9 tabelle
│   ├── 02_seed_data.sql        # dati di riferimento (generato da convert_reference_xlsx.py)
│   ├── convert_reference_xlsx.py  # converte un file Excel di riferimento in 02_seed_data.sql
│   └── generate_seed.py        # generatore precedente (dati placeholder, non piu' usato per il seed attuale)
├── backend/
│   ├── main.py                  # app FastAPI, monta le route e il frontend
│   ├── db.py                     # connessione Postgres
│   ├── crud.py                    # CRUD generico per le 9 tabelle
│   ├── calc.py                     # filtri a cascata + motore di calcolo ricorsivo
│   ├── schemas.py                   # modelli Pydantic
│   ├── excel_io.py                   # export/import Excel
│   └── routers/
│       ├── tables.py                  # route REST CRUD (generate da crud.TABLES)
│       ├── calcolo.py                  # route filtri + /api/calcolo-impianto
│       └── excel.py                     # /api/export/excel, /api/import/excel
└── frontend/
    └── index.html            # dashboard (fetch verso /api/*, nessun dato incorporato)
```

## 1 · Prerequisiti

- **Docker Desktop** (Windows/Mac) o **Docker Engine + plugin compose** (Linux)
- (Solo se NON usi Docker per l'API) **Python 3.10+**

## 2 · Avvio con Docker (consigliato — un solo comando)

```bash
docker compose up -d --build
```
Alla primissima esecuzione, Postgres carica automaticamente schema e dati da
`db/*.sql`. Apri **http://localhost:8000** per la dashboard, **/docs** per la
documentazione automatica delle API.

Per ripartire da zero (cancella anche i dati):
```bash
docker compose down -v
docker compose up -d --build
```

## 3 · Avvio alternativo senza Docker per l'API (solo Postgres in container)

```bash
docker compose up -d db
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd backend
uvicorn main:app --reload --port 8000
```

### Con Postgres nativo (senza Docker, es. su Windows con Anaconda)

```bat
psql -h localhost -U tuo_utente_postgres -c "CREATE USER recupero_user WITH PASSWORD 'recupero_pass';"
psql -h localhost -U tuo_utente_postgres -c "CREATE DATABASE recupero_materie OWNER recupero_user;"
psql -h localhost -U recupero_user -d recupero_materie -f db\01_schema.sql
psql -h localhost -U recupero_user -d recupero_materie -f db\02_seed_data.sql
```
Poi installa le dipendenze e avvia `uvicorn` come sopra.

**Per ricreare il database da zero:**
```bat
psql -h localhost -U tuo_utente_postgres -c "DROP DATABASE recupero_materie;"
psql -h localhost -U tuo_utente_postgres -c "CREATE DATABASE recupero_materie OWNER recupero_user;"
psql -h localhost -U recupero_user -d recupero_materie -f db\01_schema.sql
psql -h localhost -U recupero_user -d recupero_materie -f db\02_seed_data.sql
```

## Cosa puoi fare nella dashboard

- **Calcolo economico**, tre punti di partenza:
  - **Da impianto**: scegli un impianto esistente (potenza e anno di
    dismissione precompilati).
  - **Manuale**: imposta tu tipologia/sotto tecnologia, potenza e anno di
    dismissione, come se stessi valutando un impianto ipotetico.
  - **Materiale acquistato**: parti direttamente da un **macrocomponente**
    o da un **intermedio** già separato (nessun impianto coinvolto) —
    indichi la quantità in ingresso in tonnellate, e il costo di acquisto è
    calcolato automaticamente al prezzo di vendita già presente nel
    database (modificabile cliccando sulla card, come ogni altro prezzo).
    Da lì in poi la catena di lavorazione è identica alle altre due
    modalità: scegli il processo/sottoprocesso direttamente sulla card,
    ogni intermedio generato può essere lavorato oltre con "Trasforma ▸",
    a qualsiasi profondità.

  In tutte e tre le modalità, al centro **un unico schema cliccabile**
  guida dal punto di partenza ai prodotti finali:
  - ogni **macrocomponente** è una card cliccabile che mostra la massa;
    attivandola scegli il processo da applicare;
  - se il processo produce un **intermedio**, la card mostra quantità,
    prezzo corrente e ricavo — con un pulsante "Trasforma ▸" per lavorarlo
    oltre con un sottoprocesso, ripetibile a qualsiasi profondità;
  - ogni card di prodotto/intermedio/macrocomponente (o del materiale
    acquistato, nella terza modalità) è cliccabile per **rivalutarne il
    prezzo**: parte dal valore di listino, tu lo modifichi e confermi, il
    calcolo si aggiorna subito. Le card rivalutate hanno un bordo dorato.
  - dopo ogni processo o sottoprocesso, per ciascun elemento tracciato (con
    un contenuto noto) non completamente recuperato, una card tratteggiata
    mostra l'**elemento non estratto** (massa contenuta − massa recuperata)
    — ogni gruppo di uscite è racchiuso in un riquadro etichettato con la
    tecnica che lo ha prodotto, per non confondere i livelli della catena.
  - **Materiale recuperato** (sotto lo schema) aggrega tutti i prodotti
    finali della catena, sempre prezzati; **Analisi economica** (in fondo)
    mostra massa, costo, ricavo e margine, sempre calcolati.
- **Impianti / Prodotti / Macro componenti / Composizione intermedi / Macro
  processi / Processi / Intermedi / Sottoprocessi / Indici rivalutazione**:
  le 9 tabelle modificabili nel browser. Ogni modifica di cella salva
  subito su Postgres (`PUT`); la riga in fondo evidenziata aggiunge un
  nuovo record (`POST`); l'icona ✕ elimina (`DELETE`).
- **⬇ Esporta Excel / ⬆ Importa Excel / 🗑 Cancella tutto** (header):
  - **Esporta**: tutte le tabelle in un unico file `.xlsx`, un foglio per tabella.
  - **Importa**: prima scegli la modalità — **Aggiungi/Aggiorna** (le righe
    con la stessa chiave vengono aggiornate, le altre aggiunte in coda,
    nessuna cancellazione) oppure **Sostituisci tutto** (cancella prima
    tutte le righe di tutte le tabelle, poi importa il file da zero). In
    entrambi i casi vedi sempre un'**anteprima** (righe create/aggiornate/
    scartate) prima di scrivere davvero su Postgres.
  - **Cancella tutto**: elimina irreversibilmente tutte le righe di tutte le
    9 tabelle (lo schema resta intatto). Richiede di digitare `CANCELLA` per
    confermare — usalo per ripartire da zero prima di un nuovo import, o per
    svuotare un database di prova.

## Note tecniche

- **Integrità referenziale**: `db_processi`/`db_sottoprocessi` referenziano
  `db_prodotti.prodotto` e/o `db_intermedi.intermedio`; `db_prodotti` ha
  anche una FK verso se stessa (`elemento_confronto`). Eliminare un record
  ancora referenziato fallisce con un errore chiaro (409) invece di
  corrompere i dati.
- **Chiavi**: `db_processi` e `db_sottoprocessi` usano una chiave numerica
  auto-incrementale (`id`) perché una stessa "riga logica" di processo può
  avere più uscite (una riga per prodotto/intermedio generato, raggruppate
  dallo stesso `id_processo`/`id_sottoprocesso`).
- **API REST**: ogni tabella ha `GET/POST /api/{tabella}` e
  `PUT/DELETE /api/{tabella}/{chiave}`. Vedi `/docs` per lo schema completo.
- **Calcolo**: `POST /api/calcolo-impianto` accetta tipologia, sotto
  tecnologia, potenza, anno di dismissione, indice costi e la lista dei
  macrocomponenti con le scelte fatte (processo, eventuali sottoprocessi a
  catena, eventuali prezzi rivalutati); restituisce l'intero albero calcolato
  con massa, costo e ricavo a ogni livello. `POST /api/calcolo-da-macrocomponente`
  e `POST /api/calcolo-da-intermedio` fanno lo stesso a partire da una
  quantità in tonnellate acquistata direttamente (modalità "Materiale
  acquistato"), aggiungendo il costo di acquisto al totale.
- **Aggiungere un nuovo macroprocesso, processo o sottoprocesso**: dalle
  rispettive schermate CRUD, aggiungi una riga con la stessa combinazione
  tipologia/sotto tecnologia/macrocomponente (o lo stesso intermedio di
  ingresso per i sottoprocessi). Compare automaticamente nello schema,
  nessuna modifica al codice necessaria. Se un'uscita è un prodotto
  composto (non un elemento), assicurati che in `db_prodotti` abbia
  `elemento_confronto`/`peso_molare`/`parametro_equivalenza` corretti e che
  quell'elemento abbia un contenuto noto in `db_macro` (o
  `db_intermedi_composizione`) per l'input in questione — altrimenti il
  prodotto ricade sul modello diretto invece che sulla conversione
  stechiometrica.

## Problemi comuni

| Sintomo | Causa probabile |
|---|---|
| Dashboard mostra "● API non raggiungibile" | Il container `api` non è avviato, o hai aperto il file HTML direttamente invece di `http://localhost:8000` |
| Dashboard mostra "● Database non raggiungibile" | Postgres non ancora pronto: `docker compose ps`, oppure con Postgres nativo verifica il servizio in "Servizi" di Windows |
| `relation "recupero_materie.db_impianti" non esiste` | Lo schema non è stato caricato: riesegui `01_schema.sql` (controlla l'output riga per riga per eventuali errori) |
| `docker compose up` non ricarica i dati aggiornati | Il volume `pgdata` esiste già: i file in `db/` girano solo alla primissima creazione. Usa `docker compose down -v` |
| Porta 8000 o 5432 già in uso | Cambia le porte esposte nel `docker-compose.yml`, o usa una porta diversa con `psql -p` |
