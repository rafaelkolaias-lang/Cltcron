<?php
declare(strict_types=1);

/**
 * listar.php — o que a janela "Opções > Gastos" do editor mostra quando o
 * adm escolhe um usuário (ou todos) no seletor. SOMENTE a conta adm.
 *
 * Entrada (GET; auth por query string user_id+chave ou header):
 *   usuario = user_id de UM usuário, ou vazio = todos
 *   dias    = 7 | 30 | 90 | 0 (0 = tudo)
 *
 * Resposta `dados`:
 *   {
 *     "usuarios":  [ { user_id, nome_exibicao, status_conta, total_usd, ultimo_dia } ],
 *                  -- TODOS os usuários que já mandaram algum gasto ou produção (sem filtro
 *                     de período), para preencher o seletor do app
 *     "por_dia":   [ { user_id, origem, dia, usd } ],      -- agregado COMPLETO do período
 *     "itens":     [ { user_id, origem, quando, operacao, detalhe, usd, maquina } ],
 *                  -- os últimos EDITOR_MAX_ITENS_LISTA lançamentos do período
 *     "producoes": [ { user_id, maquina, ficha } ],         -- fichas do período (ficha = JSON do app)
 *     "periodo":   { dias, inicio }
 *   }
 */

require_once __DIR__ . '/_comum_editor.php';

try {
    $u = autenticar_cliente_ou_morrer();
    editor_exigir_adm($u);

    $usuario = normalizar_user_id((string)($_GET['usuario'] ?? ''));
    $dias    = (int)($_GET['dias'] ?? 30);
    if ($dias < 0) $dias = 0;
    if ($dias > 3660) $dias = 3660;
    $inicio  = editor_data_inicio_do_periodo($dias);

    $pdo = obter_conexao_pdo();

    // Filtro comum (usuário + período), montado uma vez.
    $where = [];
    $args  = [];
    if ($usuario !== '') { $where[] = 'user_id = ?'; $args[] = $usuario; }
    if ($inicio !== null) { $where[] = 'dia >= ?';   $args[] = $inicio; }
    $sql_where = $where ? (' WHERE ' . implode(' AND ', $where)) : '';

    // 1. Usuários conhecidos (sem filtro de período — o seletor precisa de todos).
    $stm = $pdo->query(
        "SELECT x.user_id,
                COALESCE(us.nome_exibicao, x.user_id) AS nome_exibicao,
                COALESCE(us.status_conta, '')          AS status_conta,
                ROUND(SUM(x.usd), 6)                   AS total_usd,
                MAX(x.dia)                             AS ultimo_dia
           FROM (
                SELECT user_id, usd, dia FROM editor_gastos
                UNION ALL
                SELECT user_id, 0 AS usd, dia FROM editor_producoes
           ) x
      LEFT JOIN usuarios us ON us.user_id = x.user_id
       GROUP BY x.user_id, us.nome_exibicao, us.status_conta
       ORDER BY nome_exibicao ASC"
    );
    $usuarios = [];
    foreach ($stm->fetchAll() as $r) {
        $usuarios[] = [
            'user_id'       => (string)$r['user_id'],
            'nome_exibicao' => (string)$r['nome_exibicao'],
            'status_conta'  => (string)$r['status_conta'],
            'total_usd'     => (float)$r['total_usd'],
            'ultimo_dia'    => (string)($r['ultimo_dia'] ?? ''),
        ];
    }

    // 2. Agregado por usuário x origem x dia (completo no período).
    $stm = $pdo->prepare(
        "SELECT user_id, origem, dia, ROUND(SUM(usd), 6) AS usd
           FROM editor_gastos" . $sql_where . "
       GROUP BY user_id, origem, dia
       ORDER BY dia ASC"
    );
    $stm->execute($args);
    $por_dia = [];
    foreach ($stm->fetchAll() as $r) {
        $por_dia[] = [
            'user_id' => (string)$r['user_id'],
            'origem'  => (string)$r['origem'],
            'dia'     => (string)$r['dia'],
            'usd'     => (float)$r['usd'],
        ];
    }

    // 3. Lançamentos (os mais recentes primeiro, com teto).
    $stm = $pdo->prepare(
        "SELECT user_id, origem, quando, operacao, detalhe, usd, maquina
           FROM editor_gastos" . $sql_where . "
       ORDER BY quando DESC, id DESC
          LIMIT " . EDITOR_MAX_ITENS_LISTA
    );
    $stm->execute($args);
    $itens = [];
    foreach ($stm->fetchAll() as $r) {
        $itens[] = [
            'user_id'  => (string)$r['user_id'],
            'origem'   => (string)$r['origem'],
            'quando'   => substr((string)$r['quando'], 0, 16),   // "AAAA-MM-DD HH:MM", como o app
            'operacao' => (string)$r['operacao'],
            'detalhe'  => (string)$r['detalhe'],
            'usd'      => (float)$r['usd'],
            'maquina'  => (string)($r['maquina'] ?? ''),
        ];
    }

    // 4. Fichas de produção do período.
    $stm = $pdo->prepare(
        "SELECT user_id, maquina, ficha_json
           FROM editor_producoes" . $sql_where . "
       ORDER BY quando ASC, id ASC
          LIMIT " . EDITOR_MAX_PRODUCOES_LISTA
    );
    $stm->execute($args);
    $producoes = [];
    foreach ($stm->fetchAll() as $r) {
        $ficha = json_decode((string)($r['ficha_json'] ?? ''), true);
        if (!is_array($ficha)) continue;
        $producoes[] = [
            'user_id' => (string)$r['user_id'],
            'maquina' => (string)($r['maquina'] ?? ''),
            'ficha'   => $ficha,
        ];
    }

    responder_json(true, 'OK', [
        'usuarios'  => $usuarios,
        'por_dia'   => $por_dia,
        'itens'     => $itens,
        'producoes' => $producoes,
        'periodo'   => ['dias' => $dias, 'inicio' => $inicio],
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
