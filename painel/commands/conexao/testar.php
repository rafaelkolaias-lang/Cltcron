<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

try {
    $caminho_conexao = __DIR__ . '/conexao.php';

    if (!file_exists($caminho_conexao)) {
        http_response_code(500);
        echo json_encode(
            ['ok' => false, 'mensagem' => 'Arquivo conexao.php não encontrado.', 'dados' => ['caminho' => $caminho_conexao]],
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
        );
        exit;
    }

    require_once $caminho_conexao;

    if (!function_exists('obter_conexao_pdo')) {
        http_response_code(500);
        echo json_encode(
            ['ok' => false, 'mensagem' => 'Função obter_conexao_pdo() não foi carregada.', 'dados' => ['arquivo' => $caminho_conexao]],
            JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
        );
        exit;
    }

    $pdo = obter_conexao_pdo();
    $pdo->query('SELECT 1');

    echo json_encode(
        ['ok' => true, 'mensagem' => 'conexao com sucesso'],
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
    );
} catch (Throwable $e) {
    http_response_code(500);
    echo json_encode(
        ['ok' => false, 'mensagem' => 'falha na conexao', 'dados' => ['erro' => $e->getMessage()]],
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
    );
}
