-- =============================================================================
-- Migrazione v10.8: tolte dai prodotti le colonne di crescita del prezzo (non usate nel calcolo)
--
--   db_prodotti.proiezione_prezzo_p1, db_prodotti.proiezione_prezzo_p2
--
-- I ricavi si rivalutano all'anno di trattamento con l'indice dei costi (v10.6). Gli intermedi
-- conservano le loro colonne P1/P2.
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
ALTER TABLE db_prodotti DROP COLUMN IF EXISTS proiezione_prezzo_p1;
ALTER TABLE db_prodotti DROP COLUMN IF EXISTS proiezione_prezzo_p2;
COMMIT;
