-- =============================================================================
-- Migrazione v10: processi e sottoprocessi in due tabelle (testata 1 -> N trasformazioni)
--
--   db_processi                    una riga per processo: id_processo (chiave), tipologia,
--                                  sotto_tecnologia, macro_componente, tecnica, capex, opex,
--                                  descrizione_fasi, taglia di riferimento, esponente, vita utile
--   db_processi_trasformazioni     una riga per trasformazione: materiale in ingresso -> uscita
--                                  (prodotto / impurita' / scarto / intermedio) con le tre rese
--   db_sottoprocessi               una riga per sottoprocesso (intermedio in ingresso, costi...)
--   db_sottoprocessi_trasformazioni una riga per uscita del sottoprocesso
--
-- Le trasformazioni referenziano la testata con ON DELETE CASCADE (cancellando il processo si
-- cancellano le sue righe) e ON UPDATE CASCADE (rinominando l'id_processo le righe lo seguono).
--
-- I dati esistenti sono convertiti sul posto. Testata = valori della PRIMA riga (id minimo) di
-- ogni processo, gli stessi che il calcolo usava finora (righe[0]). Se le righe di un processo
-- hanno tipologia, macrocomponente, sotto-tecnologia o tecnica diverse la migrazione si ferma;
-- per capex/opex/fasi/taglia/esponente/vita diversi si tiene la prima riga e si segnala (NOTICE).
--
-- Uso (in una sola transazione):
--   psql ... -v ON_ERROR_STOP=1 -c "SET search_path TO recupero_novembre" -f migrazione_v10_processi_testata.sql
-- oppure anteporre:  SET search_path TO <schema>;
-- =============================================================================
BEGIN;

-- ---------------------------------------------------------------- controlli ----
DO $$
DECLARE r record;
BEGIN
    IF to_regclass('db_processi_trasformazioni') IS NOT NULL THEN
        RAISE EXCEPTION 'migrazione gia'' applicata: db_processi_trasformazioni esiste';
    END IF;
    FOR r IN SELECT id_processo FROM db_processi GROUP BY id_processo
             HAVING COUNT(DISTINCT (tipologia, COALESCE(sotto_tecnologia,''), macro_componente, tecnica)) > 1 LOOP
        RAISE EXCEPTION 'processo % con tipologia/sotto-tecnologia/macrocomponente/tecnica diverse tra le righe', r.id_processo;
    END LOOP;
    FOR r IN SELECT id_sottoprocesso FROM db_sottoprocessi GROUP BY id_sottoprocesso
             HAVING COUNT(DISTINCT (intermedio, tecnica)) > 1 LOOP
        RAISE EXCEPTION 'sottoprocesso % con intermedio/tecnica diversi tra le righe', r.id_sottoprocesso;
    END LOOP;
    FOR r IN SELECT id_processo FROM db_processi GROUP BY id_processo
             HAVING COUNT(DISTINCT (capex_eur_ton, opex_eur_ton, COALESCE(descrizione_fasi,''),
                                    COALESCE(taglia_riferimento_t_anno,0), esponente_scala, vita_utile_anni)) > 1 LOOP
        RAISE NOTICE 'processo %: costi/fasi/taglia diversi tra le righe, si tiene la prima riga', r.id_processo;
    END LOOP;
    FOR r IN SELECT id_sottoprocesso FROM db_sottoprocessi GROUP BY id_sottoprocesso
             HAVING COUNT(DISTINCT (capex_eur_ton, opex_eur_ton, COALESCE(descrizione_fasi,''),
                                    COALESCE(taglia_riferimento_t_anno,0), esponente_scala, vita_utile_anni)) > 1 LOOP
        RAISE NOTICE 'sottoprocesso %: costi/fasi/taglia diversi tra le righe, si tiene la prima riga', r.id_sottoprocesso;
    END LOOP;
END $$;

ALTER TABLE db_processi RENAME TO db_processi_v9;
ALTER TABLE db_sottoprocessi RENAME TO db_sottoprocessi_v9;
ALTER INDEX IF EXISTS idx_processi_filtro RENAME TO idx_processi_v9_filtro;
ALTER INDEX IF EXISTS idx_processi_id RENAME TO idx_processi_v9_id;
ALTER INDEX IF EXISTS idx_sottoprocessi_input RENAME TO idx_sottoprocessi_v9_input;
ALTER INDEX IF EXISTS idx_sottoprocessi_id RENAME TO idx_sottoprocessi_v9_id;

-- ------------------------------------------------------------ processi -----
CREATE TABLE db_processi (
    id_processo           VARCHAR(40)   PRIMARY KEY,
    tipologia             VARCHAR(30)   NOT NULL CHECK (tipologia IN ('BESS','EOLICO','FOTOVOLTAICO')),
    sotto_tecnologia      VARCHAR(30),   -- vuota = qualsiasi; piu' valori separati da ';'
    macro_componente      VARCHAR(80)   NOT NULL,
    tecnica               VARCHAR(80)   NOT NULL,
    capex_eur_ton         NUMERIC(12,2) NOT NULL CHECK (capex_eur_ton >= 0),   -- EUR per t/anno di capacita'
    opex_eur_ton          NUMERIC(12,2) NOT NULL CHECK (opex_eur_ton >= 0),    -- EUR per t trattata
    descrizione_fasi      TEXT,
    taglia_riferimento_t_anno NUMERIC(14,2) CHECK (taglia_riferimento_t_anno > 0),  -- vuota = capex lineare
    esponente_scala       NUMERIC(4,2)  NOT NULL DEFAULT 0.6 CHECK (esponente_scala > 0 AND esponente_scala <= 1),
    vita_utile_anni       NUMERIC(5,1)  NOT NULL DEFAULT 15 CHECK (vita_utile_anni > 0)
);
CREATE INDEX idx_processi_filtro ON db_processi (tipologia, macro_componente);

CREATE TABLE db_processi_trasformazioni (
    id                    SERIAL        PRIMARY KEY,
    id_processo           VARCHAR(40)   NOT NULL REFERENCES db_processi(id_processo) ON UPDATE CASCADE ON DELETE CASCADE,
    material_id           VARCHAR(60)   NOT NULL,
    assieme_dettaglio     VARCHAR(160),  -- vuota = tutto il materiale (o il resto non coperto da righe specifiche)
    tipo_output           VARCHAR(15)   NOT NULL CHECK (tipo_output IN ('prodotto','impurita','scarto','intermedio')),
    prodotto              VARCHAR(40)   REFERENCES db_prodotti(prodotto) ON UPDATE CASCADE,
    intermedio_output     VARCHAR(40)   REFERENCES db_intermedi(intermedio) ON UPDATE CASCADE,
    scarto                VARCHAR(80)   REFERENCES db_scarti(scarto) ON UPDATE CASCADE,
    recupero_pct_min      NUMERIC(14,12) NOT NULL CHECK (recupero_pct_min >= 0 AND recupero_pct_min <= 1),
    recupero_pct          NUMERIC(14,12) NOT NULL CHECK (recupero_pct >= 0 AND recupero_pct <= 1),
    recupero_pct_max      NUMERIC(14,12) NOT NULL CHECK (recupero_pct_max >= 0 AND recupero_pct_max <= 1),
    reagente              VARCHAR(40)   REFERENCES db_reagenti(reagente) ON UPDATE CASCADE,
    CONSTRAINT chk_proc_trasf_reagente CHECK (reagente IS NULL OR tipo_output = 'prodotto'),
    CONSTRAINT chk_proc_trasf_output CHECK (
        (tipo_output IN ('prodotto','impurita') AND (prodotto IS NOT NULL OR intermedio_output IS NOT NULL) AND scarto IS NULL) OR
        (tipo_output = 'intermedio' AND intermedio_output IS NOT NULL AND prodotto IS NULL AND scarto IS NULL) OR
        (tipo_output = 'scarto' AND scarto IS NOT NULL AND prodotto IS NULL AND intermedio_output IS NULL)
    )
);
CREATE INDEX idx_proc_trasf_processo ON db_processi_trasformazioni (id_processo);
CREATE INDEX idx_proc_trasf_materiale ON db_processi_trasformazioni (material_id);

INSERT INTO db_processi (id_processo, tipologia, sotto_tecnologia, macro_componente, tecnica, capex_eur_ton,
                         opex_eur_ton, descrizione_fasi, taglia_riferimento_t_anno, esponente_scala, vita_utile_anni)
SELECT DISTINCT ON (id_processo) id_processo, tipologia, sotto_tecnologia, macro_componente, tecnica, capex_eur_ton,
       opex_eur_ton, descrizione_fasi, taglia_riferimento_t_anno, esponente_scala, vita_utile_anni
FROM db_processi_v9 ORDER BY id_processo, id;

INSERT INTO db_processi_trasformazioni (id, id_processo, material_id, assieme_dettaglio, tipo_output, prodotto,
                                        intermedio_output, scarto, recupero_pct_min, recupero_pct, recupero_pct_max, reagente)
SELECT id, id_processo, material_id, assieme_dettaglio, tipo_output, prodotto,
       intermedio_output, scarto, recupero_pct_min, recupero_pct, recupero_pct_max, reagente
FROM db_processi_v9 ORDER BY id;

-- --------------------------------------------------------- sottoprocessi -----
CREATE TABLE db_sottoprocessi (
    id_sottoprocesso      VARCHAR(40)   PRIMARY KEY,
    intermedio            VARCHAR(40)   NOT NULL REFERENCES db_intermedi(intermedio) ON UPDATE CASCADE,
    tecnica               VARCHAR(80)   NOT NULL,
    capex_eur_ton         NUMERIC(12,2) NOT NULL CHECK (capex_eur_ton >= 0),
    opex_eur_ton          NUMERIC(12,2) NOT NULL CHECK (opex_eur_ton >= 0),
    descrizione_fasi      TEXT,
    taglia_riferimento_t_anno NUMERIC(14,2) CHECK (taglia_riferimento_t_anno > 0),
    esponente_scala       NUMERIC(4,2)  NOT NULL DEFAULT 0.6 CHECK (esponente_scala > 0 AND esponente_scala <= 1),
    vita_utile_anni       NUMERIC(5,1)  NOT NULL DEFAULT 15 CHECK (vita_utile_anni > 0)
);
CREATE INDEX idx_sottoprocessi_input ON db_sottoprocessi (intermedio);

CREATE TABLE db_sottoprocessi_trasformazioni (
    id                    SERIAL        PRIMARY KEY,
    id_sottoprocesso      VARCHAR(40)   NOT NULL REFERENCES db_sottoprocessi(id_sottoprocesso) ON UPDATE CASCADE ON DELETE CASCADE,
    tipo_output           VARCHAR(15)   NOT NULL CHECK (tipo_output IN ('prodotto','impurita','scarto','intermedio')),
    prodotto              VARCHAR(40)   REFERENCES db_prodotti(prodotto) ON UPDATE CASCADE,
    intermedio_output     VARCHAR(40)   REFERENCES db_intermedi(intermedio) ON UPDATE CASCADE,
    scarto                VARCHAR(80)   REFERENCES db_scarti(scarto) ON UPDATE CASCADE,
    recupero_pct_min      NUMERIC(14,12) NOT NULL CHECK (recupero_pct_min >= 0 AND recupero_pct_min <= 1),
    recupero_pct          NUMERIC(14,12) NOT NULL CHECK (recupero_pct >= 0 AND recupero_pct <= 1),
    recupero_pct_max      NUMERIC(14,12) NOT NULL CHECK (recupero_pct_max >= 0 AND recupero_pct_max <= 1),
    reagente              VARCHAR(40)   REFERENCES db_reagenti(reagente) ON UPDATE CASCADE,
    CONSTRAINT chk_sotto_trasf_reagente CHECK (reagente IS NULL OR tipo_output = 'prodotto'),
    CONSTRAINT chk_sotto_trasf_output CHECK (
        (tipo_output IN ('prodotto','impurita') AND (prodotto IS NOT NULL OR intermedio_output IS NOT NULL) AND scarto IS NULL) OR
        (tipo_output = 'intermedio' AND intermedio_output IS NOT NULL AND prodotto IS NULL AND scarto IS NULL) OR
        (tipo_output = 'scarto' AND scarto IS NOT NULL AND prodotto IS NULL AND intermedio_output IS NULL)
    )
);
CREATE INDEX idx_sotto_trasf_sottoprocesso ON db_sottoprocessi_trasformazioni (id_sottoprocesso);

INSERT INTO db_sottoprocessi (id_sottoprocesso, intermedio, tecnica, capex_eur_ton, opex_eur_ton, descrizione_fasi,
                              taglia_riferimento_t_anno, esponente_scala, vita_utile_anni)
SELECT DISTINCT ON (id_sottoprocesso) id_sottoprocesso, intermedio, tecnica, capex_eur_ton, opex_eur_ton, descrizione_fasi,
       taglia_riferimento_t_anno, esponente_scala, vita_utile_anni
FROM db_sottoprocessi_v9 ORDER BY id_sottoprocesso, id;

INSERT INTO db_sottoprocessi_trasformazioni (id, id_sottoprocesso, tipo_output, prodotto, intermedio_output, scarto,
                                             recupero_pct_min, recupero_pct, recupero_pct_max, reagente)
SELECT id, id_sottoprocesso, tipo_output, prodotto, intermedio_output, scarto,
       recupero_pct_min, recupero_pct, recupero_pct_max, reagente
FROM db_sottoprocessi_v9 ORDER BY id;

-- sequenze allineate agli id copiati
SELECT setval(pg_get_serial_sequence('db_processi_trasformazioni', 'id'),
              COALESCE((SELECT MAX(id) FROM db_processi_trasformazioni), 0) + 1, false);
SELECT setval(pg_get_serial_sequence('db_sottoprocessi_trasformazioni', 'id'),
              COALESCE((SELECT MAX(id) FROM db_sottoprocessi_trasformazioni), 0) + 1, false);

-- controllo finale: nessuna riga persa
DO $$
BEGIN
    IF (SELECT COUNT(*) FROM db_processi_trasformazioni) <> (SELECT COUNT(*) FROM db_processi_v9)
       OR (SELECT COUNT(*) FROM db_sottoprocessi_trasformazioni) <> (SELECT COUNT(*) FROM db_sottoprocessi_v9) THEN
        RAISE EXCEPTION 'conteggio righe diverso dopo la copia';
    END IF;
END $$;

-- vecchie tabelle eliminate: per conservarle commentare le due righe seguenti
DROP TABLE db_processi_v9;
DROP TABLE db_sottoprocessi_v9;

COMMIT;
