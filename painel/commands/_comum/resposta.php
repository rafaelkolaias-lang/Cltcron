<?php
declare(strict_types=1);

/**
 * resposta.php (completo e atualizado)
 *
 * O que este arquivo faz:
 * - Responde JSON padronizado { ok, mensagem, dados }
 * - Ativa logs de erro do PHP em arquivo (sem quebrar JSON com HTML)
 * - Possibilita "debug" apenas por ENV: APP_DEBUG=1
 *
 * Obs:
 * - Não exibimos erros como HTML (display_errors=0) para não corromper JSON.
 * - Os erros vão para logs/painel_php_errors.log
 */

if (!headers_sent()) {
    header('Content-Type: application/json; charset=utf-8');
}

// ==========================================================
// DEBUG / LOGS
// ==========================================================
function debug_ativo(): bool
{
    // Apenas variável de ambiente — querystring e header removidos por segurança
    $env = getenv('APP_DEBUG');
    return ($env !== false && (string)$env === '1');
}

function caminho_log_php(): string
{
    // __DIR__ = painel/commands/_comum
    // queremos: painel/logs/painel_php_errors.log
    $dir_logs = dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'logs';

    if (!is_dir($dir_logs)) {
        // tenta criar sem “gritar” se falhar
        @mkdir($dir_logs, 0775, true);
    }

    return $dir_logs . DIRECTORY_SEPARATOR . 'painel_php_errors.log';
}

function configurar_erro_php(): void
{
    // Não imprimir HTML de erro no meio do JSON
    ini_set('display_errors', '0');
    ini_set('html_errors', '0');

    // Logar erros
    ini_set('log_errors', '1');
    ini_set('error_log', caminho_log_php());

    // Log completo
    error_reporting(E_ALL);
}

// chama sempre ao carregar o arquivo
configurar_erro_php();

/**
 * Handler global (ajuda a capturar warnings/notices e tratar como erro)
 * -> Isso faz o try/catch pegar problemas que antes viravam só warning.
 */
set_error_handler(function (int $severity, string $message, string $file, int $line): bool {
    // respeita @ (erro suprimido)
    if (!(error_reporting() & $severity)) return true;
    throw new ErrorException($message, 0, $severity, $file, $line);
});

/**
 * Caso aconteça um "fatal error" fora de try/catch,
 * garantimos que a resposta seja JSON.
 */
register_shutdown_function(function (): void {
    $err = error_get_last();
    if (!$err) return;

    $tipos_fatais = [E_ERROR, E_PARSE, E_CORE_ERROR, E_COMPILE_ERROR];
    if (!in_array((int)$err['type'], $tipos_fatais, true)) return;

    // limpa qualquer saída anterior (evita HTML quebrando JSON)
    while (ob_get_level() > 0) {
        @ob_end_clean();
    }

    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');

    $dados = null;
    if (debug_ativo()) {
        $dados = [
            'erro' => (string)($err['message'] ?? 'Erro fatal'),
            'arquivo' => (string)($err['file'] ?? ''),
            'linha' => (int)($err['line'] ?? 0),
            'tipo' => (int)($err['type'] ?? 0),
            'log' => caminho_log_php(),
        ];
    }

    echo json_encode([
        'ok' => false,
        'mensagem' => 'erro fatal no servidor',
        'dados' => $dados,
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
});

// ==========================================================
// RESPOSTA JSON
// ==========================================================
function responder_json(bool $ok, string $mensagem, $dados = null, int $codigo_http = 200): void
{
    http_response_code($codigo_http);

    if (!headers_sent()) {
        header('Content-Type: application/json; charset=utf-8');
        header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
    }

    $payload = [
        'ok' => $ok,
        'mensagem' => $mensagem,
        'dados' => $dados ?? null,
    ];

    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

// ==========================================================
// HELPERS
// ==========================================================
function ler_json_do_corpo(): array
{
    $bruto = file_get_contents('php://input');
    if ($bruto === false || trim($bruto) === '') return [];

    $obj = json_decode($bruto, true);
    return is_array($obj) ? $obj : [];
}

function normalizar_user_id(string $valor): string
{
    $v = strtolower(trim($valor));
    $v = preg_replace('/[^a-z0-9_\-\.]/', '', $v) ?? '';
    return (string)$v;
}

function nivel_valido(string $nivel): bool
{
    $n = strtolower(trim($nivel));
    return in_array($n, ['iniciante','intermediario','avancado'], true);
}

function status_conta_valido(string $status): bool
{
    $s = strtolower(trim($status));
    return in_array($s, ['ativa','inativa','bloqueada'], true);
}

function situacao_valida(string $situacao): bool
{
    $s = strtolower(trim($situacao));
    return in_array($s, ['trabalhando','ocioso','pausado'], true);
}
