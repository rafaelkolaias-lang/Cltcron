<?php
declare(strict_types=1);

/**
 * desconto_criar.php — registra um desconto avulso de horas para um usuário.
 *
 * O valor em R$ é calculado no servidor: segundos_desconto × valor_hora atual
 * do usuário. O desconto entra no "A pagar" da Gestão, mas não trava tarefas
 * nem reseta ciclo (ver _descontos.php).
 *
 * Auth: sessão do painel (admin).
 *
 * POST { user_id, data_desconto: 'YYYY-MM-DD', segundos_desconto: int, motivo: string }
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_descontos.php';
require_once __DIR__ . '/../_comum/log_atividades.php';

try {
    $in = ler_json_do_corpo();

    $user_id  = trim((string)($in['user_id'] ?? ''));
    $data     = trim((string)($in['data_desconto'] ?? ''));
    $segundos = (int)($in['segundos_desconto'] ?? 0);
    $motivo   = trim((string)($in['motivo'] ?? ''));

    if ($user_id === '') {
        responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
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

    $usuario = pagamento_descontos_buscar_usuario($pdo, $user_id);
    if ($usuario === null) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }

    $valor = round(($segundos / 3600) * $usuario['valor_hora'], 2);

    $st = $pdo->prepare("
        INSERT INTO pagamento_descontos (id_usuario, data_desconto, segundos_desconto, valor, motivo)
        VALUES (:id_usuario, :data_desconto, :segundos, :valor, :motivo)
    ");
    $st->execute([
        ':id_usuario'    => $usuario['id_usuario'],
        ':data_desconto' => $data,
        ':segundos'      => $segundos,
        ':valor'         => number_format($valor, 2, '.', ''),
        ':motivo'        => $motivo,
    ]);
    $id_desconto = (int)$pdo->lastInsertId();

    log_registrar($pdo, 'desconto', 'criou',
        "Registrou desconto de R\$ " . number_format($valor, 2, ',', '.') . " (" . gmdate('H:i', $segundos) . "h) para {$user_id} em {$data}. Motivo: {$motivo}",
        ['id_desconto' => $id_desconto, 'user_id' => $user_id, 'data_desconto' => $data, 'segundos_desconto' => $segundos, 'valor' => $valor, 'motivo' => $motivo],
        null,
        (string)$id_desconto
    );

    responder_json(true, 'Desconto registrado.', [
        'id_desconto'       => $id_desconto,
        'user_id'           => $user_id,
        'data_desconto'     => $data,
        'segundos_desconto' => $segundos,
        'valor'             => round($valor, 2),
        'motivo'            => $motivo,
    ], 201);
} catch (Throwable $e) {
    responder_json(false, 'Falha ao registrar desconto.', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
