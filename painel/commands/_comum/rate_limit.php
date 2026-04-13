<?php
declare(strict_types=1);

/**
 * rate_limit.php — rate limiting simples baseado em arquivos.
 *
 * Janela deslizante por "chave" (ex.: "obter:user:rafael" ou "auth_fail:ip:1.2.3.4").
 * Cada chave vira um arquivo JSON em painel/logs/ratelimit/<sha1>.json contendo
 * somente os timestamps dentro da janela atual.
 *
 * Concorrência: `flock` exclusivo no arquivo. Bom para 1 servidor. Para múltiplos
 * servidores, migrar para Redis ou tabela MySQL (ver Fase 3 avançada).
 *
 * Uso típico:
 *   rate_limit_proteger('obter:user:' . $u['user_id'], 60, 60);   // 60/min
 *   rate_limit_proteger('obter:ip:'   . $ip,            120, 60); // 120/min
 *
 * Em caso de excesso: responde 429 e encerra (responder_json).
 * Não loga valores sensíveis — só a chave abstrata.
 */

require_once __DIR__ . '/resposta.php';

function _rate_dir(): string
{
    $dir = dirname(__DIR__, 2) . DIRECTORY_SEPARATOR . 'logs' . DIRECTORY_SEPARATOR . 'ratelimit';
    if (!is_dir($dir)) {
        @mkdir($dir, 0775, true);
    }
    return $dir;
}

function _rate_arquivo(string $chave): string
{
    return _rate_dir() . DIRECTORY_SEPARATOR . sha1($chave) . '.json';
}

/**
 * Retorna ['permitido'=>bool, 'restante'=>int, 'reset_em'=>int]
 * e registra o hit se permitido.
 */
function rate_limit_consumir(string $chave, int $max_req, int $janela_s): array
{
    $agora = time();
    $inicio_janela = $agora - $janela_s;
    $arq = _rate_arquivo($chave);

    $fp = @fopen($arq, 'c+');
    if (!$fp) {
        // falha ao abrir arquivo: não bloqueia (fail-open). Logar em error_log.
        error_log('[rate_limit] falha ao abrir ' . $arq);
        return ['permitido' => true, 'restante' => $max_req - 1, 'reset_em' => $agora + $janela_s];
    }

    try {
        flock($fp, LOCK_EX);
        $conteudo = stream_get_contents($fp);
        $stamps = [];
        if ($conteudo !== false && $conteudo !== '') {
            $decoded = json_decode($conteudo, true);
            if (is_array($decoded)) $stamps = $decoded;
        }

        // mantém apenas timestamps dentro da janela
        $stamps = array_values(array_filter($stamps, static fn($t) => (int)$t >= $inicio_janela));

        if (count($stamps) >= $max_req) {
            $reset_em = (int)$stamps[0] + $janela_s;
            return ['permitido' => false, 'restante' => 0, 'reset_em' => $reset_em];
        }

        $stamps[] = $agora;

        // regrava
        ftruncate($fp, 0);
        rewind($fp);
        fwrite($fp, json_encode($stamps));
        fflush($fp);

        return [
            'permitido' => true,
            'restante'  => $max_req - count($stamps),
            'reset_em'  => $agora + $janela_s,
        ];
    } finally {
        flock($fp, LOCK_UN);
        fclose($fp);
    }
}

/**
 * Aplica rate limit — encerra a requisição com 429 se exceder.
 * Adiciona cabeçalhos `X-RateLimit-*` sempre.
 */
function rate_limit_proteger(string $chave, int $max_req, int $janela_s): void
{
    $r = rate_limit_consumir($chave, $max_req, $janela_s);

    if (!headers_sent()) {
        header('X-RateLimit-Limit: ' . $max_req);
        header('X-RateLimit-Remaining: ' . max(0, (int)$r['restante']));
        header('X-RateLimit-Reset: ' . (int)$r['reset_em']);
    }

    if (!$r['permitido']) {
        $retry = max(1, (int)$r['reset_em'] - time());
        if (!headers_sent()) {
            header('Retry-After: ' . $retry);
        }
        responder_json(false, 'rate limit excedido', [
            'retry_em_s' => $retry,
        ], 429);
    }
}

/**
 * Apenas conta um hit sem bloquear (para métricas/brute-force soft).
 * Retorna quantos hits existem na janela DEPOIS de registrar este.
 */
function rate_limit_contar(string $chave, int $janela_s): int
{
    $r = rate_limit_consumir($chave, PHP_INT_MAX, $janela_s);
    // hits na janela = max - restante
    return PHP_INT_MAX - (int)$r['restante'];
}

/**
 * Devolve IP cliente considerando proxy reverso comum (se configurado).
 * Fallback seguro: REMOTE_ADDR.
 */
function obter_ip_cliente(): string
{
    $candidatos = [];
    if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
        $partes = explode(',', (string)$_SERVER['HTTP_X_FORWARDED_FOR']);
        $candidatos[] = trim($partes[0]);
    }
    if (!empty($_SERVER['HTTP_X_REAL_IP'])) {
        $candidatos[] = trim((string)$_SERVER['HTTP_X_REAL_IP']);
    }
    $candidatos[] = (string)($_SERVER['REMOTE_ADDR'] ?? '');
    foreach ($candidatos as $ip) {
        if ($ip !== '' && filter_var($ip, FILTER_VALIDATE_IP)) return $ip;
    }
    return '0.0.0.0';
}
