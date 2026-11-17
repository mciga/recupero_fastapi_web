-- =============================================================================
-- Migrazione v10.5: trasformazioni uniche per campi chiave
--
-- Nel file Excel le trasformazioni (e i macrocomponenti) non hanno piu' la colonna id: ogni riga si
-- riconosce dai campi che la identificano. Questi indici impediscono due righe con gli stessi campi,
-- cosi' un import o una sincronizzazione non possono creare doppioni.
-- Prima di applicarla vanno tolte le righe doppie eventualmente presenti.
-- (db_macro ha gia' l'indice uq_macro sugli stessi campi.)
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
CREATE UNIQUE INDEX IF NOT EXISTS uq_processi_trasformazioni ON db_processi_trasformazioni
    (id_processo, material_id, COALESCE(assieme_dettaglio, ''), tipo_output,
     COALESCE(prodotto, ''), COALESCE(intermedio_output, ''), COALESCE(scarto, ''));
CREATE UNIQUE INDEX IF NOT EXISTS uq_sottoprocessi_trasformazioni ON db_sottoprocessi_trasformazioni
    (id_sottoprocesso, tipo_output, COALESCE(prodotto, ''), COALESCE(intermedio_output, ''), COALESCE(scarto, ''));
COMMIT;
