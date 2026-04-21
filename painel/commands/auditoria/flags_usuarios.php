<?php
// painel/commands/auditoria/flags_usuarios.php
//
// Retorna flags de auditoria por usuário, cruzando os apps configurados em
// auditoria_apps_suspeitos (ativos) com cronometro_apps_intervalos.
//
// Query params opcionais:
//   ?user_id=richard   — restringe a um único usuário
//
// Resposta:
// {
//   ok: true,
//   dados: {
//     usuarios: [
//       {
//         user_id: "richard",
//         nome_exibicao: "Richard",
//         tem_flag_7dias: true,
//         apps_detectados: [
//           {
//             id_app_suspeito: 1,
//             nome_app_config: "gs-auto-clicker",
//             nome_app_real:   "gs-auto-clicker-3.1.4-installer.exe",
//             motivo:          "Auto-clicker (GS Auto Clicker)",
//             sessoes:         14,
//             horas_abertas:   "184h44m",
//             segundos_totais: 665040,
//             primeiro_uso:    "2026-04-06 18:15:40",
//             ultimo_uso:      "2026-04-20 14:16:50",
//             usado_ultimos_7d: true
//           },
//           ...
//         ]
//       },
//       ...
//     ],
//     apps_suspeitos_ativos: 10,
//     gerado_em: "2026-04-21 15:30:00"
//   }
// }
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function formatar_hhmm(int $segundos): string
{
    $segundos = max(0, $segundos);
    $h = intdiv($segundos, 3600);
    $m = intdiv($segundos % 3600, 60);
    return sprintf('%dh%02dm', $h, $m);
}

try {
    $pdo = obter_conexao_pdo();

    $user_filtro = isset($_GET['user_id']) ? normalizar_user_id((string)$_GET['user_id']) : '';

    // ── Carrega lista de apps suspeitos ativos
    $st = $pdo->prepare("SELECT id, nome_app, motivo FROM auditoria_apps_suspeitos WHERE ativo = 1");
    $st->execute();
    $apps_config = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    if (empty($apps_config)) {
        responder_json(true, 'OK', [
            'usuarios'               => [],
            'apps_suspeitos_ativos'  => 0,
            'gerado_em'              => date('Y-m-d H:i:s'),
        ], 200);
    }

    // ── Monta WHERE dinâmico com LIKE por cada substring
    // O match é case-insensitive (utf8mb4_unicode_ci já cobre)
    $conds = [];
    $parametros = [];
    foreach ($apps_config as $i => $a) {
        $ph = ":app_{$i}";
        $conds[] = "ai.nome_app LIKE {$ph}";
        $parametros[$ph] = '%' . $a['nome_app'] . '%';
    }
    $where_app = '(' . implode(' OR ', $conds) . ')';

    $where_user_sql = '';
    if ($user_filtro !== '') {
        $where_user_sql = ' AND ai.user_id = :user_id ';
        $parametros[':user_id'] = $user_filtro;
    }

    // ── Agregados por (user_id, nome_app real detectado)
    $sql = "
        SELECT
            ai.user_id,
            ai.nome_app AS nome_app_real,
            COUNT(DISTINCT ai.id_sessao) AS sessoes,
            SUM(
                GREATEST(0,
                    TIMESTAMPDIFF(
                        SECOND,
                        ai.inicio_em,
                        COALESCE(ai.fim_em, ai.ultima_atualizacao_em, NOW())
                    )
                )
            ) AS segundos_totais,
            MIN(ai.inicio_em) AS primeiro_uso,
            MAX(COALESCE(ai.fim_em, ai.ultima_atualizacao_em, ai.inicio_em)) AS ultimo_uso,
            MAX(
                CASE
                    WHEN COALESCE(ai.fim_em, ai.ultima_atualizacao_em, ai.inicio_em) >= (NOW() - INTERVAL 7 DAY)
                    THEN 1 ELSE 0
                END
            ) AS usado_ultimos_7d
        FROM cronometro_apps_intervalos ai
        WHERE {$where_app}
        {$where_user_sql}
        GROUP BY ai.user_id, ai.nome_app
        ORDER BY ai.user_id ASC, segundos_totais DESC
    ";

    $cmd = $pdo->prepare($sql);
    $cmd->execute($parametros);
    $linhas = $cmd->fetchAll(PDO::FETCH_ASSOC) ?: [];

    // ── Agrupa por usuário + casa cada nome_app real com o registro de config
    // (o primeiro config que der match por LIKE vence)
    $por_user = [];
    foreach ($linhas as $l) {
        $uid = (string)$l['user_id'];
        if ($uid === '') continue;

        $nome_real = (string)$l['nome_app_real'];
        $nome_real_lc = mb_strtolower($nome_real);

        $id_app_suspeito = null;
        $nome_app_config = null;
        $motivo_config   = null;
        foreach ($apps_config as $a) {
            if ($a['nome_app'] !== '' && mb_strpos($nome_real_lc, (string)$a['nome_app']) !== false) {
                $id_app_suspeito = (int)$a['id'];
                $nome_app_config = (string)$a['nome_app'];
                $motivo_config   = $a['motivo'] !== null ? (string)$a['motivo'] : null;
                break;
            }
        }

        if (!isset($por_user[$uid])) {
            $por_user[$uid] = [
                'user_id'         => $uid,
                'nome_exibicao'   => null,
                'tem_flag_7dias'  => false,
                'apps_detectados' => [],
            ];
        }

        $segs = (int)($l['segundos_totais'] ?? 0);
        $usado_7d = ((int)($l['usado_ultimos_7d'] ?? 0)) === 1;
        if ($usado_7d) {
            $por_user[$uid]['tem_flag_7dias'] = true;
        }

        $por_user[$uid]['apps_detectados'][] = [
            'id_app_suspeito'  => $id_app_suspeito,
            'nome_app_config'  => $nome_app_config,
            'nome_app_real'    => $nome_real,
            'motivo'           => $motivo_config,
            'sessoes'          => (int)$l['sessoes'],
            'segundos_totais'  => $segs,
            'horas_abertas'    => formatar_hhmm($segs),
            'primeiro_uso'     => (string)($l['primeiro_uso'] ?? ''),
            'ultimo_uso'       => (string)($l['ultimo_uso'] ?? ''),
            'usado_ultimos_7d' => $usado_7d,
        ];
    }

    // ── Enriquece com nome_exibicao (JOIN separado é mais simples)
    if (!empty($por_user)) {
        $uids = array_keys($por_user);
        $ph   = implode(',', array_fill(0, count($uids), '?'));
        $stN = $pdo->prepare("SELECT user_id, nome_exibicao FROM usuarios WHERE user_id IN ({$ph})");
        $stN->execute($uids);
        foreach ($stN->fetchAll(PDO::FETCH_ASSOC) ?: [] as $r) {
            if (isset($por_user[$r['user_id']])) {
                $por_user[$r['user_id']]['nome_exibicao'] = (string)$r['nome_exibicao'];
            }
        }
    }

    // Remove user_ids que não existem em usuarios (dados órfãos) — opcional,
    // mas evita mostrar flag de user deletado. Comentar se preferir mostrar:
    $usuarios = array_values(array_filter(
        $por_user,
        static fn($u) => $u['nome_exibicao'] !== null
    ));

    responder_json(true, 'OK', [
        'usuarios'              => $usuarios,
        'apps_suspeitos_ativos' => count($apps_config),
        'gerado_em'             => date('Y-m-d H:i:s'),
    ], 200);

} catch (Throwable $e) {
    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = ['erro' => $e->getMessage(), 'arquivo' => $e->getFile(), 'linha' => $e->getLine()];
    }
    responder_json(false, 'falha ao consultar flags de auditoria', $dados, 500);
}
