-- =============================================================
-- MÓDULO: Credenciais e APIs — Fase 1
-- Executar manualmente no servidor MySQL/MariaDB.
-- Seguro para rodar em banco sem estas tabelas (IF NOT EXISTS).
-- =============================================================

-- Tabela 1: modelos globais de credenciais.
CREATE TABLE IF NOT EXISTS credenciais_modelos (
    id_modelo        INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    identificador    VARCHAR(60)  NOT NULL,
    nome_exibicao    VARCHAR(120) NOT NULL,
    categoria        VARCHAR(60)  NOT NULL DEFAULT 'api',
    descricao        VARCHAR(255) NULL,
    ordem_exibicao   INT UNSIGNED NOT NULL DEFAULT 0,
    status           ENUM('ativo','inativo') NOT NULL DEFAULT 'ativo',
    criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_identificador (identificador)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed inicial. INSERT IGNORE evita duplicar em re-execução.
INSERT IGNORE INTO credenciais_modelos (identificador, nome_exibicao, categoria, ordem_exibicao) VALUES
  ('chatgpt',    'ChatGPT',    'llm',  10),
  ('gemini',     'Gemini',     'llm',  20),
  ('minimax',    'Minimax',    'tts',  30),
  ('elevenlabs', 'Elevenlabs', 'tts',  40),
  ('assembly',   'Assembly',   'stt',  50);

-- Tabela 2: valor da credencial POR usuário (cifrado em repouso).
CREATE TABLE IF NOT EXISTS credenciais_usuario (
    id_credencial     BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    id_modelo         INT UNSIGNED NOT NULL,
    user_id           VARCHAR(60)  NOT NULL,
    mascara_parcial   VARCHAR(32)  NULL,
    valor_cifrado     MEDIUMBLOB   NOT NULL,
    nonce             BINARY(24)   NOT NULL,
    versao_chave      TINYINT UNSIGNED NOT NULL DEFAULT 1,
    status            ENUM('ativo','revogado') NOT NULL DEFAULT 'ativo',
    criado_em         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ultimo_acesso_em  DATETIME NULL,
    UNIQUE KEY uk_modelo_user (id_modelo, user_id),
    KEY idx_user (user_id),
    KEY idx_modelo (id_modelo),
    CONSTRAINT fk_credusr_modelo FOREIGN KEY (id_modelo)
        REFERENCES credenciais_modelos(id_modelo) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
