<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/log_atividades.php';

try {
    $pdo = obter_conexao_pdo();

    // Cleanup automatico (remove logs > 60 dias, LIMIT 5000 por request)
    log_atividades_cleanup($pdo, 60);

    // Filtros via GET
    $pagina      = max(1, (int)($_GET['pagina'] ?? 1));
    $por_pagina  = min(100, max(10, (int)($_GET['por_pagina'] ?? 50)));
    $entidade    = trim((string)($_GET['entidade'] ?? ''));
    $acao        = trim((string)($_GET['acao'] ?? ''));
    $executor    = trim((string)($_GET['executor'] ?? ''));
    $busca       = trim((string)($_GET['busca'] ?? ''));
    $data_inicio = trim((string)($_GET['data_inicio'] ?? ''));
    $data_fim    = trim((string)($_GET['data_fim'] ?? ''));

    // Montar WHERE dinamico
    $wheres = [];
    $params = [];

    if ($entidade !== '') {
        $wheres[] = 'l.entidade = :entidade';
        $params[':entidade'] = $entidade;
    }
    if ($acao !== '') {
        $wheres[] = 'l.acao = :acao';
        $params[':acao'] = $acao;
    }
    if ($executor !== '') {
        $wheres[] = 'l.user_id_executor = :executor';
        $params[':executor'] = $executor;
    }
    if ($busca !== '') {
        $wheres[] = 'l.descricao LIKE :busca';
        $params[':busca'] = '%' . $busca . '%';
    }
    if ($data_inicio !== '') {
        $wheres[] = 'l.data_hora >= :data_inicio';
        $params[':data_inicio'] = $data_inicio . ' 00:00:00';
    }
    if ($data_fim !== '') {
        $wheres[] = 'l.data_hora <= :data_fim';
        $params[':data_fim'] = $data_fim . ' 23:59:59';
    }

    $where_sql = count($wheres) > 0 ? 'WHERE ' . implode(' AND ', $wheres) : '';

    // Total de registros (para paginacao)
    $stCount = $pdo->prepare("SELECT COUNT(*) FROM log_atividades l $where_sql");
    $stCount->execute($params);
    $total = (int)$stCount->fetchColumn();

    // Buscar registros paginados
    $offset = ($pagina - 1) * $por_pagina;
    $stList = $pdo->prepare("
        SELECT l.id_log, l.data_hora, l.user_id_executor, l.entidade, l.acao,
               l.id_entidade, l.descricao, l.ip,
               CASE WHEN l.dados_antes IS NOT NULL THEN 1 ELSE 0 END AS tem_dados_antes,
               CASE WHEN l.dados_depois IS NOT NULL THEN 1 ELSE 0 END AS tem_dados_depois
        FROM log_atividades l
        $where_sql
        ORDER BY l.data_hora DESC, l.id_log DESC
        LIMIT :limite OFFSET :offset
    ");
    foreach ($params as $k => $v) {
        $stList->bindValue($k, $v);
    }
    $stList->bindValue(':limite', $por_pagina, PDO::PARAM_INT);
    $stList->bindValue(':offset', $offset, PDO::PARAM_INT);
    $stList->execute();
    $registros = $stList->fetchAll(PDO::FETCH_ASSOC);

    // Buscar valores distintos para os filtros
    $entidades = $pdo->query("SELECT DISTINCT entidade FROM log_atividades ORDER BY entidade")->fetchAll(PDO::FETCH_COLUMN);
    $acoes     = $pdo->query("SELECT DISTINCT acao FROM log_atividades ORDER BY acao")->fetchAll(PDO::FETCH_COLUMN);
    $executores = $pdo->query("SELECT DISTINCT user_id_executor FROM log_atividades WHERE user_id_executor IS NOT NULL ORDER BY user_id_executor")->fetchAll(PDO::FETCH_COLUMN);

    responder_json(true, 'ok', [
        'registros'    => $registros,
        'total'        => $total,
        'pagina'       => $pagina,
        'por_pagina'   => $por_pagina,
        'total_paginas' => (int)ceil($total / $por_pagina),
        'filtros'      => [
            'entidades'  => $entidades,
            'acoes'      => $acoes,
            'executores' => $executores,
        ],
    ]);
} catch (Throwable $e) {
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao listar logs.', $dados, 500);
}
