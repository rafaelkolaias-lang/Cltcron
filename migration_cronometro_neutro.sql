-- =============================================================
-- Migration: Cronômetro Neutro + Abatimento Global
-- Data: 2026-05-21
-- Executar APÓS deploy do código (PHP + Python)
-- =============================================================

-- 1. Unificar cronometro_relatorios: setar id_atividade = NULL
--    (dados históricos preservados na mesma tabela, apenas o vínculo é removido)
UPDATE cronometro_relatorios SET id_atividade = NULL WHERE id_atividade IS NOT NULL;

-- 2. Unificar cronometro_finalizacoes: setar id_atividade = NULL
--    (tabela legada, não recebe novos registros, mas mantém consistência)
UPDATE cronometro_finalizacoes SET id_atividade = NULL WHERE id_atividade IS NOT NULL;

-- 3. Unificar pagamento_abatimentos: setar id_atividade = NULL
--    (abatimentos agora são globais por pagamento, não por atividade)
UPDATE pagamento_abatimentos SET id_atividade = NULL WHERE id_atividade IS NOT NULL;

-- 4. Permitir NULL na coluna id_atividade (caso ainda tenha NOT NULL)
ALTER TABLE cronometro_relatorios MODIFY COLUMN id_atividade INT NULL DEFAULT NULL;
ALTER TABLE cronometro_finalizacoes MODIFY COLUMN id_atividade INT NULL DEFAULT NULL;
ALTER TABLE pagamento_abatimentos MODIFY COLUMN id_atividade INT NULL DEFAULT NULL;

-- 5. Remover UNIQUE KEY e índice antigos que incluíam id_atividade
--    (nova lógica grava 1 linha por pagamento com id_atividade = NULL)
ALTER TABLE pagamento_abatimentos DROP INDEX uq_pag_atividade;
ALTER TABLE pagamento_abatimentos DROP INDEX idx_abt_user_ativ;

-- 6. Criar novo índice por (user_id, id_pagamento) — sem id_atividade
ALTER TABLE pagamento_abatimentos ADD UNIQUE INDEX uq_pag_user (id_pagamento, user_id);
