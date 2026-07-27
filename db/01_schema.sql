-- ============================================================================
-- SCHEMA POSTGRESQL v6 - MODELLO ECONOMICO RECUPERO MATERIE PRIME STRATEGICHE
--
-- Rispetto alla versione precedente:
--  - "sottoprodotto" rinominato "intermedio" ovunque (tabella e colonne):
--    db_sottoprodotti -> db_intermedi, colonna sottoprodotto -> intermedio,
--    sottoprodotto_output -> intermedio_output.
--  - LA CONVERSIONE STECHIOMETRICA VALE SEMPRE: sia un macrocomponente che
--    un intermedio hanno una tabella di composizione elementare (db_macro,
--    db_intermedi_composizione) — un prodotto composto generato in
--    qualunque punto della catena passa dal bilancio a due stadi.
--  - db_prodotti ha 3 colonne nuove per la conversione stechiometrica da
--    elemento a composto: peso_molare, elemento_confronto (FK verso se
--    stessa: l'elemento puro corrispondente), parametro_equivalenza
--    (quanti atomi dell'elemento di confronto per formula del composto).
--
-- BILANCIO DI MASSA A DUE STADI (da un macrocomponente O un intermedio, a
-- un prodotto composto):
--   massa_elemento_in_ingresso = massa_input x %contenuto (db_macro o db_intermedi_composizione)
--   massa_elemento_recuperata  = massa_elemento_in_ingresso x %efficienza (recupero_pct)
--   massa_composto             = massa_elemento_recuperata / peso_molare_elemento
--                                 / parametro_equivalenza x peso_molare_composto
-- Se il prodotto in uscita non ha un elemento di confronto con un contenuto
-- noto per quel macrocomponente/intermedio, si ricade sul modello diretto:
-- massa_uscita = massa_in x %resa (usato sempre per generare un altro
-- INTERMEDIO, che non ha una formula chimica univoca).
--
-- "Elemento non estratto" (ex "scarto"): per ogni elemento tracciato (con
-- contenuto noto) non completamente recuperato, si espone la massa
-- dell'elemento rimasta nel residuo: massa_contenuta - massa_recuperata.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS recupero_materie;
SET search_path TO recupero_materie;

-- ----------------------------------------------------------------------------
-- 1) DB_IMPIANTI - anagrafica degli impianti (invariata)
-- ----------------------------------------------------------------------------
CREATE TABLE db_impianti (
    id_imp              VARCHAR(20)   PRIMARY KEY,
    tipologia           VARCHAR(30)   NOT NULL,
    sotto_tecnologia    VARCHAR(30)   NOT NULL,
    potenza_mw          NUMERIC(10,2) NOT NULL CHECK (potenza_mw > 0),
    anno_installazione  SMALLINT      NOT NULL,
    anno_dismissione    SMALLINT      NOT NULL CHECK (anno_dismissione > anno_installazione),
    regione             VARCHAR(50),
    provincia           VARCHAR(50),
    lat                 NUMERIC(8,5),
    lon                 NUMERIC(8,5)
);
CREATE INDEX idx_impianti_tipologia ON db_impianti (tipologia, sotto_tecnologia);

-- ----------------------------------------------------------------------------
-- 2) DB_PRODOTTI - materiali terminali: sia elementi chimici puri (Fe, Cu,
--    Li...) sia composti (solfato di cobalto, idrossido di litio...).
--    Per un elemento puro, elemento_confronto punta a se stesso e
--    parametro_equivalenza = 1 (nessuna conversione). Per un composto,
--    elemento_confronto e' l'elemento la cui massa recuperata (db_macro x
--    db_processi) viene convertita in massa del composto via le masse
--    molari e il parametro_equivalenza (numero di atomi dell'elemento per
--    formula del composto: es. Li2CO3 -> 2).
-- ----------------------------------------------------------------------------
CREATE TABLE db_prodotti (
    prodotto                  VARCHAR(30)   PRIMARY KEY,
    nome                       VARCHAR(60)   NOT NULL,
    categoria                  VARCHAR(20)   NOT NULL,      -- strategico / critico / utile
    peso_molare                NUMERIC(10,3) NOT NULL CHECK (peso_molare > 0),
    elemento_confronto          VARCHAR(30)   NOT NULL REFERENCES db_prodotti(prodotto),
    parametro_equivalenza       NUMERIC(6,2)  NOT NULL DEFAULT 1 CHECK (parametro_equivalenza > 0),
    prezzo_attuale_eur_kg      NUMERIC(12,4) NOT NULL CHECK (prezzo_attuale_eur_kg >= 0),
    proiezione_prezzo_p1       NUMERIC(6,4)  NOT NULL,
    proiezione_prezzo_p2       NUMERIC(6,4)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- 3) DB_MACRO - composizione elementare dei macrocomponenti: quanto di ogni
--    prodotto ELEMENTARE (mai un composto) e' contenuto, come range min/max.
--    Piu' righe per lo stesso macrocomponente = piu' elementi contenuti.
-- ----------------------------------------------------------------------------
CREATE TABLE db_macro (
    id_macro           VARCHAR(30)   NOT NULL,
    tipologia          VARCHAR(30)   NOT NULL,
    sotto_tecnologia   VARCHAR(30)   NOT NULL,
    macro_componente   VARCHAR(50)   NOT NULL,
    massa_kg_per_mw    NUMERIC(12,2) NOT NULL CHECK (massa_kg_per_mw > 0),
    prodotto           VARCHAR(30)   NOT NULL REFERENCES db_prodotti(prodotto),
    pct_contenuto_min  NUMERIC(7,5)  NOT NULL CHECK (pct_contenuto_min > 0 AND pct_contenuto_min <= 1),
    pct_contenuto_max  NUMERIC(7,5)  NOT NULL CHECK (pct_contenuto_max > 0 AND pct_contenuto_max <= 1),
    PRIMARY KEY (id_macro, prodotto),
    CONSTRAINT chk_macro_range CHECK (pct_contenuto_max >= pct_contenuto_min)
);
CREATE INDEX idx_macro_filtro ON db_macro (tipologia, sotto_tecnologia, macro_componente);

-- ----------------------------------------------------------------------------
-- 4) DB_MACRO_PROCESSI - macroprocessi che trasformano l'impianto nei suoi
--    macrocomponenti. Keyed direttamente su tipologia/sotto_tecnologia/
--    macro_componente (nessuno scenario): piu' righe per lo stesso
--    macrocomponente = piu' macroprocessi alternativi selezionabili.
-- ----------------------------------------------------------------------------
CREATE TABLE db_macro_processi (
    id_processo_macro     VARCHAR(30)   PRIMARY KEY,
    tipologia              VARCHAR(30)   NOT NULL,
    sotto_tecnologia       VARCHAR(30)   NOT NULL,
    macro_componente       VARCHAR(50)   NOT NULL,
    tecnica                 VARCHAR(60)   NOT NULL,
    capex_eur_ton           NUMERIC(12,2) NOT NULL CHECK (capex_eur_ton >= 0),
    opex_eur_ton            NUMERIC(12,2) NOT NULL CHECK (opex_eur_ton >= 0),
    -- prezzo di vendita del macrocomponente COME MATERIALE GREZZO, se non
    -- viene trattato con un processo
    prezzo_vendita_eur_kg     NUMERIC(12,4) NOT NULL DEFAULT 0 CHECK (prezzo_vendita_eur_kg >= 0),
    proiezione_prezzo_p1      NUMERIC(6,4)  NOT NULL DEFAULT 0,
    proiezione_prezzo_p2      NUMERIC(6,4)  NOT NULL DEFAULT 0,
    descrizione_fasi        TEXT
);
CREATE INDEX idx_macro_processi_filtro ON db_macro_processi (tipologia, sotto_tecnologia, macro_componente);

-- ----------------------------------------------------------------------------
-- 5) DB_PROCESSI - processi applicati a un macrocomponente. L'uscita puo'
--    essere un PRODOTTO (elemento o composto, terminale) oppure un
--    INTERMEDIO (puo' essere venduto o lavorato oltre con un sottoprocesso).
--    recupero_pct e' l'efficienza di recupero: per un prodotto il cui
--    elemento di confronto ha un contenuto noto in db_macro per questo
--    macrocomponente, si applica alla massa di quell'elemento contenuta
--    (poi convertita in massa del composto); altrimenti alla massa totale
--    del macrocomponente, direttamente. Per un intermedio, sempre diretta.
-- ----------------------------------------------------------------------------
CREATE TABLE db_processi (
    id                    SERIAL        PRIMARY KEY,
    id_processo           VARCHAR(30)   NOT NULL,   -- raggruppa le righe dello stesso processo (piu' uscite)
    tipologia             VARCHAR(30)   NOT NULL,
    sotto_tecnologia      VARCHAR(30)   NOT NULL,
    macro_componente      VARCHAR(50)   NOT NULL,
    tecnica                VARCHAR(60)   NOT NULL,
    capex_eur_ton          NUMERIC(12,2) NOT NULL CHECK (capex_eur_ton >= 0),
    opex_eur_ton           NUMERIC(12,2) NOT NULL CHECK (opex_eur_ton >= 0),
    tipo_output            VARCHAR(15)   NOT NULL CHECK (tipo_output IN ('prodotto','intermedio')),
    prodotto               VARCHAR(30)   REFERENCES db_prodotti(prodotto),
    intermedio_output      VARCHAR(30),   -- FK aggiunta dopo la creazione di db_intermedi
    recupero_pct_min       NUMERIC(6,5)  NOT NULL CHECK (recupero_pct_min > 0 AND recupero_pct_min <= 1),
    recupero_pct_max       NUMERIC(6,5)  NOT NULL CHECK (recupero_pct_max > 0 AND recupero_pct_max <= 1),
    descrizione_fasi       TEXT,
    CONSTRAINT chk_processi_range CHECK (recupero_pct_max >= recupero_pct_min),
    CONSTRAINT chk_processi_output CHECK (
        (tipo_output = 'prodotto' AND prodotto IS NOT NULL AND intermedio_output IS NULL) OR
        (tipo_output = 'intermedio' AND intermedio_output IS NOT NULL AND prodotto IS NULL)
    )
);
CREATE INDEX idx_processi_filtro ON db_processi (tipologia, sotto_tecnologia, macro_componente);
CREATE INDEX idx_processi_id ON db_processi (id_processo);

-- ----------------------------------------------------------------------------
-- 6) DB_INDICI_RIVALUTAZIONE - indici per rivalutare i costi (capex/opex di
--    entrambi gli stadi) all'anno di dismissione.
-- ----------------------------------------------------------------------------
CREATE TABLE db_indici_rivalutazione (
    id_indice    VARCHAR(20)   PRIMARY KEY,
    nome         VARCHAR(100)  NOT NULL,
    tasso_annuo  NUMERIC(6,4)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- 7) DB_INTERMEDI (ex db_sottoprodotti) - materiali intermedi (BM, MHP...):
--    possono essere venduti as-is oppure lavorati oltre con un sottoprocesso.
--    La loro composizione elementare (se un sottoprocesso genera un prodotto
--    composto a partire da questo intermedio) e' in db_intermedi_composizione.
-- ----------------------------------------------------------------------------
CREATE TABLE db_intermedi (
    intermedio                 VARCHAR(30)   PRIMARY KEY,
    nome                       VARCHAR(60)   NOT NULL,
    prezzo_attuale_eur_kg      NUMERIC(12,4) NOT NULL CHECK (prezzo_attuale_eur_kg >= 0),
    proiezione_prezzo_p1       NUMERIC(6,4)  NOT NULL,
    proiezione_prezzo_p2       NUMERIC(6,4)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- 7bis) DB_INTERMEDI_COMPOSIZIONE - composizione elementare di un intermedio
--    (analoga a db_macro, ma per un intermedio invece che un macrocomponente):
--    serve perche' la conversione stechiometrica valga SEMPRE, anche quando
--    un sottoprocesso trasforma un intermedio in un prodotto composto (es.
--    BM -> CoSO4). Un intermedio senza righe qui semplicemente non alimenta
--    nessun prodotto a due stadi (es. Elet, cake_metallico: mai ulteriore
--    input di un sottoprocesso in questo database).
-- ----------------------------------------------------------------------------
CREATE TABLE db_intermedi_composizione (
    intermedio          VARCHAR(30)   NOT NULL REFERENCES db_intermedi(intermedio),
    prodotto             VARCHAR(30)   NOT NULL REFERENCES db_prodotti(prodotto),
    pct_contenuto_min    NUMERIC(7,5)  NOT NULL CHECK (pct_contenuto_min > 0 AND pct_contenuto_min <= 1),
    pct_contenuto_max    NUMERIC(7,5)  NOT NULL CHECK (pct_contenuto_max > 0 AND pct_contenuto_max <= 1),
    PRIMARY KEY (intermedio, prodotto),
    CONSTRAINT chk_intermedi_comp_range CHECK (pct_contenuto_max >= pct_contenuto_min)
);

ALTER TABLE db_processi
    ADD CONSTRAINT fk_processi_intermedio FOREIGN KEY (intermedio_output) REFERENCES db_intermedi(intermedio);

-- ----------------------------------------------------------------------------
-- 8) DB_SOTTOPROCESSI - lavorazioni applicate a un intermedio (mai a un
--    macrocomponente: quello e' compito di db_processi). L'ingresso ha
--    quindi una vera FK verso db_intermedi. L'uscita, come in db_processi,
--    puo' essere un PRODOTTO (a due stadi se l'elemento di confronto ha un
--    contenuto noto in db_intermedi_composizione, diretto altrimenti) o un
--    altro INTERMEDIO (sempre diretto: catena ricorsiva a profondita'
--    arbitraria).
-- ----------------------------------------------------------------------------
CREATE TABLE db_sottoprocessi (
    id                    SERIAL        PRIMARY KEY,
    id_sottoprocesso      VARCHAR(30)   NOT NULL,
    intermedio            VARCHAR(30)   NOT NULL REFERENCES db_intermedi(intermedio),
    tecnica                VARCHAR(60)   NOT NULL,
    capex_eur_ton          NUMERIC(12,2) NOT NULL CHECK (capex_eur_ton >= 0),
    opex_eur_ton           NUMERIC(12,2) NOT NULL CHECK (opex_eur_ton >= 0),
    tipo_output            VARCHAR(15)   NOT NULL CHECK (tipo_output IN ('prodotto','intermedio')),
    prodotto               VARCHAR(30)   REFERENCES db_prodotti(prodotto),
    intermedio_output      VARCHAR(30)   REFERENCES db_intermedi(intermedio),
    recupero_pct_min       NUMERIC(6,5)  NOT NULL CHECK (recupero_pct_min > 0 AND recupero_pct_min <= 1),
    recupero_pct_max       NUMERIC(6,5)  NOT NULL CHECK (recupero_pct_max > 0 AND recupero_pct_max <= 1),
    descrizione_fasi       TEXT,
    CONSTRAINT chk_sottoprocessi_range CHECK (recupero_pct_max >= recupero_pct_min),
    CONSTRAINT chk_sottoprocessi_output CHECK (
        (tipo_output = 'prodotto' AND prodotto IS NOT NULL AND intermedio_output IS NULL) OR
        (tipo_output = 'intermedio' AND intermedio_output IS NOT NULL AND prodotto IS NULL)
    )
);
CREATE INDEX idx_sottoprocessi_input ON db_sottoprocessi (intermedio);
CREATE INDEX idx_sottoprocessi_id ON db_sottoprocessi (id_sottoprocesso);
CREATE INDEX idx_intermedi_comp ON db_intermedi_composizione (intermedio);
