<?php
declare(strict_types=1);

/**
 * log_atividades.php
 *
 * Sistema centralizado de log de atividades do painel.
 * Registra todas as ações (criação, edição, exclusão) em uma tabela
 * `log_atividades` com retenção de 60 dias.
 *
 * Uso:
 *   require_once __DIR__ . '/../_comum/log_atividades.php';
 *   log_registrar($pdo, 'usuario', 'criou', 'Criou o usuário joao', [
 *       'user_id' => 'joao', 'nome' => 'João da Silva'
 *   ]);
 */

/**
 * Garante que a tabela `log_atividades` exista no banco.
 * Chamada lazy na primeira execução de `log_registrar()`.
 */
function log_atividades_garantir_tabela(PDO $pdo): void
{
    static $verificado = false;
    if ($verificado) return;

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS log_atividades (
            id_log          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            data_hora       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
            user_id_executor VARCHAR(100)   NULL COMMENT 'Quem executou a acao (user_id ou admin)',
            entidade        VARCHAR(80)     NOT NULL COMMENT 'Tipo: usuario, atividade, subtarefa, pagamento, etc.',
            acao            VARCHAR(40)     NOT NULL COMMENT 'criou, editou, excluiu, alterou_status, etc.',
            id_entidade     VARCHAR(100)    NULL COMMENT 'ID do registro afetado',
            descricao       TEXT            NOT NULL COMMENT 'Descricao legivel da acao',
            dados_antes     JSON            NULL COMMENT 'Snapshot antes da alteracao',
            dados_depois    JSON            NULL COMMENT 'Snapshot depois da alteracao',
            ip              VARCHAR(45)     NULL COMMENT 'IP do cliente',
            INDEX idx_log_data (data_hora),
            INDEX idx_log_entidade (entidade),
            INDEX idx_log_executor (user_id_executor)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    $verificado = true;
}

/**
 * Registra uma entrada no log de atividades.
 *
 * @param PDO         $pdo             Conexao PDO ativa
 * @param string      $entidade        Tipo de entidade (usuario, atividade, subtarefa, pagamento, credencial, mega, auditoria, config)
 * @param string      $acao            Acao realizada (criou, editou, excluiu, alterou_status, etc.)
 * @param string      $descricao       Texto legivel descrevendo o que aconteceu
 * @param array|null  $dados_depois    Snapshot dos dados apos a acao
 * @param array|null  $dados_antes     Snapshot dos dados antes da acao
 * @param string|null $id_entidade     ID do registro afetado (pode ser int convertido pra string)
 * @param string|null $user_id_executor Quem fez a acao (se null, tenta pegar da sessao)
 */
function log_registrar(
    PDO     $pdo,
    string  $entidade,
    string  $acao,
    string  $descricao,
    ?array  $dados_depois = null,
    ?array  $dados_antes = null,
    ?string $id_entidade = null,
    ?string $user_id_executor = null
): void {
    try {
        log_atividades_garantir_tabela($pdo);

        // Tenta obter executor da sessao se nao informado
        if ($user_id_executor === null) {
            if (session_status() === PHP_SESSION_ACTIVE && isset($_SESSION['user_id'])) {
                $user_id_executor = (string)$_SESSION['user_id'];
            } else {
                $user_id_executor = 'admin';
            }
        }

        // IP do cliente
        $ip = $_SERVER['HTTP_X_FORWARDED_FOR']
            ?? $_SERVER['HTTP_X_REAL_IP']
            ?? $_SERVER['REMOTE_ADDR']
            ?? null;
        if ($ip !== null) {
            // Pega o primeiro IP se for lista (X-Forwarded-For pode ter varios)
            $ip = trim(explode(',', (string)$ip)[0]);
        }

        $st = $pdo->prepare("
            INSERT INTO log_atividades
                (user_id_executor, entidade, acao, id_entidade, descricao, dados_antes, dados_depois, ip)
            VALUES
                (:executor, :entidade, :acao, :id_entidade, :descricao, :antes, :depois, :ip)
        ");
        $st->execute([
            ':executor'    => $user_id_executor,
            ':entidade'    => $entidade,
            ':acao'        => $acao,
            ':id_entidade' => $id_entidade,
            ':descricao'   => $descricao,
            ':antes'       => $dados_antes !== null ? json_encode($dados_antes, JSON_UNESCAPED_UNICODE) : null,
            ':depois'      => $dados_depois !== null ? json_encode($dados_depois, JSON_UNESCAPED_UNICODE) : null,
            ':ip'          => $ip,
        ]);
    } catch (Throwable $e) {
        // Log de atividades NUNCA deve quebrar a operacao principal.
        // Se falhar, registra no log do PHP e segue.
        error_log('[log_atividades] Falha ao registrar: ' . $e->getMessage());
    }
}

/**
 * Remove logs com mais de $dias dias.
 * Chamada pelo endpoint listar.php a cada request (lightweight: DELETE com LIMIT).
 */
function log_atividades_cleanup(PDO $pdo, int $dias = 60): int
{
    try {
        log_atividades_garantir_tabela($pdo);

        $st = $pdo->prepare("
            DELETE FROM log_atividades
            WHERE data_hora < DATE_SUB(NOW(), INTERVAL :dias DAY)
            LIMIT 5000
        ");
        $st->execute([':dias' => $dias]);
        return $st->rowCount();
    } catch (Throwable $e) {
        error_log('[log_atividades] Falha no cleanup: ' . $e->getMessage());
        return 0;
    }
}
