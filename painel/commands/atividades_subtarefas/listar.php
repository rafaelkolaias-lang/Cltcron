<?php
// commands/atividades_subtarefas/listar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    $data_inicio = trim((string)($_GET['data_inicio'] ?? ''));
    $data_fim    = trim((string)($_GET['data_fim']    ?? ''));
    $user_id     = trim((string)($_GET['user_id']     ?? ''));
    $id_atividade = (int)($_GET['id_atividade'] ?? 0);
    $canal       = trim((string)($_GET['canal']       ?? ''));

    $condicoes = [];
    $params    = [];

    if ($data_inicio !== '') {
        $condicoes[] = 's.referencia_data >= :data_inicio';
        $params[':data_inicio'] = $data_inicio;
    }
    if ($data_fim !== '') {
        $condicoes[] = 's.referencia_data <= :data_fim';
        $params[':data_fim'] = $data_fim;
    }
    if ($user_id !== '') {
        $condicoes[] = 's.user_id = :user_id';
        $params[':user_id'] = $user_id;
    }
    if ($id_atividade > 0) {
        $condicoes[] = 's.id_atividade = :id_atividade';
        $params[':id_atividade'] = $id_atividade;
    }
    if ($canal !== '') {
        $condicoes[] = 's.canal_entrega LIKE :canal';
        $params[':canal'] = '%' . $canal . '%';
    }

    $where = $condicoes ? ('WHERE ' . implode(' AND ', $condicoes)) : '';

    $sql = "
        SELECT
            s.id_subtarefa,
            s.id_atividade,
            s.user_id,
            s.referencia_data,
            s.titulo,
            s.canal_entrega,
            s.concluida,
            s.segundos_gastos,
            s.observacao,
            s.bloqueada_pagamento,
            s.criada_em,
            s.atualizada_em,
            u.nome_exibicao,
            a.titulo AS atividade_titulo
        FROM atividades_subtarefas s
        LEFT JOIN usuarios u ON u.user_id = s.user_id
        LEFT JOIN atividades a ON a.id_atividade = s.id_atividade
        $where
        ORDER BY s.referencia_data DESC, s.criada_em DESC
        LIMIT 500
    ";

    $st = $pdo->prepare($sql);
    $st->execute($params);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    // cast tipos
    foreach ($linhas as &$l) {
        $l['id_subtarefa']       = (int)$l['id_subtarefa'];
        $l['id_atividade']       = (int)$l['id_atividade'];
        $l['concluida']          = (bool)$l['concluida'];
        $l['segundos_gastos']    = (int)$l['segundos_gastos'];
        $l['bloqueada_pagamento'] = (bool)$l['bloqueada_pagamento'];
    }

    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    responder_json(false, 'Falha ao listar tarefas declaradas', ['erro' => $e->getMessage()], 500);
}
