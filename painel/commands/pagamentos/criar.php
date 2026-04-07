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

function validar_data_iso(?string $data): bool
{
    $data = trim((string)$data);
    if ($data === '') {
        return false;
    }

    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $data)) {
        return false;
    }

    $dt = DateTime::createFromFormat('Y-m-d', $data);
    return $dt && $dt->format('Y-m-d') === $data;
}

function normalizar_data_iso_ou_nulo($valor): ?string
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '') {
        return null;
    }

    if (!validar_data_iso($texto)) {
        return null;
    }

    return $texto;
}

function normalizar_decimal($valor): float
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '') {
        return 0.0;
    }

    $texto = str_replace('.', '', $texto);
    $texto = str_replace(',', '.', $texto);

    return (float)$texto;
}

try {
    $in = ler_json_entrada();

    $user_id = trim((string)($in['user_id'] ?? ''));
    $data_pagamento = trim((string)($in['data_pagamento'] ?? ''));
    $referencia_inicio = normalizar_data_iso_ou_nulo($in['referencia_inicio'] ?? null);
    $referencia_fim = normalizar_data_iso_ou_nulo($in['referencia_fim'] ?? null);
    $travado_ate_data = normalizar_data_iso_ou_nulo($in['travado_ate_data'] ?? null);
    $valor = normalizar_decimal($in['valor'] ?? 0);
    $observacao = trim((string)($in['observacao'] ?? ''));

    if ($user_id === '') {
        responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
    }

    if (!validar_data_iso($data_pagamento)) {
        responder_json(false, 'data_pagamento inválida (YYYY-MM-DD).', ['campo' => 'data_pagamento'], 400);
    }

    if ($valor <= 0) {
        responder_json(false, 'valor deve ser maior que zero.', ['campo' => 'valor'], 400);
    }

    if (($in['referencia_inicio'] ?? '') !== '' && $referencia_inicio === null) {
        responder_json(false, 'referencia_inicio inválida (YYYY-MM-DD).', ['campo' => 'referencia_inicio'], 400);
    }

    if (($in['referencia_fim'] ?? '') !== '' && $referencia_fim === null) {
        responder_json(false, 'referencia_fim inválida (YYYY-MM-DD).', ['campo' => 'referencia_fim'], 400);
    }

    if (($in['travado_ate_data'] ?? '') !== '' && $travado_ate_data === null) {
        responder_json(false, 'travado_ate_data inválida (YYYY-MM-DD).', ['campo' => 'travado_ate_data'], 400);
    }

    if ($referencia_inicio !== null && $referencia_fim !== null && $referencia_inicio > $referencia_fim) {
        responder_json(false, 'referencia_inicio não pode ser maior que referencia_fim.', ['campo' => 'referencia_inicio'], 400);
    }

    if ($travado_ate_data === null) {
        $travado_ate_data = $referencia_fim ?: $data_pagamento;
    }

    if (mb_strlen($observacao) > 255) {
        $observacao = mb_substr($observacao, 0, 255);
    }

    $pdo = obter_conexao_pdo();

    $stU = $pdo->prepare("
        SELECT id_usuario
        FROM usuarios
        WHERE user_id = :user_id
        LIMIT 1
    ");
    $stU->execute([':user_id' => $user_id]);
    $linhaU = $stU->fetch(PDO::FETCH_ASSOC);

    if (!$linhaU || !isset($linhaU['id_usuario'])) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }

    $id_usuario = (int)$linhaU['id_usuario'];

    $st = $pdo->prepare("
        INSERT INTO Pagamentos (
            id_usuario,
            data_pagamento,
            referencia_inicio,
            referencia_fim,
            travado_ate_data,
            valor,
            observacao
        )
        VALUES (
            :id_usuario,
            :data_pagamento,
            :referencia_inicio,
            :referencia_fim,
            :travado_ate_data,
            :valor,
            :observacao
        )
    ");

    $pdo->beginTransaction();

    $st->execute([
        ':id_usuario' => $id_usuario,
        ':data_pagamento' => $data_pagamento,
        ':referencia_inicio' => $referencia_inicio,
        ':referencia_fim' => $referencia_fim,
        ':travado_ate_data' => $travado_ate_data,
        ':valor' => number_format($valor, 2, '.', ''),
        ':observacao' => $observacao !== '' ? $observacao : null,
    ]);

    $id_pagamento = (int)$pdo->lastInsertId();

    // Travar subtarefas com referencia_data <= travado_ate_data para este membro
    $stLock = $pdo->prepare("
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 1,
            id_pagamento = :id_pag,
            bloqueada_em = NOW()
        WHERE user_id = :user_id
          AND referencia_data IS NOT NULL
          AND referencia_data <= :travado_ate
          AND bloqueada_pagamento = 0
    ");
    $stLock->execute([
        ':id_pag'      => $id_pagamento,
        ':user_id'     => $user_id,
        ':travado_ate' => $travado_ate_data,
    ]);
    $travadas = $stLock->rowCount();

    // Registrar no histórico de cada subtarefa travada
    $stIds = $pdo->prepare("
        SELECT id_subtarefa, user_id
        FROM atividades_subtarefas
        WHERE id_pagamento = :id_pag
    ");
    $stIds->execute([':id_pag' => $id_pagamento]);
    $subtsTravadas = $stIds->fetchAll(PDO::FETCH_ASSOC);

    if (count($subtsTravadas) > 0) {
        $stH = $pdo->prepare("
            INSERT INTO atividades_subtarefas_historico
                (id_subtarefa, acao, user_id_alvo, user_id_executor, dados_antes, dados_depois)
            VALUES
                (:id_sub, 'bloqueio_pagamento', :user_alvo, :user_exec, :antes, :depois)
        ");
        foreach ($subtsTravadas as $sub) {
            $stH->execute([
                ':id_sub'     => $sub['id_subtarefa'],
                ':user_alvo'  => $sub['user_id'],
                ':user_exec'  => $sub['user_id'],
                ':antes'      => json_encode(['bloqueada_pagamento' => false]),
                ':depois'     => json_encode(['bloqueada_pagamento' => true, 'id_pagamento' => $id_pagamento]),
            ]);
        }
    }

    $pdo->commit();

    responder_json(true, "Pagamento registrado. {$travadas} tarefa(s) travada(s).", [
        'id_pagamento' => $id_pagamento,
        'user_id' => $user_id,
        'id_usuario' => $id_usuario,
        'data_pagamento' => $data_pagamento,
        'referencia_inicio' => $referencia_inicio,
        'referencia_fim' => $referencia_fim,
        'travado_ate_data' => $travado_ate_data,
        'valor' => round($valor, 2),
        'observacao' => $observacao,
        'tarefas_travadas' => $travadas,
    ], 201);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao criar pagamento.', $dados, 500);
}