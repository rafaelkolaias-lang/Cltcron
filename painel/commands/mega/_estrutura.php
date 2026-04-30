<?php
declare(strict_types=1);

/**
 * _estrutura.php — cria (se não existir) as tabelas do módulo MEGA e
 * registra os modelos de credenciais usados para login automático na conta
 * dedicada do MEGA.
 *
 * Idempotente. Chamado pelos endpoints do módulo MEGA antes de qualquer query.
 */

require_once __DIR__ . '/../conexao/conexao.php';

function mega_garantir_estrutura(?PDO $pdo = null): void
{
    static $ja_garantido = false;
    if ($ja_garantido) return;

    $pdo = $pdo ?: obter_conexao_pdo();

    // A. Configuração do canal/atividade no MEGA
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS mega_canal_config (
            id_config        BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            id_atividade     INT UNSIGNED NOT NULL,
            nome_pasta_mega  VARCHAR(255) NOT NULL,
            upload_ativo     TINYINT(1) NOT NULL DEFAULT 0,
            criado_em        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY uk_atividade (id_atividade)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // B. Campos de upload exigidos por user+atividade
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS mega_campos_upload (
            id_campo              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            user_id               VARCHAR(60) NOT NULL,
            id_atividade          INT UNSIGNED NOT NULL,
            label_campo           VARCHAR(120) NOT NULL,
            extensoes_permitidas  VARCHAR(255) NULL,
            quantidade_maxima     SMALLINT UNSIGNED NOT NULL DEFAULT 1,
            obrigatorio           TINYINT(1) NOT NULL DEFAULT 1,
            ordem                 SMALLINT UNSIGNED NOT NULL DEFAULT 0,
            ativo                 TINYINT(1) NOT NULL DEFAULT 1,
            criado_em             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_user_atividade (user_id, id_atividade),
            KEY idx_atividade (id_atividade)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // C. Cadastro da pasta lógica do vídeo (índice canônico no banco)
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS mega_pasta_logica (
            id_pasta_logica BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            id_atividade    INT UNSIGNED NOT NULL,
            nome_pasta      VARCHAR(255) NOT NULL,
            numero_video    VARCHAR(20)  NOT NULL,
            titulo_video    VARCHAR(255) NOT NULL,
            criado_por      VARCHAR(60)  NULL,
            criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ativo           TINYINT(1) NOT NULL DEFAULT 1,
            UNIQUE KEY uk_atividade_pasta (id_atividade, nome_pasta),
            KEY idx_atividade (id_atividade)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // D. Metadados de uploads realizados (auditoria/controle, sem link público)
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS mega_uploads (
            id_upload       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            id_pasta_logica BIGINT UNSIGNED NOT NULL,
            id_subtarefa    BIGINT UNSIGNED NULL,
            user_id         VARCHAR(60)  NOT NULL,
            nome_campo      VARCHAR(120) NOT NULL,
            nome_arquivo    VARCHAR(500) NOT NULL,
            tamanho_bytes   BIGINT UNSIGNED NULL,
            status_upload   ENUM('pendente','enviando','concluido','erro') NOT NULL DEFAULT 'pendente',
            mensagem_erro   VARCHAR(500) NULL,
            enviado_em      DATETIME NULL,
            criado_em       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_pasta (id_pasta_logica),
            KEY idx_user (user_id),
            KEY idx_subtarefa (id_subtarefa)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // Modelos de credenciais para login automático no MEGA. Aproveitam a infra
    // existente (cifragem MASTER no banco, recifragem CLIENT na entrega ao
    // desktop). O admin preenche os valores em modo global (aplicar_todos=true)
    // — assim cada cliente vê os mesmos credenciais via /credenciais/api/obter.
    $pdo->exec("
        INSERT IGNORE INTO credenciais_modelos
            (identificador, nome_exibicao, categoria, descricao, ordem_exibicao, aplicar_novos_usuarios)
        VALUES
            ('mega_email',    'MEGA — E-mail conta dedicada', 'mega', 'Login automático na conta MEGA dedicada do sistema', 60, 0),
            ('mega_password', 'MEGA — Senha conta dedicada',  'mega', 'Senha da conta MEGA dedicada (cifrada em repouso)', 61, 0)
    ");

    $ja_garantido = true;
}
