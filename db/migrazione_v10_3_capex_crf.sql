-- =============================================================================
-- Migrazione v10.3: capex annualizzato con il fattore di recupero del capitale (CRF)
--
--   db_processi.tasso_sconto, db_sottoprocessi.tasso_sconto
--       tasso di sconto del CRF (frazione, predefinito 0,08)
--   db_processi.taglia_minima_t_anno, db_sottoprocessi.taglia_minima_t_anno
--       soglia economica della taglia (t/anno); sotto la soglia il calcolo lo segnala
--
-- Calcolo (backend/calc.py, _capex_taglia):
--   CRF            = i (1 + i)^n / [(1 + i)^n - 1]      i = tasso_sconto, n = vita_utile_anni
--   quota d'uso    = (massa / taglia) x CRF               (prima: massa / taglia / vita utile)
--   taglia default = taglia_riferimento_t_anno (se c'e'; altrimenti la massa trattata in 1 anno)
-- Uso: anteporre  SET search_path TO <schema>;
-- =============================================================================
BEGIN;
ALTER TABLE db_processi ADD COLUMN IF NOT EXISTS tasso_sconto NUMERIC(6,4) NOT NULL DEFAULT 0.08
    CHECK (tasso_sconto >= 0 AND tasso_sconto < 1);
ALTER TABLE db_processi ADD COLUMN IF NOT EXISTS taglia_minima_t_anno NUMERIC(14,2)
    CHECK (taglia_minima_t_anno IS NULL OR taglia_minima_t_anno > 0);
ALTER TABLE db_sottoprocessi ADD COLUMN IF NOT EXISTS tasso_sconto NUMERIC(6,4) NOT NULL DEFAULT 0.08
    CHECK (tasso_sconto >= 0 AND tasso_sconto < 1);
ALTER TABLE db_sottoprocessi ADD COLUMN IF NOT EXISTS taglia_minima_t_anno NUMERIC(14,2)
    CHECK (taglia_minima_t_anno IS NULL OR taglia_minima_t_anno > 0);
COMMIT;
