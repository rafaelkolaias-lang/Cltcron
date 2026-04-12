<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
date_default_timezone_set('America/Sao_Paulo');

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function relatorio_validar_data(?string $valor): ?string
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '') return null;
    $data = DateTime::createFromFormat('Y-m-d', $texto);
    return $data ? $data->format('Y-m-d') : null;
}

function relatorio_normalizar_lista(?array $valor, int $max = 100): array
{
    if (!is_array($valor)) return [];
    $resultado = [];
    foreach ($valor as $item) {
        $item = trim((string)($item ?? ''));
        if ($item !== '') $resultado[] = $item;
        if (count($resultado) >= $max) break;
    }
    return array_values(array_unique($resultado));
}

function relatorio_montar_in(string $prefixo, array $itens, array &$params): string
{
    $marcadores = [];
    foreach ($itens as $i => $valor) {
        $chave = ':' . $prefixo . '_' . $i;
        $marcadores[] = $chave;
        $params[$chave] = $valor;
    }
    return '(' . implode(',', $marcadores) . ')';
}

function relatorio_formatar_horas(int $segundos): string
{
    $h = intdiv($segundos, 3600);
    $m = intdiv($segundos % 3600, 60);
    $s = $segundos % 60;
    return sprintf('%02d:%02d:%02d', $h, $m, $s);
}

try {
    $corpo = (string)file_get_contents('php://input');
    $json  = $corpo !== '' ? (json_decode($corpo, true) ?: []) : [];
    $entrada = array_merge($_GET ?? [], $_POST ?? [], $json);

    // --- período ---
    $data_fim   = relatorio_validar_data($entrada['data_fim']   ?? null) ?? (new DateTime('today'))->format('Y-m-d');
    $data_inicio = relatorio_validar_data($entrada['data_inicio'] ?? null);
    if (!$data_inicio) {
        $dt = new DateTime($data_fim);
        $dt->modify('-29 days');
        $data_inicio = $dt->format('Y-m-d');
    }

    // garantir inicio <= fim
    if ($data_inicio > $data_fim) {
        [$data_inicio, $data_fim] = [$data_fim, $data_inicio];
    }

    $usuarios_filtro = relatorio_normalizar_lista($entrada['usuarios'] ?? null);
    // Filtro por membro único (vem do select do frontend)
    $membro_filtro = trim((string)($entrada['user_id'] ?? ''));

    $pdo = obter_conexao_pdo();

    // -------------------------------------------------------
    // 1. Horas DECLARADAS por usuário × dia
    //    Fonte: declaracoes_dia_itens
    // -------------------------------------------------------
    $params_dec = [
        ':data_inicio' => $data_inicio,
        ':data_fim'    => $data_fim,
    ];
    $where_dec = "d.referencia_data BETWEEN :data_inicio AND :data_fim";

    if ($membro_filtro !== '') {
        $where_dec .= " AND d.user_id = :membro";
        $params_dec[':membro'] = $membro_filtro;
    } elseif (!empty($usuarios_filtro)) {
        $in = relatorio_montar_in('ud', $usuarios_filtro, $params_dec);
        $where_dec .= " AND d.user_id IN {$in}";
    }

    $sql_declarados = "
        SELECT
            d.user_id,
            u.nome_exibicao,
            COALESCE(u.valor_hora, 0)      AS valor_hora,
            d.referencia_data,
            SUM(d.segundos_declarados)     AS segundos_declarados,
            COUNT(d.id_item)               AS total_declaracoes
        FROM declaracoes_dia_itens d
        INNER JOIN usuarios u ON u.user_id = d.user_id
        WHERE {$where_dec}
        GROUP BY d.user_id, u.nome_exibicao, u.valor_hora, d.referencia_data
        ORDER BY d.referencia_data DESC, u.nome_exibicao ASC
    ";

    $cmd = $pdo->prepare($sql_declarados);
    $cmd->execute($params_dec);
    $linhas_raw = $cmd->fetchAll(PDO::FETCH_ASSOC) ?: [];

    // -------------------------------------------------------
    // 2. Horas TRABALHADAS por usuário × dia (registros_tempo)
    // -------------------------------------------------------
    $params_trab = [':data_inicio' => $data_inicio, ':data_fim' => $data_fim];
    // Tenta filtrar horas já pagas; fallback se coluna id_pagamento não existe
    $tem_col_pagamento = true;
    try {
        $pdo->query("SELECT id_pagamento FROM registros_tempo LIMIT 0");
    } catch (Throwable $_) {
        $tem_col_pagamento = false;
    }
    $filtro_pago = $tem_col_pagamento ? " AND rt.id_pagamento IS NULL" : "";
    $where_trab = "rt.referencia_data BETWEEN :data_inicio AND :data_fim AND rt.situacao = 'trabalhando'" . $filtro_pago;

    if ($membro_filtro !== '') {
        $where_trab .= " AND rt.user_id = :membro";
        $params_trab[':membro'] = $membro_filtro;
    } elseif (!empty($usuarios_filtro)) {
        $in = relatorio_montar_in('ut', $usuarios_filtro, $params_trab);
        $where_trab .= " AND rt.user_id IN {$in}";
    }

    $sql_trab = "
        SELECT rt.user_id, rt.referencia_data, SUM(rt.segundos) AS segundos_trabalhados
        FROM registros_tempo rt
        WHERE {$where_trab}
        GROUP BY rt.user_id, rt.referencia_data
    ";
    $cmd2 = $pdo->prepare($sql_trab);
    $cmd2->execute($params_trab);
    $trab_raw = $cmd2->fetchAll(PDO::FETCH_ASSOC) ?: [];

    // Mapa user_id|data => segundos_trabalhados
    $mapa_trab = [];
    $trab_por_usuario = [];
    foreach ($trab_raw as $t) {
        $chave = $t['user_id'] . '|' . $t['referencia_data'];
        $mapa_trab[$chave] = (int)$t['segundos_trabalhados'];
        $trab_por_usuario[$t['user_id']] = ($trab_por_usuario[$t['user_id']] ?? 0) + (int)$t['segundos_trabalhados'];
    }

    // -------------------------------------------------------
    // 3. Status de pagamento por usuário × dia
    // -------------------------------------------------------
    $params_pag = [':data_inicio' => $data_inicio, ':data_fim' => $data_fim];
    $where_pag = "s.referencia_data BETWEEN :data_inicio AND :data_fim";

    if ($membro_filtro !== '') {
        $where_pag .= " AND s.user_id = :membro";
        $params_pag[':membro'] = $membro_filtro;
    }

    $sql_pag = "
        SELECT s.user_id, s.referencia_data, MAX(s.bloqueada_pagamento) AS pago
        FROM atividades_subtarefas s
        WHERE {$where_pag} AND s.referencia_data IS NOT NULL
        GROUP BY s.user_id, s.referencia_data
    ";
    $cmd3 = $pdo->prepare($sql_pag);
    $cmd3->execute($params_pag);
    $pag_raw = $cmd3->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $mapa_pago = [];
    foreach ($pag_raw as $p) {
        $mapa_pago[$p['user_id'] . '|' . $p['referencia_data']] = (int)$p['pago'];
    }

    // -------------------------------------------------------
    // 3b. Total pago por usuário (soma de Pagamentos)
    // -------------------------------------------------------
    $mapa_total_pago = [];
    $sql_total_pago = "
        SELECT u.user_id, COALESCE(SUM(p.valor), 0) AS total_pago
        FROM Pagamentos p
        JOIN usuarios u ON u.id_usuario = p.id_usuario
        GROUP BY u.user_id
    ";
    $cmd_tp = $pdo->query($sql_total_pago);
    foreach ($cmd_tp->fetchAll(PDO::FETCH_ASSOC) ?: [] as $tp) {
        $mapa_total_pago[$tp['user_id']] = (float)$tp['total_pago'];
    }

    // -------------------------------------------------------
    // 4. Montar linhas e totais por usuário
    // -------------------------------------------------------
    $linhas        = [];
    $por_usuario   = [];

    foreach ($linhas_raw as $linha) {
        $uid   = (string)($linha['user_id']       ?? '');
        $nome  = (string)($linha['nome_exibicao'] ?? $uid);
        $vh    = (float)($linha['valor_hora']      ?? 0);
        $segs  = (int)($linha['segundos_declarados'] ?? 0);
        $qtd   = (int)($linha['total_declaracoes']   ?? 0);
        $data  = (string)($linha['referencia_data']  ?? '');

        $chave = $uid . '|' . $data;
        $segs_trab = $mapa_trab[$chave] ?? 0;
        $pago = ($mapa_pago[$chave] ?? 0) === 1;

        $horas_float = $segs / 3600.0;
        $valor_est   = round($horas_float * $vh, 2);

        // Divergência: declarado > trabalhado+10% (margem de 10%)
        $divergente = $segs_trab > 0 && $segs > ($segs_trab * 1.1);

        $linhas[] = [
            'user_id'               => $uid,
            'nome_exibicao'         => $nome,
            'valor_hora'            => $vh,
            'referencia_data'       => $data,
            'segundos_declarados'   => $segs,
            'segundos_trabalhados'  => $segs_trab,
            'horas_formatado'       => relatorio_formatar_horas($segs),
            'trabalhado_formatado'  => relatorio_formatar_horas($segs_trab),
            'total_declaracoes'     => $qtd,
            'valor_estimado'        => $valor_est,
            'pago'                  => $pago,
            'divergente'            => $divergente,
        ];

        if (!isset($por_usuario[$uid])) {
            $por_usuario[$uid] = [
                'user_id'              => $uid,
                'nome_exibicao'        => $nome,
                'valor_hora'           => $vh,
                'segundos_total'       => 0,
                'segundos_trab_total'  => 0,
                'valor_estimado'       => 0.0,
                'total_pago'           => $mapa_total_pago[$uid] ?? 0.0,
                'dias_trabalhados'     => 0,
            ];
        }
        $por_usuario[$uid]['segundos_total']      += $segs;
        $por_usuario[$uid]['segundos_trab_total']  += $segs_trab;
        $por_usuario[$uid]['valor_estimado']       += $valor_est;
        $por_usuario[$uid]['dias_trabalhados']     += 1;
    }

    // formatar totais por usuário
    $totais_por_usuario = [];
    foreach ($por_usuario as $u) {
        $u['horas_formatado']      = relatorio_formatar_horas($u['segundos_total']);
        $u['trabalhado_formatado'] = relatorio_formatar_horas($u['segundos_trab_total']);
        $u['valor_estimado']       = round($u['valor_estimado'], 2);
        $u['total_pago']           = round($u['total_pago'], 2);
        $u['valor_pendente']       = round(max(0, $u['valor_estimado'] - $u['total_pago']), 2);
        $totais_por_usuario[]      = $u;
    }

    usort($totais_por_usuario, static fn(array $a, array $b): int => $b['segundos_total'] <=> $a['segundos_total']);

    $total_geral_segundos = array_sum(array_column($totais_por_usuario, 'segundos_total'));
    $total_geral_valor    = round(array_sum(array_column($totais_por_usuario, 'valor_estimado')), 2);

    responder_json(true, 'OK', [
        'periodo' => [
            'data_inicio'    => $data_inicio,
            'data_fim'       => $data_fim,
            'atualizado_em'  => (new DateTime())->format('Y-m-d H:i:s'),
        ],
        'linhas'             => $linhas,
        'totais_por_usuario' => $totais_por_usuario,
        'total_geral_segundos' => $total_geral_segundos,
        'total_geral_horas'    => relatorio_formatar_horas($total_geral_segundos),
        'total_geral_valor'    => $total_geral_valor,
    ], 200);

} catch (Throwable $e) {
    responder_json(false, 'Erro ao gerar relatório.', ['erro' => $e->getMessage()], 500);
}
