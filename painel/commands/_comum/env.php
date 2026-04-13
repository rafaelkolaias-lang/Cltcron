<?php
declare(strict_types=1);

/**
 * env.php — carregador simples de variáveis de ambiente a partir de arquivo .env local.
 *
 * Procura .env em (nesta ordem):
 *   1. painel/.env
 *   2. raiz do projeto (..//..//..//.env)
 *
 * Não versionado. Usado para APP_SECRETS_MASTER_KEY e afins.
 * Só define variáveis se ainda não existirem no ambiente (ENV real tem precedência).
 */

function _env_carregar_arquivo(string $caminho): void
{
    if (!is_file($caminho) || !is_readable($caminho)) {
        return;
    }
    $linhas = @file($caminho, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if (!is_array($linhas)) {
        return;
    }
    foreach ($linhas as $linha) {
        $linha = trim($linha);
        if ($linha === '' || $linha[0] === '#') {
            continue;
        }
        $pos = strpos($linha, '=');
        if ($pos === false) {
            continue;
        }
        $chave = trim(substr($linha, 0, $pos));
        $valor = trim(substr($linha, $pos + 1));
        // remove aspas simples/duplas envolventes
        if (strlen($valor) >= 2) {
            $primeiro = $valor[0];
            $ultimo   = $valor[strlen($valor) - 1];
            if (($primeiro === '"' && $ultimo === '"') || ($primeiro === "'" && $ultimo === "'")) {
                $valor = substr($valor, 1, -1);
            }
        }
        if ($chave === '' || getenv($chave) !== false) {
            continue;
        }
        putenv("$chave=$valor");
        $_ENV[$chave] = $valor;
    }
}

function carregar_env_local(): void
{
    static $carregado = false;
    if ($carregado) {
        return;
    }
    $carregado = true;

    $base_painel = dirname(__DIR__, 2);               // .../painel
    $base_projeto = dirname($base_painel);            // raiz do projeto

    _env_carregar_arquivo($base_painel . DIRECTORY_SEPARATOR . '.env');
    _env_carregar_arquivo($base_projeto . DIRECTORY_SEPARATOR . '.env');
}

carregar_env_local();
