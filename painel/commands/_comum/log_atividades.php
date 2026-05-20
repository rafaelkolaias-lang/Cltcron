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
 * Registra um erro/rejeicao automaticamente.
 * Chamada por responder_json() quando $ok === false.
 * Cria sua propria conexao PDO (responder_json nem sempre tem uma).
 *
 * @param string $mensagem    Mensagem de erro
 * @param int    $codigo_http Status HTTP (400, 403, 404, 409, 422, 500)
 * @param mixed  $dados       Dados extras do erro (sem secrets)
 */
function log_registrar_erro(string $mensagem, int $codigo_http, $dados = null): void
{
    // Evita recursao: se o proprio log der erro, nao tenta logar de novo
    static $logando = false;
    if ($logando) return;
    $logando = true;

    try {
        // Cria conexao propria (responder_json pode nao ter $pdo)
        require_once __DIR__ . '/../conexao/conexao.php';
        $pdo = obter_conexao_pdo();

        log_atividades_garantir_tabela($pdo);

        // Detectar endpoint
        $endpoint = $_SERVER['REQUEST_URI'] ?? '?';
        // Remover query string e prefixo do painel para ficar legivel
        $endpoint = explode('?', $endpoint)[0];
        $endpoint = preg_replace('#.*/commands/#', '', $endpoint) ?? $endpoint;

        // Detectar origem (painel admin vs desktop app)
        $origem = 'painel';
        $auth_header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
        if (stripos($auth_header, 'Bearer') !== false || isset($_SERVER['HTTP_X_USER_ID'])) {
            $origem = 'desktop';
        }

        // Detectar executor
        $executor = null;
        if (session_status() === PHP_SESSION_ACTIVE && isset($_SESSION['user_id'])) {
            $executor = (string)$_SESSION['user_id'];
        } elseif (isset($_SERVER['HTTP_X_USER_ID'])) {
            $executor = (string)$_SERVER['HTTP_X_USER_ID'];
        } elseif ($auth_header !== '' && preg_match('#Bearer\s+([^:]+):#', $auth_header, $m)) {
            $executor = $m[1];
        }

        // Classificar acao
        $acao = $codigo_http >= 500 ? 'erro_interno' : 'rejeicao';

        // Montar descricao legivel
        $metodo = $_SERVER['REQUEST_METHOD'] ?? '?';
        $descricao = "[{$codigo_http}] {$metodo} {$endpoint} — {$mensagem}";

        // IP
        $ip = $_SERVER['HTTP_X_FORWARDED_FOR']
            ?? $_SERVER['HTTP_X_REAL_IP']
            ?? $_SERVER['REMOTE_ADDR']
            ?? null;
        if ($ip !== null) {
            $ip = trim(explode(',', (string)$ip)[0]);
        }

        // Sanitizar dados (remover campos sensiveis)
        $dados_limpos = null;
        if ($dados !== null && is_array($dados)) {
            $campos_sensiveis = ['senha', 'password', 'chave', 'valor', 'valor_cifrado', 'nonce', 'secret', 'token'];
            $dados_limpos = [];
            foreach ($dados as $k => $v) {
                $k_lower = strtolower((string)$k);
                $eh_sensivel = false;
                foreach ($campos_sensiveis as $cs) {
                    if (strpos($k_lower, $cs) !== false) { $eh_sensivel = true; break; }
                }
                $dados_limpos[$k] = $eh_sensivel ? '***' : $v;
            }
        }

        $st = $pdo->prepare("
            INSERT INTO log_atividades
                (user_id_executor, entidade, acao, id_entidade, descricao, dados_antes, dados_depois, ip)
            VALUES
                (:executor, :entidade, :acao, NULL, :descricao, NULL, :depois, :ip)
        ");
        $st->execute([
            ':executor'  => $executor,
            ':entidade'  => $origem,
            ':acao'      => $acao,
            ':descricao' => mb_substr($descricao, 0, 2000),
            ':depois'    => $dados_limpos !== null ? json_encode($dados_limpos, JSON_UNESCAPED_UNICODE) : null,
            ':ip'        => $ip,
        ]);
    } catch (Throwable $e) {
        error_log('[log_atividades] Falha ao registrar erro: ' . $e->getMessage());
    } finally {
        $logando = false;
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
