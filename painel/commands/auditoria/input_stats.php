<?php
// painel/commands/auditoria/input_stats.php
//
// Retorna agregados de input humano vs sintético por dia para um usuário.
//
// Query params:
//   user_id (obrigatório)
//   dias    (opcional, default 15) — quantidade de dias mais recentes
//
// Resposta:
// {
//   ok: true,
//   dados: {
//     user_id: "richard",
//     dias: [
//       { referencia_data: "2026-04-20", humano: 18000, sintetico: 7200 },
//       ...
//     ],
//     totais: {
//       humano: 123456,
//       sintetico: 78900,
//       percentual_sintetico: 39.0  // sobre (humano + sintetico)
//     }
//   }
// }
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $user_id = isset($_GET['user_id']) ? normalizar_user_id((string)$_GET['user_id']) : '';
    if ($user_id === '') {
        responder_json(false, 'user_id obrigatório', null, 400);
    }

    $dias = isset($_GET['dias']) ? max(1, min(365, (int)$_GET['dias'])) : 15;

    $pdo = obter_conexao_pdo();

    $sql = "
        SELECT
            DATE_FORMAT(referencia_data, '%Y-%m-%d') AS referencia_data,
            COALESCE(SUM(segundos_input_humano), 0)    AS humano,
            COALESCE(SUM(segundos_input_sintetico), 0) AS sintetico
        FROM cronometro_input_stats
        WHERE user_id = :uid
          AND referencia_data >= (CURDATE() - INTERVAL :dias DAY)
        GROUP BY referencia_data
        ORDER BY referencia_data ASC
    ";
    $st = $pdo->prepare($sql);
    $st->bindValue(':uid', $user_id, PDO::PARAM_STR);
    $st->bindValue(':dias', $dias, PDO::PARAM_INT);
    $st->execute();
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $total_h = 0;
    $total_s = 0;
    foreach ($linhas as &$l) {
        $l['humano']    = (int)$l['humano'];
        $l['sintetico'] = (int)$l['sintetico'];
        $total_h += $l['humano'];
        $total_s += $l['sintetico'];
    }

    $soma = $total_h + $total_s;
    $perc = $soma > 0 ? round(($total_s / $soma) * 100, 1) : 0.0;

    responder_json(true, 'OK', [
        'user_id' => $user_id,
        'dias'    => $linhas,
        'totais'  => [
            'humano'               => $total_h,
            'sintetico'            => $total_s,
            'percentual_sintetico' => $perc,
        ],
    ], 200);

} catch (Throwable $e) {
    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = ['erro' => $e->getMessage(), 'arquivo' => $e->getFile(), 'linha' => $e->getLine()];
    }
    responder_json(false, 'falha ao consultar input_stats', $dados, 500);
}
