<?php
declare(strict_types=1);

/**
 * desktop_marcar_pastas_logicas_inativas_lote.php — soft-delete em lote.
 *
 * Versão batch de desktop_marcar_pasta_logica_inativa.php pra performance
 * na sincronização periódica do desktop (até centenas de pastas por
 * execução). Mesma defesa contra IDOR: filtra IDs que pertencem a canais
 * do user antes de atualizar.
 *
 * Auth: user_id + chave.
 *
 * POST { ids_pasta_logica: [1,2,3,...] }
 *
 * Resposta: 200 com {
 *   solicitados:int,
 *   inativadas:int,        // efetivamente atualizadas (já podia estar 0 — UPDATE é idempotente)
 *   ids_ignorados:int[]    // IDs que não pertencem a canais do user (silenciosos pra não vazar info)
 * }
 *
 * Limite de 1000 IDs por chamada pra não estourar placeholders do PDO.
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

const LIMITE_IDS_POR_LOTE = 1000;

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $in = ler_json_do_corpo();
    $ids_in = $in['ids_pasta_logica'] ?? [];
    if (!is_array($ids_in)) {
        responder_json(false, 'ids_pasta_logica deve ser um array', null, 400);
    }

    // Sanitize: int positivos + dedup.
    $ids = [];
    foreach ($ids_in as $v) {
        $i = (int)$v;
        if ($i > 0) $ids[$i] = true;
    }
    $ids = array_keys($ids);

    if (count($ids) > LIMITE_IDS_POR_LOTE) {
        responder_json(false, 'lote acima do limite (' . LIMITE_IDS_POR_LOTE . ')', null, 400);
    }
    if (!$ids) {
        responder_json(true, 'OK', ['solicitados' => 0, 'inativadas' => 0, 'ids_ignorados' => []]);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Filtra só IDs que pertencem a canais do user (defesa IDOR).
    $place = implode(',', array_fill(0, count($ids), '?'));
    $st = $pdo->prepare("
        SELECT pl.id_pasta_logica
          FROM mega_pasta_logica pl
          JOIN atividades_usuarios au ON au.id_atividade = pl.id_atividade
          JOIN usuarios u ON u.id_usuario = au.id_usuario
         WHERE u.user_id = ?
           AND pl.id_pasta_logica IN ($place)
    ");
    $st->execute(array_merge([$user_id], $ids));
    $autorizados = array_map(static fn($v) => (int)$v, $st->fetchAll(PDO::FETCH_COLUMN) ?: []);

    $ids_ignorados = array_values(array_diff($ids, $autorizados));

    $inativadas = 0;
    if ($autorizados) {
        $place2 = implode(',', array_fill(0, count($autorizados), '?'));
        $st = $pdo->prepare("UPDATE mega_pasta_logica SET ativo=0
                              WHERE ativo=1 AND id_pasta_logica IN ($place2)");
        $st->execute($autorizados);
        $inativadas = $st->rowCount();
    }

    responder_json(true, 'OK', [
        'solicitados'   => count($ids),
        'inativadas'    => $inativadas,
        'ids_ignorados' => $ids_ignorados,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao marcar pastas lógicas inativas em lote', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
