<?php
// painel/commands/auditoria/listar_apps_suspeitos.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    $incluir_inativos = isset($_GET['incluir_inativos']) && $_GET['incluir_inativos'] === '1';

    $sql = "
        SELECT
            id,
            nome_app,
            motivo,
            ativo,
            criado_em,
            criado_por,
            atualizado_em
        FROM auditoria_apps_suspeitos
    ";
    if (!$incluir_inativos) {
        $sql .= " WHERE ativo = 1 ";
    }
    $sql .= " ORDER BY nome_app ASC ";

    $st = $pdo->prepare($sql);
    $st->execute();
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$l) {
        $l['id']    = (int)$l['id'];
        $l['ativo'] = (int)$l['ativo'];
    }

    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = ['erro' => $e->getMessage(), 'arquivo' => $e->getFile(), 'linha' => $e->getLine()];
    }
    responder_json(false, 'falha ao listar apps suspeitos', $dados, 500);
}
