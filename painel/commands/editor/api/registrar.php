<?php
declare(strict_types=1);

/**
 * registrar.php — o Editor Premiere Premium manda os lançamentos de gasto
 * e as fichas de produção do usuário logado (fila local do app, em lotes).
 *
 * Entrada (POST, corpo JSON; auth por query string user_id+chave ou header):
 *   {
 *     "versao_app": "3.9",
 *     "maquina": "PC-DO-JOAO",
 *     "gastos": [
 *       { "uid": "<32 hex>", "origem": "manual"|"motor", "quando": "2026-09-06 13:40",
 *         "operacao": "...", "detalhe": "...", "usd": 0.1234 }
 *     ],
 *     "producoes": [
 *       { "uid": "<32 hex>", "ficha": { ...FichaProducao.dados... } }
 *     ]
 *   }
 *
 * Resposta: { ok, dados: { gastos: { recebidos, novos, rejeitados: [uid...] },
 *                          producoes: { recebidos, novos, rejeitados: [uid...] } } }
 *
 * Idempotente: `uid` é UNIQUE — reenvio do mesmo item (app caiu antes de
 * apagar da fila) conta como aceito e não duplica. Item inválido volta em
 * `rejeitados` para o app tirar da fila e não tentar para sempre.
 * O user_id NUNCA vem do corpo: é o da autenticação.
 */

require_once __DIR__ . '/_comum_editor.php';

try {
    if (strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET')) !== 'POST') {
        responder_json(false, 'use POST', null, 405);
    }

    $u = autenticar_cliente_ou_morrer();
    $corpo = ler_json_do_corpo();

    $gastos    = isset($corpo['gastos'])    && is_array($corpo['gastos'])    ? $corpo['gastos']    : [];
    $producoes = isset($corpo['producoes']) && is_array($corpo['producoes']) ? $corpo['producoes'] : [];
    if (count($gastos) > EDITOR_MAX_LOTE || count($producoes) > EDITOR_MAX_LOTE) {
        responder_json(false, 'lote grande demais (máx. ' . EDITOR_MAX_LOTE . ' por tipo)', null, 413);
    }

    $versao_app = editor_texto($corpo['versao_app'] ?? '', 20);
    $maquina    = editor_texto($corpo['maquina'] ?? '', 80);
    $user_id    = (string)$u['user_id'];

    $pdo = obter_conexao_pdo();

    // ---------------- gastos ----------------
    $ins_g = $pdo->prepare(
        "INSERT IGNORE INTO editor_gastos
            (uid, user_id, origem, quando, dia, operacao, detalhe, usd, versao_app, maquina)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    );
    $res_g = ['recebidos' => count($gastos), 'novos' => 0, 'rejeitados' => []];
    foreach ($gastos as $g) {
        $uid = is_array($g) ? strtolower(trim((string)($g['uid'] ?? ''))) : '';
        if (!is_array($g) || !editor_uid_valido($uid)) {
            if ($uid !== '') $res_g['rejeitados'][] = $uid;
            continue;
        }
        $quando = editor_normalizar_quando((string)($g['quando'] ?? ''));
        $origem = strtolower(trim((string)($g['origem'] ?? 'manual')));
        if ($quando === null || !in_array($origem, ['manual', 'motor'], true)) {
            $res_g['rejeitados'][] = $uid;
            continue;
        }
        $ins_g->execute([
            $uid, $user_id, $origem, $quando[0], $quando[1],
            editor_texto($g['operacao'] ?? '', 255),
            editor_texto($g['detalhe'] ?? '', 500),
            round(editor_numero($g['usd'] ?? 0), 6),
            $versao_app !== '' ? $versao_app : null,
            $maquina !== '' ? $maquina : null,
        ]);
        $res_g['novos'] += $ins_g->rowCount() > 0 ? 1 : 0;
    }

    // ---------------- produções ----------------
    $ins_p = $pdo->prepare(
        "INSERT IGNORE INTO editor_producoes
            (uid, user_id, quando, dia, projeto, origem, modo, canal, tema, status,
             tempo_parede_s, tempo_espera_s, tempo_liquido_s, custo_usd, ficha_json,
             versao_app, maquina)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    );
    $res_p = ['recebidos' => count($producoes), 'novos' => 0, 'rejeitados' => []];
    foreach ($producoes as $p) {
        $uid = is_array($p) ? strtolower(trim((string)($p['uid'] ?? ''))) : '';
        $ficha = (is_array($p) && isset($p['ficha']) && is_array($p['ficha'])) ? $p['ficha'] : null;
        if (!is_array($p) || !editor_uid_valido($uid) || $ficha === null) {
            if ($uid !== '') $res_p['rejeitados'][] = $uid;
            continue;
        }
        $quando = editor_normalizar_quando((string)($ficha['quando'] ?? ''));
        if ($quando === null) {
            $res_p['rejeitados'][] = $uid;
            continue;
        }
        $json = json_encode($ficha, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        if ($json === false || strlen($json) > 200000) {
            $res_p['rejeitados'][] = $uid;
            continue;
        }
        $ins_p->execute([
            $uid, $user_id, $quando[0], $quando[1],
            editor_texto($ficha['projeto'] ?? '', 200),
            editor_texto($ficha['origem'] ?? 'Manual', 20),
            editor_texto($ficha['modo'] ?? '', 40),
            editor_texto($ficha['canal'] ?? '', 120),
            editor_texto($ficha['tema'] ?? '', 255),
            editor_texto($ficha['status'] ?? '', 20),
            round(editor_numero($ficha['tempo_parede_s'] ?? 0), 1),
            round(editor_numero($ficha['tempo_espera_s'] ?? 0), 1),
            round(editor_numero($ficha['tempo_liquido_s'] ?? 0), 1),
            round(editor_numero($ficha['custo_usd'] ?? 0), 6),
            $json,
            $versao_app !== '' ? $versao_app : null,
            $maquina !== '' ? $maquina : null,
        ]);
        $res_p['novos'] += $ins_p->rowCount() > 0 ? 1 : 0;
    }

    responder_json(true, 'OK', ['gastos' => $res_g, 'producoes' => $res_p]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao registrar', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
