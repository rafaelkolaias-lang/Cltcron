<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

/**
 * GET — lista modelos de campo de upload (templates globais).
 *  - incluir_inativos=1 inclui soft-deleted (default: só ativos).
 */
try {
    $incluir_inativos = !empty($_GET['incluir_inativos']);

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $sql = "
        SELECT id_modelo, nome_modelo, label_campo, extensoes_permitidas,
               quantidade_maxima, obrigatorio, ativo, ordem,
               criado_em, atualizado_em
          FROM mega_campos_modelos
    ";
    if (!$incluir_inativos) $sql .= ' WHERE ativo = 1';
    $sql .= ' ORDER BY ordem ASC, nome_modelo ASC, id_modelo ASC';

    $linhas = $pdo->query($sql)->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$l) {
        $l['id_modelo']         = (int)$l['id_modelo'];
        $l['quantidade_maxima'] = (int)$l['quantidade_maxima'];
        $l['obrigatorio']       = (int)$l['obrigatorio'] === 1;
        $l['ativo']             = (int)$l['ativo'] === 1;
        $l['ordem']             = (int)$l['ordem'];
    }

    responder_json(true, 'OK', $linhas);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar modelos de campo', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
