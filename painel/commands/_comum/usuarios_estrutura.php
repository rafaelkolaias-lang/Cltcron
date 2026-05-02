<?php
declare(strict_types=1);

/**
 * usuarios_estrutura.php — garante colunas/campos extras na tabela `usuarios`.
 *
 * Idempotente. Chamado pelos endpoints que dependem dessas colunas.
 * Atualmente: só `chave_pix` (introduzida em 2026-05-01).
 */

require_once __DIR__ . '/../conexao/conexao.php';

if (!function_exists('usuarios_garantir_chave_pix')) {
    function usuarios_garantir_chave_pix(?PDO $pdo = null): void
    {
        static $ja_garantido = false;
        if ($ja_garantido) return;

        $pdo = $pdo ?: obter_conexao_pdo();
        try {
            $linha = $pdo->query(
                "SELECT 1 FROM information_schema.COLUMNS
                  WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'usuarios'
                    AND COLUMN_NAME = 'chave_pix'
                  LIMIT 1"
            )->fetchColumn();
            if (!$linha) {
                $pdo->exec("ALTER TABLE usuarios ADD COLUMN chave_pix VARCHAR(255) NULL DEFAULT NULL");
            }
            $ja_garantido = true;
        } catch (Throwable $_e) {
            // Se a verificação/ALTER falhar, não bloqueia o endpoint — propaga só
            // se ele realmente tentar gravar/ler a coluna.
        }
    }
}
