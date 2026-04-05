<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
date_default_timezone_set('America/Sao_Paulo');

require_once __DIR__ . '/../_comum/resposta.php';
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

    if (!empty($usuarios_filtro)) {
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
    // 2. Montar linhas e totais por usuário
    // -------------------------------------------------------
    $linhas        = [];
    $por_usuario   = [];   // user_id => [nome, valor_hora, segundos_total, valor_estimado]

    foreach ($linhas_raw as $linha) {
        $uid   = (string)($linha['user_id']       ?? '');
        $nome  = (string)($linha['nome_exibicao'] ?? $uid);
        $vh    = (float)($linha['valor_hora']      ?? 0);
        $segs  = (int)($linha['segundos_declarados'] ?? 0);
        $qtd   = (int)($linha['total_declaracoes']   ?? 0);
        $data  = (string)($linha['referencia_data']  ?? '');

        $horas_float = $segs / 3600.0;
        $valor_est   = round($horas_float * $vh, 2);

        $linhas[] = [
            'user_id'             => $uid,
            'nome_exibicao'       => $nome,
            'valor_hora'          => $vh,
            'referencia_data'     => $data,
            'segundos_declarados' => $segs,
            'horas_formatado'     => relatorio_formatar_horas($segs),
            'total_declaracoes'   => $qtd,
            'valor_estimado'      => $valor_est,
        ];

        if (!isset($por_usuario[$uid])) {
            $por_usuario[$uid] = [
                'user_id'        => $uid,
                'nome_exibicao'  => $nome,
                'valor_hora'     => $vh,
                'segundos_total' => 0,
                'valor_estimado' => 0.0,
                'dias_trabalhados' => 0,
            ];
        }
        $por_usuario[$uid]['segundos_total']   += $segs;
        $por_usuario[$uid]['valor_estimado']   += $valor_est;
        $por_usuario[$uid]['dias_trabalhados'] += 1;
    }

    // formatar totais por usuário
    $totais_por_usuario = [];
    foreach ($por_usuario as $u) {
        $u['horas_formatado']  = relatorio_formatar_horas($u['segundos_total']);
        $u['valor_estimado']   = round($u['valor_estimado'], 2);
        $totais_por_usuario[]  = $u;
    }

    // ordenar totais: mais horas primeiro
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
