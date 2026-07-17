<?php
declare(strict_types=1);

/**
 * desconto_excluir.php — exclui um desconto avulso (as horas voltam pro "A pagar").
 *
 * Auth: sessão do painel (admin).
 *
 * POST { id_desconto }
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

    if ($id_desconto <= 0) {
        responder_json(false, 'id_desconto é obrigatório.', ['campo' => 'id_desconto'], 400);
    }

    $pdo = obter_conexao_pdo();
    pagamento_descontos_garantir_tabela($pdo);

    $st = $pdo->prepare("
        SELECT d.id_desconto, d.data_desconto, d.segundos_desconto, d.valor, d.motivo, u.user_id
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

    $stD = $pdo->prepare("DELETE FROM pagamento_descontos WHERE id_desconto = :id");
    $stD->execute([':id' => $id_desconto]);

    log_registrar($pdo, 'desconto', 'excluiu',
        "Excluiu desconto #{$id_desconto} de {$antes['user_id']}: R\$ " . number_format((float)$antes['valor'], 2, ',', '.') . " ({$antes['data_desconto']}). Motivo era: {$antes['motivo']}",
        null,
        ['data_desconto' => $antes['data_desconto'], 'segundos_desconto' => (int)$antes['segundos_desconto'], 'valor' => (float)$antes['valor'], 'motivo' => $antes['motivo']],
        (string)$id_desconto
    );

    responder_json(true, 'Desconto excluído.', ['id_desconto' => $id_desconto]);
} catch (Throwable $e) {
    responder_json(false, 'Falha ao excluir desconto.', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
