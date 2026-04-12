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
    if ($data === '' || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $data)) return false;
    $dt = DateTime::createFromFormat('Y-m-d', $data);
    return $dt && $dt->format('Y-m-d') === $data;
}

function normalizar_data_iso_ou_nulo($valor): ?string
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '' || !validar_data_iso($texto)) return null;
    return $texto;
}

function normalizar_decimal($valor): float
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '') return 0.0;
    $texto = str_replace('.', '', $texto);
    $texto = str_replace(',', '.', $texto);
    return (float)$texto;
}

try {
    $in = ler_json_entrada();

    $id_pagamento = (int)($in['id_pagamento'] ?? 0);
    if ($id_pagamento <= 0) {
        responder_json(false, 'id_pagamento inválido.', ['campo' => 'id_pagamento'], 400);
    }

    $pdo = obter_conexao_pdo();

    // Buscar pagamento existente
    $stE = $pdo->prepare("SELECT * FROM Pagamentos WHERE id_pagamento = :id LIMIT 1");
    $stE->execute([':id' => $id_pagamento]);
    $existente = $stE->fetch(PDO::FETCH_ASSOC);

    if (!$existente) {
        responder_json(false, 'Pagamento não encontrado.', ['id_pagamento' => $id_pagamento], 404);
    }

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
        responder_json(false, 'Apenas os 2 últimos pagamentos podem ser editados.', ['id_pagamento' => $id_pagamento], 403);
    }

    // Campos editáveis
    $campos = [];
    $params = [];

    if (isset($in['data_pagamento'])) {
        $data_pagamento = trim((string)$in['data_pagamento']);
        if (!validar_data_iso($data_pagamento)) {
            responder_json(false, 'data_pagamento inválida (YYYY-MM-DD).', ['campo' => 'data_pagamento'], 400);
        }
        $campos[] = 'data_pagamento = :data_pagamento';
        $params[':data_pagamento'] = $data_pagamento;
    }

    if (array_key_exists('referencia_inicio', $in)) {
        $referencia_inicio = normalizar_data_iso_ou_nulo($in['referencia_inicio']);
        $campos[] = 'referencia_inicio = :referencia_inicio';
        $params[':referencia_inicio'] = $referencia_inicio;
    }

    if (array_key_exists('referencia_fim', $in)) {
        $referencia_fim = normalizar_data_iso_ou_nulo($in['referencia_fim']);
        $campos[] = 'referencia_fim = :referencia_fim';
        $params[':referencia_fim'] = $referencia_fim;
    }

    if (array_key_exists('travado_ate_data', $in)) {
        $travado_ate_data = normalizar_data_iso_ou_nulo($in['travado_ate_data']);
        $campos[] = 'travado_ate_data = :travado_ate_data';
        $params[':travado_ate_data'] = $travado_ate_data;
    }

    if (isset($in['valor'])) {
        $valor = normalizar_decimal($in['valor']);
        if ($valor <= 0) {
            responder_json(false, 'valor deve ser maior que zero.', ['campo' => 'valor'], 400);
        }
        $campos[] = 'valor = :valor';
        $params[':valor'] = number_format($valor, 2, '.', '');
    }

    if (array_key_exists('observacao', $in)) {
        $observacao = trim((string)($in['observacao'] ?? ''));
        if (mb_strlen($observacao) > 255) $observacao = mb_substr($observacao, 0, 255);
        $campos[] = 'observacao = :observacao';
        $params[':observacao'] = $observacao !== '' ? $observacao : null;
    }

    if (empty($campos)) {
        responder_json(false, 'Nenhum campo para atualizar.', null, 400);
    }

    $params[':id'] = $id_pagamento;
    $sql = "UPDATE Pagamentos SET " . implode(', ', $campos) . " WHERE id_pagamento = :id";

    // Verificar se campos de período/data mudaram (requer reprocessamento de travas)
    $campos_periodo = ['referencia_inicio', 'referencia_fim', 'travado_ate_data', 'data_pagamento'];
    $periodo_mudou = false;
    foreach ($campos_periodo as $cp) {
        if (array_key_exists($cp, $in)) {
            $periodo_mudou = true;
            break;
        }
    }

    // Obter user_id textual do dono do pagamento
    $stUser = $pdo->prepare("
        SELECT u.user_id
        FROM usuarios u
        JOIN Pagamentos p ON p.id_usuario = u.id_usuario
        WHERE p.id_pagamento = :id
        LIMIT 1
    ");
    $stUser->execute([':id' => $id_pagamento]);
    $linhaUser = $stUser->fetch(PDO::FETCH_ASSOC);
    $user_id = $linhaUser['user_id'] ?? '';

    $pdo->beginTransaction();
    $st = $pdo->prepare($sql);
    $st->execute($params);

    // Se campos de período mudaram, reprocessar todos os pagamentos do usuário
    if ($periodo_mudou && $user_id !== '') {
        pagamento_reprocessar_todos($pdo, (int)$existente['id_usuario'], $user_id);
    }

    $pdo->commit();

    // Retornar pagamento atualizado
    $stR = $pdo->prepare("SELECT * FROM Pagamentos WHERE id_pagamento = :id LIMIT 1");
    $stR->execute([':id' => $id_pagamento]);
    $atualizado = $stR->fetch(PDO::FETCH_ASSOC);

    responder_json(true, 'Pagamento atualizado.', $atualizado, 200);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao editar pagamento.', $dados, 500);
}
