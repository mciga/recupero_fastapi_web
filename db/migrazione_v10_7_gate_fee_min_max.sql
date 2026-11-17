-- =============================================================================
-- Migrazione v10.7: campo di variazione del gate fee
--
--   db_processi.gate_fee_eur_ton_min   gate fee minimo (EUR/t, con segno); vuoto = uguale al centrale
--   db_processi.gate_fee_eur_ton_max   gate fee massimo (EUR/t, con segno); vuoto = uguale al centrale
--
-- Il margine minimo usa il gate fee minimo, il massimo il gate fee massimo, insieme ai ricavi
-- dello scenario minimo e massimo. Vincolo: minimo <= centrale <= massimo.
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
ALTER TABLE db_processi ADD COLUMN IF NOT EXISTS gate_fee_eur_ton_min NUMERIC(14,2);
ALTER TABLE db_processi ADD COLUMN IF NOT EXISTS gate_fee_eur_ton_max NUMERIC(14,2);
ALTER TABLE db_processi DROP CONSTRAINT IF EXISTS ck_gate_fee_intervallo;
ALTER TABLE db_processi ADD CONSTRAINT ck_gate_fee_intervallo CHECK (
    (gate_fee_eur_ton_min IS NULL OR gate_fee_eur_ton_min <= gate_fee_eur_ton) AND
    (gate_fee_eur_ton_max IS NULL OR gate_fee_eur_ton_max >= gate_fee_eur_ton));
COMMIT;
