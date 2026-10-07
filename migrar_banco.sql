-- =====================================================================
-- MIGRAÇÃO — Adicionar campo senha na tabela usuario
--            e campo valor_unit na tabela despesa
-- Execute este script no SQL Editor do Supabase (uma vez)
-- =====================================================================

-- 1. Adicionar coluna senha na tabela usuario
ALTER TABLE usuario
    ADD COLUMN IF NOT EXISTS senha VARCHAR(64);

-- 2. Adicionar coluna valor_unit na tabela despesa
ALTER TABLE despesa
    ADD COLUMN IF NOT EXISTS valor_unit NUMERIC(10,3);

-- 3. Definir uma senha padrão para o usuário Luis já existente
--    (SHA-256 de "1234" — troque depois pelo app)
UPDATE usuario
   SET senha = '03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4'
 WHERE nome = 'Luis' AND senha IS NULL;

-- =====================================================================
-- Pronto! Agora defina as senhas dos usuários pelo app (aba Cadastros)
-- =====================================================================
