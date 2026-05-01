<?php
declare(strict_types=1);

/**
 * _auth_cliente.php — autenticação dos endpoints de consumo (Fase 2).
 *
 * Identifica o programa cliente usando (user_id + chave) do próprio usuário
 * cadastrado no painel. Sem "token de serviço" separado — o crachá é a chave
 * do usuário que está logado no app.
 *
 * Credenciais aceitas (qualquer um destes formatos funciona):
 *   - Header `Authorization: Bearer <user_id>:<chave>`
 *   - Headers separados: `X-User-Id: ...` + `X-User-Chave: ...`
 *   - Query string (fallback, só para teste): ?user_id=...&chave=...
 *
 * NUNCA loga valores. Em caso de falha: 401 sem detalhes.
 */

require_once __DIR__ . '/../../_comum/resposta.php';
require_once __DIR__ . '/../../_comum/rate_limit.php';
require_once __DIR__ . '/../../conexao/conexao.php';

function _http_header(string $nome): string
{
    $chave = 'HTTP_' . strtoupper(str_replace('-', '_', $nome));
    if (isset($_SERVER[$chave]) && $_SERVER[$chave] !== '') {
        return (string)$_SERVER[$chave];
    }
    // Apache + PHP-FPM em alguns hosts (incluindo o EasyPanel atual) movem
    // `Authorization` pra `REDIRECT_HTTP_AUTHORIZATION` quando passa por
    // mod_rewrite, e em outros casos só expõem via `apache_request_headers()`.
    // Sem este fallback, todo Authorization Bearer enviado pelo desktop chega
    // vazio aqui e dispara 401 indistinguível de credencial inválida.
    $chave_redirect = 'REDIRECT_' . $chave;
    if (isset($_SERVER[$chave_redirect]) && $_SERVER[$chave_redirect] !== '') {
        return (string)$_SERVER[$chave_redirect];
    }
    if (function_exists('apache_request_headers')) {
        $todos = apache_request_headers();
        if (is_array($todos)) {
            foreach ($todos as $k => $v) {
                if (strcasecmp($k, $nome) === 0 && $v !== '') {
                    return (string)$v;
                }
            }
        }
    }
    return '';
}

/**
 * Retorna o array do usuário autenticado ou encerra com 401.
 * Colunas retornadas: id_usuario, user_id, nome_exibicao, nivel, status_conta.
 */
function autenticar_cliente_ou_morrer(): array
{
    // Proteção anti-brute-force ANTES de tocar no banco:
    // Limita tentativas por IP, independente de ter ou não credencial.
    // 30 tentativas por 5 minutos por IP. Excedeu -> 429.
    $ip = obter_ip_cliente();
    rate_limit_proteger('auth_attempt:ip:' . $ip, 30, 300);

    $user_id = '';
    $chave   = '';

    // 1. Authorization: Bearer user:chave
    $auth = _http_header('Authorization');
    if ($auth !== '' && stripos($auth, 'Bearer ') === 0) {
        $v = trim(substr($auth, 7));
        $pos = strpos($v, ':');
        if ($pos !== false) {
            $user_id = substr($v, 0, $pos);
            $chave   = substr($v, $pos + 1);
        }
    }

    // 2. Headers separados
    if ($user_id === '') $user_id = _http_header('X-User-Id');
    if ($chave   === '') $chave   = _http_header('X-User-Chave');

    // 3. Query string (fallback)
    if ($user_id === '') $user_id = (string)($_GET['user_id'] ?? '');
    if ($chave   === '') $chave   = (string)($_GET['chave']   ?? '');

    $user_id = normalizar_user_id($user_id);
    $chave   = trim($chave);

    if ($user_id === '' || $chave === '') {
        responder_json(false, 'não autorizado', null, 401);
    }

    try {
        $pdo = obter_conexao_pdo();
        $stm = $pdo->prepare("SELECT id_usuario, user_id, nome_exibicao, nivel, status_conta
                                FROM usuarios
                               WHERE user_id = ? AND chave = ?
                               LIMIT 1");
        $stm->execute([$user_id, $chave]);
        $u = $stm->fetch();
    } catch (Throwable $e) {
        responder_json(false, 'falha interna', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
    }

    if (!$u) {
        // Contabiliza falha no bucket dedicado: 10 falhas em 5min por IP -> 429 nas próximas.
        rate_limit_proteger('auth_fail:ip:' . $ip, 10, 300);
        responder_json(false, 'não autorizado', null, 401);
    }
    if (strtolower((string)$u['status_conta']) !== 'ativa') {
        responder_json(false, 'conta inativa ou bloqueada', null, 403);
    }

    // Sucesso: aplica rate limit por usuário (separado do IP).
    // 120 requisições por minuto por usuário é suficiente para qualquer uso legítimo.
    rate_limit_proteger('consumo:user:' . $u['user_id'], 120, 60);
    // Rate limit adicional por IP (protege contra vários user_ids vindos do mesmo IP).
    rate_limit_proteger('consumo:ip:' . $ip, 300, 60);

    return $u;
}
