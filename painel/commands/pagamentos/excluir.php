<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_aplicar_pagamento.php';

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
    $stE = $pdo->prepare("
        SELECT p.id_pagamento, p.id_usuario, u.user_id
        FROM Pagamentos p
        JOIN usuarios u ON u.id_usuario = p.id_usuario
        WHERE p.id_pagamento = :id
        LIMIT 1
    ");
    $stE->execute([':id' => $id_pagamento]);
    $existente = $stE->fetch(PDO::FETCH_ASSOC);

    if (!$existente) {
        responder_json(false, 'Pagamento não encontrado.', ['id_pagamento' => $id_pagamento], 404);
    }

    $user_id = $existente['user_id'];

    // Verificar se está entre os 2 últimos pagamentos do usuário
    $stUltimos = $pdo->prepare("
        SELECT id_pagamento
        FROM Pagamentos
        WHERE id_usuario = :id_usuario
        ORDER BY data_pagamento DESC, id_pagamento DESC
        LIMIT 2
    ");
    $stUltimos->execute([':id_usuario' => $existente['id_usuario']]);
    $ultimos = array_map('intval', array_column($stUltimos->fetchAll(PDO::FETCH_ASSOC), 'id_pagamento'));

    if (!in_array($id_pagamento, $ultimos, true)) {
        responder_json(false, 'Apenas os 2 últimos pagamentos podem ser excluídos.', ['id_pagamento' => $id_pagamento], 403);
    }

    $id_usuario = (int)$existente['id_usuario'];

    $pdo->beginTransaction();

    // Desvincular subtarefas e registros_tempo deste pagamento
    $limpos = pagamento_desvincular($pdo, $id_pagamento);

    // Excluir pagamento
    $stD = $pdo->prepare("DELETE FROM Pagamentos WHERE id_pagamento = :id");
    $stD->execute([':id' => $id_pagamento]);

    // Reprocessar pagamentos restantes do usuário para reavaliar cobertura
    pagamento_reprocessar_todos($pdo, $id_usuario, $user_id);

    $pdo->commit();

    responder_json(true, "Pagamento excluído. Vínculos reprocessados.", [
        'id_pagamento' => $id_pagamento,
        'tarefas_desvinculadas' => $limpos['subtarefas'],
        'registros_desvinculados' => $limpos['registros'],
        'abatimentos_apagados' => $limpos['abatimentos'] ?? 0,
    ], 200);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao excluir pagamento.', $dados, 500);
}
