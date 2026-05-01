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
    $resumo_periodo = trim((string)($_GET['resumo_periodo'] ?? 'tudo')); // 'tudo' | '30dias'

    // Filtro temporal para os agregados do resumo (não afeta a listagem de subtarefas)
    $filtroResumo = '';
    $paramResumo = [];
    if ($resumo_periodo === '30dias') {
        $filtroResumo = ' AND criado_em >= DATE_SUB(NOW(), INTERVAL 30 DAY)';
        $filtroResumoRef = ' AND referencia_data >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)';
        $filtroResumoData = ' AND data_pagamento >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)';
    } else {
        $filtroResumoRef = '';
        $filtroResumoData = '';
    }

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
            a.titulo AS atividade_titulo,
            a.status AS status_atividade
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

    // Agregar horas trabalhadas e declaradas ACUMULADAS por membro (todas as datas)
    $userIds = array_unique(array_column($linhas, 'user_id'));

    $mapaCron = [];   // horas cronometradas (cronometro_relatorios)
    $mapaOcio = [];   // horas ociosas (cronometro_relatorios)
    $mapaDecl = [];   // total declarado (todas as subtarefas)
    $mapaDeclNaoPago = []; // declarado não pago (para modal de edição)
    $mapaPago = [];   // total de pagamentos

    foreach ($userIds as $uid) {
        // Horas cronometradas e ociosas (cronometro_relatorios — fonte real do cronômetro)
        $stC = $pdo->prepare("
            SELECT COALESCE(SUM(segundos_trabalhando), 0) AS trab,
                   COALESCE(SUM(segundos_ocioso), 0) AS ocio
            FROM cronometro_relatorios
            WHERE user_id = :uid {$filtroResumoRef}
        ");
        $stC->execute([':uid' => $uid]);
        $cron = $stC->fetch(PDO::FETCH_ASSOC);
        $mapaCron[$uid] = (int)($cron['trab'] ?? 0);
        $mapaOcio[$uid] = (int)($cron['ocio'] ?? 0);

        // Total declarado (TODAS as subtarefas)
        $stD = $pdo->prepare("
            SELECT COALESCE(SUM(segundos_gastos), 0)
            FROM atividades_subtarefas
            WHERE user_id = :uid {$filtroResumoRef}
        ");
        $stD->execute([':uid' => $uid]);
        $mapaDecl[$uid] = (int)$stD->fetchColumn();

        // Total declarado (apenas NÃO pagas — para compatibilidade com modal de edição)
        $stDnp = $pdo->prepare("
            SELECT COALESCE(SUM(segundos_gastos), 0)
            FROM atividades_subtarefas
            WHERE user_id = :uid AND bloqueada_pagamento = 0
        ");
        $stDnp->execute([':uid' => $uid]);
        $mapaDeclNaoPago[$uid] = (int)$stDnp->fetchColumn();

        // Total pago (soma dos pagamentos)
        $stP = $pdo->prepare("
            SELECT COALESCE(SUM(p.valor), 0)
            FROM Pagamentos p
            JOIN usuarios u ON u.id_usuario = p.id_usuario
            WHERE u.user_id = :uid {$filtroResumoData}
        ");
        $stP->execute([':uid' => $uid]);
        $mapaPago[$uid] = (float)$stP->fetchColumn();
    }

    foreach ($linhas as &$l) {
        $uid = $l['user_id'];
        $decl = $mapaDecl[$uid] ?? 0;
        $cron = $mapaCron[$uid] ?? 0;
        $naoDecl = max(0, $cron - $decl);

        $l['segundos_cronometrados_total'] = $cron;
        $l['segundos_ocioso_total']        = $mapaOcio[$uid] ?? 0;
        $l['segundos_declarados_total']    = $mapaDeclNaoPago[$uid] ?? 0;
        $l['segundos_declarados_total_geral'] = $decl;
        $l['segundos_nao_declarado_total'] = $naoDecl;
        $l['segundos_trabalhados_total']   = $decl + $naoDecl;
        $l['total_pago']                   = $mapaPago[$uid] ?? 0.0;
    }

    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    responder_json(false, 'Falha ao listar tarefas declaradas', ['erro' => $e->getMessage()], 500);
}
