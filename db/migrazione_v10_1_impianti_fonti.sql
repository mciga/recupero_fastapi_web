-- =============================================================================
-- Migrazione v10.1: fonte delle coordinate e dell'anno di dismissione degli impianti
--
--   fonte_coordinate   da dove vengono lat/lon: dato utente, riconciliazione confermata,
--                      import satellitare, 'prova' (posizione di prova dentro la Puglia, da
--                      sostituire), vuota = non indicata
--   fonte_anno         da dove viene l'anno di dismissione: 'export MACTEE', 'esercizio DB +
--                      vita utile', 'esercizio di prova + vita utile', vuota = non indicata
--
-- Il cruscotto della dashboard mostra con il bordo tratteggiato gli impianti con fonte 'prova'.
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
ALTER TABLE db_impianti ADD COLUMN IF NOT EXISTS fonte_coordinate VARCHAR(60);
ALTER TABLE db_impianti ADD COLUMN IF NOT EXISTS fonte_anno VARCHAR(60);
COMMIT;
