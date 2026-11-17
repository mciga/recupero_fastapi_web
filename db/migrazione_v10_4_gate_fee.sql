-- =============================================================================
-- Migrazione v10.4: gate fee dei processi
--
--   db_processi.gate_fee_eur_ton   EUR per t di macrocomponente consegnato all'impianto (con segno)
--       > 0  il proprietario (o il produttore) paga l'impianto di riciclo per il ritiro: ricavo
--            per l'impianto (es. batterie LFP);
--       < 0  l'impianto paga il materiale ritirato: costo per l'impianto;
--       = 0  nessun corrispettivo (predefinito).
--
-- Dalla v10.4 gate fee, capex e opex si calcolano sulla massa totale del macrocomponente in
-- ingresso all'impianto (compresi i materiali che il processo non tratta), non piu' sulla sola
-- massa trattata. Il margine diventa: ricavi dai prodotti + gate fee - costi.
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
ALTER TABLE db_processi ADD COLUMN IF NOT EXISTS gate_fee_eur_ton NUMERIC(14,2) NOT NULL DEFAULT 0;
COMMIT;
