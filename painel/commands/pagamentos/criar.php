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
    // Se já chegou como número (float/int via JSON), usa direto
    if (is_int($valor) || is_float($valor)) {
        return (float)$valor;
    }

    $texto = trim((string)($valor ?? ''));
    if ($texto === '') {
        return 0.0;
    }

    // Formato BRL com vírgula decimal (ex: "559,02" ou "R$ 1.559,02")
    if (str_contains($texto, ',')) {
        $texto = str_replace('.', '', $texto);  // remove separador de milhar
        $texto = str_replace(',', '.', $texto); // vírgula → ponto decimal
    } else {
        // Já está no formato decimal (ex: "559.02") — remove só caracteres não numéricos exceto ponto
        $texto = preg_replace('/[^\d.]/', '', $texto);
    }

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

    // Garantir coluna id_pagamento em registros_tempo (ANTES da transação — ALTER TABLE causa commit implícito)
    try {
        $pdo->exec("ALTER TABLE registros_tempo ADD COLUMN id_pagamento INT NULL DEFAULT NULL");
    } catch (Throwable $ignore) {
        // Coluna já existe — ok
    }

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

    // Travar subtarefas e marcar registros_tempo por referencia_data (período do pagamento)
    $resultado = pagamento_aplicar(
        $pdo,
        $id_pagamento,
        $user_id,
        $travado_ate_data,
        $referencia_inicio,
        $referencia_fim,
        true
    );
    $travadas = $resultado['subtarefas'];
    $horasMarcadas = $resultado['registros'];

    $pdo->commit();

    responder_json(true, "Pagamento registrado. {$travadas} tarefa(s) travada(s). {$horasMarcadas} registro(s) de tempo marcado(s).", [
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