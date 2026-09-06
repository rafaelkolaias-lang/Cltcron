-- =============================================================
-- MÓDULO: Gastos e produções do Editor Premiere Premium (por usuário)
-- Executar manualmente no servidor MySQL/MariaDB (banco `dados`).
-- Seguro para rodar em banco sem estas tabelas (IF NOT EXISTS).
--
-- Quem grava: o próprio editor de cada usuário, pela API
--   painel/commands/editor/api/registrar.php  (auth user_id + chave).
-- Quem lê: só a conta "adm", pela API
--   painel/commands/editor/api/listar.php
--
-- O app continua gravando o livro local dele (historico_gastos.json,
-- motor_state.json, historico_producao.json) — estas tabelas são a
-- CÓPIA CENTRAL, para o adm ver todo mundo na janela "Opções > Gastos".
-- =============================================================

-- Tabela 1: um lançamento de gasto (modo manual OU motor) por linha.
CREATE TABLE IF NOT EXISTS editor_gastos (
    id            BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uid           CHAR(32)      NOT NULL,                 -- uuid4 hex gerado no app: reenvio não duplica
    user_id       VARCHAR(60)   NOT NULL,                 -- usuarios.user_id (vem da autenticação, nunca do corpo)
    origem        ENUM('manual','motor') NOT NULL DEFAULT 'manual',
    quando        DATETIME      NOT NULL,                 -- hora local do app
    dia           DATE          NOT NULL,                 -- = DATE(quando), indexado para somar por dia
    operacao      VARCHAR(255)  NOT NULL DEFAULT '',
    detalhe       VARCHAR(500)  NOT NULL DEFAULT '',
    usd           DECIMAL(12,6) NOT NULL DEFAULT 0,
    versao_app    VARCHAR(20)   NULL,
    maquina       VARCHAR(80)   NULL,                     -- nome do PC (mesmo usuário em 2 máquinas)
    criado_em     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_uid (uid),
    KEY idx_user_dia (user_id, dia),
    KEY idx_dia (dia)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela 2: uma ficha de produção (um "Iniciar Edição") por linha.
-- As colunas soltas são as que a janela filtra/soma; a ficha inteira
-- (etapas, contagens) vai em `ficha_json`, para a janela mostrar o
-- detalhe igual ao local sem precisar de coluna nova a cada contagem.
CREATE TABLE IF NOT EXISTS editor_producoes (
    id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    uid             CHAR(32)      NOT NULL,
    user_id         VARCHAR(60)   NOT NULL,
    quando          DATETIME      NOT NULL,
    dia             DATE          NOT NULL,
    projeto         VARCHAR(200)  NOT NULL DEFAULT '',
    origem          VARCHAR(20)   NOT NULL DEFAULT 'Manual', -- Manual | Lote | Motor
    modo            VARCHAR(40)   NOT NULL DEFAULT '',
    canal           VARCHAR(120)  NOT NULL DEFAULT '',
    tema            VARCHAR(255)  NOT NULL DEFAULT '',
    status          VARCHAR(20)   NOT NULL DEFAULT '',       -- ok | falha | cancelada
    tempo_parede_s  DECIMAL(10,1) NOT NULL DEFAULT 0,
    tempo_espera_s  DECIMAL(10,1) NOT NULL DEFAULT 0,
    tempo_liquido_s DECIMAL(10,1) NOT NULL DEFAULT 0,
    custo_usd       DECIMAL(12,6) NOT NULL DEFAULT 0,
    ficha_json      MEDIUMTEXT    NULL,
    versao_app      VARCHAR(20)   NULL,
    maquina         VARCHAR(80)   NULL,
    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_uid (uid),
    KEY idx_user_dia (user_id, dia),
    KEY idx_dia (dia)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
