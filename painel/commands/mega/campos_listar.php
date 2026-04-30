<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

/**
 * GET ?user_id=X&id_atividade=Y
 *  - Filtros opcionais: se omitidos, lista tudo.
 *  - incluir_inativos=1 mostra também desativados (default: só ativos).
 */
try {
    $user_id      = isset($_GET['user_id'])      ? normalizar_user_id((string)$_GET['user_id']) : '';
    $id_atividade = isset($_GET['id_atividade']) ? (int)$_GET['id_atividade'] : 0;
    $incluir_inativos = !empty($_GET['incluir_inativos']);

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $where  = [];
    $params = [];
    if ($user_id !== '')      { $where[] = 'c.user_id = ?';      $params[] = $user_id; }
    if ($id_atividade > 0)    { $where[] = 'c.id_atividade = ?'; $params[] = $id_atividade; }
    if (!$incluir_inativos)   { $where[] = 'c.ativo = 1'; }

    $sql = "
        SELECT c.id_campo, c.user_id, c.id_atividade,
               c.label_campo, c.extensoes_permitidas, c.quantidade_maxima,
               c.obrigatorio, c.ordem, c.ativo,
               c.criado_em, c.atualizado_em,
               u.nome_exibicao,
               a.titulo AS titulo_atividade
        FROM mega_campos_upload c
        LEFT JOIN usuarios   u ON u.user_id      = c.user_id
        LEFT JOIN atividades a ON a.id_atividade = c.id_atividade
    ";
    if ($where) $sql .= ' WHERE ' . implode(' AND ', $where);
    $sql .= ' ORDER BY u.nome_exibicao ASC, a.titulo ASC, c.ordem ASC, c.id_campo ASC';

    $st = $pdo->prepare($sql);
    $st->execute($params);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$l) {
        $l['id_campo']          = (int)$l['id_campo'];
        $l['id_atividade']      = (int)$l['id_atividade'];
        $l['quantidade_maxima'] = (int)$l['quantidade_maxima'];
        $l['obrigatorio']       = (int)$l['obrigatorio'] === 1;
        $l['ordem']             = (int)$l['ordem'];
        $l['ativo']             = (int)$l['ativo'] === 1;
    }

    responder_json(true, 'OK', $linhas);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar campos de upload', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
