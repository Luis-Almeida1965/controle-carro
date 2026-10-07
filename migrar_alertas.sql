-- =====================================================================
-- MIGRAÇÃO — Alertas de manutenção
-- Execute no SQL Editor do Supabase (uma vez)
-- =====================================================================

-- 1. Campos de intervalo de manutenção no veículo
ALTER TABLE veiculo
    ADD COLUMN IF NOT EXISTS intervalo_km_oleo     INTEGER DEFAULT 5000,
    ADD COLUMN IF NOT EXISTS intervalo_meses_oleo  INTEGER DEFAULT 6;

-- 2. Campos de alerta na despesa
ALTER TABLE despesa
    ADD COLUMN IF NOT EXISTS gera_alerta   BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS km_proximo    NUMERIC(10,1),
    ADD COLUMN IF NOT EXISTS data_proxima  DATE;

-- =====================================================================
-- Pronto! Configure os intervalos nos veículos pelo app (aba Cadastros)
-- =====================================================================
