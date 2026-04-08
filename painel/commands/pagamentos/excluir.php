<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function ler_json_entrada(): array
{
    $raw = file_get_contents('php://input');
    $obj = json_decode($raw ?: '', true);
    return is_array($obj) ? $obj : [];
}

try {
    $in = ler_json_entrada();
    $id_pagamento = (int)($in['id_pagamento'] ?? 0);

    if ($id_pagamento <= 0) {
        responder_json(false, 'id_pagamento inválido.', null, 400);
    }

    $pdo = obter_conexao_pdo();

    // Verificar existência
    $stE = $pdo->prepare("SELECT id_pagamento, id_usuario FROM Pagamentos WHERE id_pagamento = :id LIMIT 1");
    $stE->execute([':id' => $id_pagamento]);
    $existente = $stE->fetch(PDO::FETCH_ASSOC);

    if (!$existente) {
        responder_json(false, 'Pagamento não encontrado.', ['id_pagamento' => $id_pagamento], 404);
    }

    $pdo->beginTransaction();

    // Destravar subtarefas que foram travadas por este pagamento
    $stUnlock = $pdo->prepare("
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 0,
            id_pagamento = NULL,
            bloqueada_em = NULL
        WHERE id_pagamento = :id_pag
    ");
    $stUnlock->execute([':id_pag' => $id_pagamento]);
    $destravadas = $stUnlock->rowCount();

    // Excluir pagamento
    $stD = $pdo->prepare("DELETE FROM Pagamentos WHERE id_pagamento = :id");
    $stD->execute([':id' => $id_pagamento]);

    $pdo->commit();

    responder_json(true, "Pagamento excluído. {$destravadas} tarefa(s) destravada(s).", [
        'id_pagamento' => $id_pagamento,
        'tarefas_destravadas' => $destravadas,
    ], 200);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao excluir pagamento.', $dados, 500);
}
