-- =============================================================================
-- Migrazione v10.2: opex specifico per materiale nelle trasformazioni dei processi
--
--   db_processi_trasformazioni.opex_spec   EUR per t trattata (stessa unita' di opex_eur_ton)
--
-- Vuota = il materiale paga l'opex del processo (db_processi.opex_eur_ton). Compilata = la
-- massa di quel materiale (o di quel materiale nell'assieme indicato) paga opex_spec al posto
-- dell'opex del processo, per i materiali che subiscono solo una parte del trattamento:
--   opex = (massa trattata - massa dei materiali con opex_spec) x opex_eur_ton
--          + somma(massa del materiale x opex_spec)
-- Il capex non cambia. Se un materiale ha piu' righe basta compilarne una; valori diversi
-- tra le righe dello stesso materiale: vale il primo (id minimo) e il calcolo lo segnala.
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
ALTER TABLE db_processi_trasformazioni ADD COLUMN IF NOT EXISTS opex_spec NUMERIC(14,4)
    CHECK (opex_spec IS NULL OR opex_spec >= 0);
COMMIT;
