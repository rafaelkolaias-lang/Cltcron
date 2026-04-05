<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    $st = $pdo->prepare("
        SELECT id_usuario, user_id, nome_exibicao, nivel, valor_hora, status_conta, atualizado_em
        FROM usuarios
        WHERE status_conta = 'ativa'
        ORDER BY nome_exibicao ASC, user_id ASC
    ");
    $st->execute();

    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar usuários ativos', ['erro' => $e->getMessage()], 500);
}
