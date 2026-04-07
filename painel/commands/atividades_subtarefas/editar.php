<?php
// commands/atividades_subtarefas/editar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $in = ler_json_do_corpo();

    $id_subtarefa = (int)($in['id_subtarefa'] ?? 0);
    $titulo       = trim((string)($in['titulo']       ?? ''));
    $canal        = isset($in['canal_entrega']) ? trim((string)$in['canal_entrega']) : null;
    $observacao   = isset($in['observacao'])   ? trim((string)$in['observacao'])   : null;
    $concluida    = isset($in['concluida'])    ? (bool)$in['concluida']            : null;
    $segundos     = isset($in['segundos_gastos']) ? (int)$in['segundos_gastos']    : null;

    if ($id_subtarefa <= 0) {
        responder_json(false, 'id_subtarefa inválido.', null, 400);
    }
    if ($titulo === '' || mb_strlen($titulo) < 2) {
        responder_json(false, 'Título inválido (mínimo 2 caracteres).', null, 400);
    }
    if ($segundos !== null && $segundos < 0) {
        responder_json(false, 'segundos_gastos não pode ser negativo.', null, 400);
    }

    $pdo = obter_conexao_pdo();

    // Verifica existência e trava de pagamento
    $stV = $pdo->prepare("
        SELECT id_subtarefa, bloqueada_pagamento, titulo, canal_entrega,
               concluida, segundos_gastos, observacao, user_id, id_atividade
        FROM atividades_subtarefas
        WHERE id_subtarefa = :id
        LIMIT 1
    ");
    $stV->execute([':id' => $id_subtarefa]);
    $atual = $stV->fetch(PDO::FETCH_ASSOC);

    if (!$atual) {
        responder_json(false, 'Tarefa não encontrada.', null, 404);
    }
    if ((int)($atual['bloqueada_pagamento'] ?? 0) === 1) {
        responder_json(false, 'Esta tarefa está bloqueada por pagamento e não pode ser editada.', null, 403);
    }

    // Monta SET dinâmico apenas com campos enviados
    $sets   = ['titulo = :titulo'];
    $params = [':titulo' => $titulo, ':id' => $id_subtarefa];

    if ($canal !== null) {
        $sets[] = 'canal_entrega = :canal';
        $params[':canal'] = $canal !== '' ? $canal : null;
    }
    if ($observacao !== null) {
        $sets[] = 'observacao = :observacao';
        $params[':observacao'] = $observacao !== '' ? $observacao : null;
    }
    if ($concluida !== null) {
        $sets[] = 'concluida = :concluida';
        $sets[] = 'concluida_em = :concluida_em';
        $params[':concluida']    = $concluida ? 1 : 0;
        $params[':concluida_em'] = $concluida ? date('Y-m-d H:i:s') : null;
    }
    if ($segundos !== null) {
        $sets[] = 'segundos_gastos = :segundos';
        $params[':segundos'] = $segundos;
    }

    $pdo->beginTransaction();

    // Snapshot antes
    $dados_antes = [
        'titulo'         => $atual['titulo'],
        'canal_entrega'  => $atual['canal_entrega'],
        'concluida'      => (bool)$atual['concluida'],
        'segundos_gastos' => (int)$atual['segundos_gastos'],
        'observacao'     => $atual['observacao'],
    ];

    $sql = 'UPDATE atividades_subtarefas SET ' . implode(', ', $sets) . ' WHERE id_subtarefa = :id';
    $stU = $pdo->prepare($sql);
    $stU->execute($params);

    // Snapshot depois
    $stD = $pdo->prepare("
        SELECT titulo, canal_entrega, concluida, segundos_gastos, observacao
        FROM atividades_subtarefas WHERE id_subtarefa = :id LIMIT 1
    ");
    $stD->execute([':id' => $id_subtarefa]);
    $depois = $stD->fetch(PDO::FETCH_ASSOC);

    $dados_depois = [
        'titulo'          => $depois['titulo'],
        'canal_entrega'   => $depois['canal_entrega'],
        'concluida'       => (bool)$depois['concluida'],
        'segundos_gastos' => (int)$depois['segundos_gastos'],
        'observacao'      => $depois['observacao'],
    ];

    // Registra histórico
    $stH = $pdo->prepare("
        INSERT INTO atividades_subtarefas_historico
            (id_subtarefa, acao, user_id_alvo, user_id_executor, dados_antes, dados_depois)
        VALUES
            (:id_sub, 'edicao', :user_alvo, 'painel_adm', :antes, :depois)
    ");
    $stH->execute([
        ':id_sub'    => $id_subtarefa,
        ':user_alvo' => (string)($atual['user_id'] ?? ''),
        ':antes'     => json_encode($dados_antes, JSON_UNESCAPED_UNICODE),
        ':depois'    => json_encode($dados_depois, JSON_UNESCAPED_UNICODE),
    ]);

    $pdo->commit();

    responder_json(true, 'Tarefa atualizada com sucesso.', ['id_subtarefa' => $id_subtarefa], 200);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao editar tarefa.', $dados, 500);
}
