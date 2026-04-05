<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    $sql = "SELECT id_usuario, user_id, nome_exibicao, nivel, valor_hora, chave, status_conta, criado_em, atualizado_em
            FROM usuarios
            ORDER BY user_id ASC";
    $stm = $pdo->prepare($sql);
    $stm->execute();

    $dados = $stm->fetchAll();
    responder_json(true, "OK", $dados);
} catch (Throwable $e) {
    responder_json(false, "falha na conexao", ['erro' => $e->getMessage()], 500);
}
