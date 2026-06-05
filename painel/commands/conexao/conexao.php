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
    // Credenciais (com fallback para ENV). Default = PRODUÇÃO (porta 3306).
    // Homologação remota = porta 3307. NÃO existe banco MySQL local por padrão.
    $cfg = [
        'host'  => obter_variavel_de_ambiente('DB_HOST', '76.13.112.108'),
        'porta' => obter_variavel_de_ambiente('DB_PORT', '3306'),
        'nome'  => obter_variavel_de_ambiente('DB_NAME', 'dados'),
        'user'  => obter_variavel_de_ambiente('DB_USER', 'kolaias'),
        'senha' => obter_variavel_de_ambiente('DB_PASS', 'kolaias'),
    ];

    // Override LOCAL de desenvolvimento — arquivo NÃO versionado (ver .gitignore).
    // Se existir, seus valores substituem os de cima. Permite apontar o painel
    // para um MySQL local (ex.: XAMPP root sem senha, banco clonado) sem editar
    // este arquivo versionado — então a produção continua sendo o default no git
    // e não há "restaurar antes de commitar". O array pode conter qualquer
    // subconjunto de: host, porta, nome, user, senha.
    $arquivo_local = __DIR__ . '/conexao.local.php';
    if (is_file($arquivo_local)) {
        $override = require $arquivo_local;
        if (is_array($override)) {
            $cfg = array_merge($cfg, $override);
        }
    }

    $host = $cfg['host'];
    $porta = $cfg['porta'];
    $nome_banco = $cfg['nome'];
    $usuario = $cfg['user'];
    $senha = $cfg['senha'];

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
