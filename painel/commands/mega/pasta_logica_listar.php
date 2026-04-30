<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

/**
 * GET ?id_atividade=Y  — lista pastas lógicas cadastradas para um canal.
 *  - incluir_inativas=1 mostra também desativadas (default: só ativas).
 */
try {
    $id_atividade     = isset($_GET['id_atividade']) ? (int)$_GET['id_atividade'] : 0;
    $incluir_inativas = !empty($_GET['incluir_inativas']);

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $where = [];
    $params = [];
    if ($id_atividade > 0) { $where[] = 'p.id_atividade = ?'; $params[] = $id_atividade; }
    if (!$incluir_inativas) { $where[] = 'p.ativo = 1'; }

    $sql = "
        SELECT p.id_pasta_logica, p.id_atividade, p.nome_pasta,
               p.numero_video, p.titulo_video, p.criado_por, p.criado_em, p.ativo,
               a.titulo AS titulo_atividade
        FROM mega_pasta_logica p
        LEFT JOIN atividades a ON a.id_atividade = p.id_atividade
    ";
    if ($where) $sql .= ' WHERE ' . implode(' AND ', $where);
    $sql .= ' ORDER BY a.titulo ASC, p.numero_video ASC, p.criado_em DESC';

    $st = $pdo->prepare($sql);
    $st->execute($params);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$l) {
        $l['id_pasta_logica'] = (int)$l['id_pasta_logica'];
        $l['id_atividade']    = (int)$l['id_atividade'];
        $l['ativo']           = (int)$l['ativo'] === 1;
    }

    responder_json(true, 'OK', $linhas);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar pastas lógicas', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
