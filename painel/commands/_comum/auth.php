<?php
declare(strict_types=1);

/**
 * auth.php — Autenticação do painel administrativo.
 *
 * Credenciais hardcoded com senha em bcrypt.
 * Suporta "permanecer logado" via token persistente em arquivo.
 */

define('PAINEL_USUARIO', 'admin');
define('PAINEL_SENHA_HASH', '$2y$10$yS2PsiiaUFiURmt1n3twduoB04QYcd/rtBR0dMqGpg2EzqrDgh2E2');
define('PAINEL_LEMBRAR_DIAS', 30);
define('PAINEL_TOKENS_FILE', __DIR__ . '/.tokens.json');
define('PAINEL_COOKIE_LEMBRAR', 'painel_lembrar');

function _painel_iniciar_sessao(): void
{
    if (session_status() === PHP_SESSION_NONE) {
        ini_set('session.gc_maxlifetime', (string)(PAINEL_LEMBRAR_DIAS * 86400));
        session_set_cookie_params([
            'lifetime' => 0,
            'path'     => '/',
            'httponly' => true,
            'samesite' => 'Strict',
        ]);
        session_start();
    }
}

function esta_logado(): bool
{
    _painel_iniciar_sessao();

    if (isset($_SESSION['painel_logado']) && $_SESSION['painel_logado'] === true) {
        return true;
    }

    // Verifica token "permanecer logado"
    $token = $_COOKIE[PAINEL_COOKIE_LEMBRAR] ?? '';
    if ($token !== '') {
        $tokens = _painel_ler_tokens();
        if (isset($tokens[$token]) && (int)$tokens[$token] > time()) {
            $_SESSION['painel_logado'] = true;
            return true;
        }
        // Token inválido ou expirado — limpa cookie
        setcookie(PAINEL_COOKIE_LEMBRAR, '', time() - 3600, '/', '', false, true);
    }

    return false;
}

/**
 * Usado nos endpoints da API. Retorna 401 JSON se não autenticado.
 */
function verificar_sessao_painel(): void
{
    _painel_iniciar_sessao();
    if (!esta_logado()) {
        http_response_code(401);
        if (!headers_sent()) {
            header('Content-Type: application/json; charset=utf-8');
        }
        echo json_encode(['ok' => false, 'mensagem' => 'não autorizado', 'dados' => null], JSON_UNESCAPED_UNICODE);
        exit;
    }
}

function fazer_login(string $usuario, string $senha, bool $lembrar): bool
{
    if ($usuario !== PAINEL_USUARIO) {
        return false;
    }
    if (!password_verify($senha, PAINEL_SENHA_HASH)) {
        return false;
    }

    _painel_iniciar_sessao();
    session_regenerate_id(true);
    $_SESSION['painel_logado'] = true;

    if ($lembrar) {
        $token = bin2hex(random_bytes(32));
        $tokens = _painel_ler_tokens();
        $tokens[$token] = time() + PAINEL_LEMBRAR_DIAS * 86400;
        _painel_salvar_tokens($tokens);
        setcookie(
            PAINEL_COOKIE_LEMBRAR,
            $token,
            time() + PAINEL_LEMBRAR_DIAS * 86400,
            '/',
            '',
            false,
            true
        );
    }

    return true;
}

function fazer_logout(): void
{
    _painel_iniciar_sessao();

    $token = $_COOKIE[PAINEL_COOKIE_LEMBRAR] ?? '';
    if ($token !== '') {
        $tokens = _painel_ler_tokens();
        unset($tokens[$token]);
        _painel_salvar_tokens($tokens);
        setcookie(PAINEL_COOKIE_LEMBRAR, '', time() - 3600, '/', '', false, true);
    }

    $_SESSION = [];
    if (session_status() === PHP_SESSION_ACTIVE) {
        session_destroy();
    }
}

function _painel_ler_tokens(): array
{
    if (!file_exists(PAINEL_TOKENS_FILE)) {
        return [];
    }
    $conteudo = file_get_contents(PAINEL_TOKENS_FILE);
    if ($conteudo === false || $conteudo === '') {
        return [];
    }
    return json_decode($conteudo, true) ?: [];
}

function _painel_salvar_tokens(array $tokens): void
{
    // Remove tokens expirados antes de salvar
    $agora = time();
    $tokens = array_filter($tokens, static fn($exp) => (int)$exp > $agora);
    file_put_contents(PAINEL_TOKENS_FILE, json_encode($tokens));
}
