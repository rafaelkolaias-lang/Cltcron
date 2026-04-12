<?php
declare(strict_types=1);

/**
 * conexao.php
 * Conexão PDO (MySQL) usando credenciais fixas com fallback para ENV.
 */

function obter_variavel_de_ambiente(string $chave, string $padrao = ''): string
{
    $valor = getenv($chave);
    if ($valor === false || $valor === null || $valor === '') {
        return $padrao;
    }
    return (string) $valor;
}

function obter_conexao_pdo(): PDO
{
    // Credenciais (com fallback para ENV)
    $host = obter_variavel_de_ambiente('DB_HOST', '76.13.112.108');
    // Porta produção 3306 homologação 3307
    $porta = obter_variavel_de_ambiente('DB_PORT', '3306');
    $nome_banco = obter_variavel_de_ambiente('DB_NAME', 'dados');
    $usuario = obter_variavel_de_ambiente('DB_USER', 'kolaias');
    $senha = obter_variavel_de_ambiente('DB_PASS', 'kolaias');

    $dsn = sprintf(
        'mysql:host=%s;port=%s;dbname=%s;charset=utf8mb4',
        $host,
        $porta,
        $nome_banco
    );

    $opcoes = [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ];

    return new PDO($dsn, $usuario, $senha, $opcoes);
}
