<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $entrada = ler_json_do_corpo();
    $user_id = normalizar_user_id((string)($entrada['user_id'] ?? ''));

    if ($user_id === '') {
        responder_json(false, "user_id inválido", null, 400);
    }

    $pdo = obter_conexao_pdo();

    $stm = $pdo->prepare("UPDATE usuarios SET status_conta = 'inativa' WHERE user_id = :user_id LIMIT 1");
    $stm->execute([':user_id' => $user_id]);

    if ($stm->rowCount() <= 0) {
        responder_json(false, "Usuário não encontrado", ['user_id' => $user_id], 404);
    }

    responder_json(true, "Usuário inativado", ['user_id' => $user_id]);
} catch (Throwable $e) {
    responder_json(false, "falha ao excluir usuário", ['erro' => $e->getMessage()], 500);
}
