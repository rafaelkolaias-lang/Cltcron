<?php
declare(strict_types=1);

/**
 * desconto_editar.php — edita um desconto avulso (data, horas, motivo).
 * O valor em R$ é recalculado pelo valor/hora ATUAL do usuário.
 *
 * Auth: sessão do painel (admin).
 *
 * POST { id_desconto, data_desconto: 'YYYY-MM-DD', segundos_desconto: int, motivo: string }
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_descontos.php';
require_once __DIR__ . '/../_comum/log_atividades.php';

try {
    $in = ler_json_do_corpo();

    $id_desconto = (int)($in['id_desconto'] ?? 0);
    $data     = trim((string)($in['data_desconto'] ?? ''));
    $segundos = (int)($in['segundos_desconto'] ?? 0);
    $motivo   = trim((string)($in['motivo'] ?? ''));

    if ($id_desconto <= 0) {
        responder_json(false, 'id_desconto é obrigatório.', ['campo' => 'id_desconto'], 400);
    }
    if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $data)) {
        responder_json(false, 'data_desconto inválida (YYYY-MM-DD).', ['campo' => 'data_desconto'], 400);
    }
    if ($segundos <= 0) {
        responder_json(false, 'Informe as horas do desconto (maior que zero).', ['campo' => 'segundos_desconto'], 400);
    }
    if ($motivo === '') {
        responder_json(false, 'O motivo do desconto é obrigatório.', ['campo' => 'motivo'], 400);
    }
    if (mb_strlen($motivo) > 255) {
        $motivo = mb_substr($motivo, 0, 255);
    }

    $pdo = obter_conexao_pdo();
    pagamento_descontos_garantir_tabela($pdo);

    $st = $pdo->prepare("
        SELECT d.id_desconto, d.data_desconto, d.segundos_desconto, d.valor, d.motivo,
               u.user_id, u.valor_hora
        FROM pagamento_descontos d
        JOIN usuarios u ON u.id_usuario = d.id_usuario
        WHERE d.id_desconto = :id
        LIMIT 1
    ");
    $st->execute([':id' => $id_desconto]);
    $antes = $st->fetch(PDO::FETCH_ASSOC);

    if (!$antes) {
        responder_json(false, 'Desconto não encontrado.', ['id_desconto' => $id_desconto], 404);
    }

    $valor = round(($segundos / 3600) * (float)$antes['valor_hora'], 2);

    $stU = $pdo->prepare("
        UPDATE pagamento_descontos
        SET data_desconto = :data_desconto, segundos_desconto = :segundos, valor = :valor, motivo = :motivo
        WHERE id_desconto = :id
    ");
    $stU->execute([
        ':data_desconto' => $data,
        ':segundos'      => $segundos,
        ':valor'         => number_format($valor, 2, '.', ''),
        ':motivo'        => $motivo,
        ':id'            => $id_desconto,
    ]);

    log_registrar($pdo, 'desconto', 'editou',
        "Editou desconto #{$id_desconto} de {$antes['user_id']}: R\$ " . number_format($valor, 2, ',', '.') . " (" . gmdate('H:i', $segundos) . "h) em {$data}. Motivo: {$motivo}",
        ['data_desconto' => $data, 'segundos_desconto' => $segundos, 'valor' => $valor, 'motivo' => $motivo],
        ['data_desconto' => $antes['data_desconto'], 'segundos_desconto' => (int)$antes['segundos_desconto'], 'valor' => (float)$antes['valor'], 'motivo' => $antes['motivo']],
        (string)$id_desconto
    );

    responder_json(true, 'Desconto atualizado.', [
        'id_desconto'       => $id_desconto,
        'data_desconto'     => $data,
        'segundos_desconto' => $segundos,
        'valor'             => round($valor, 2),
        'motivo'            => $motivo,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'Falha ao editar desconto.', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
