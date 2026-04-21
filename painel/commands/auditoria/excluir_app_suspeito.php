<?php
// painel/commands/auditoria/excluir_app_suspeito.php
// POST JSON: { id: 5 }  — soft delete (ativo = 0)
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $in = ler_json_do_corpo();
    $id = isset($in['id']) ? (int)$in['id'] : 0;

    if ($id <= 0) {
        responder_json(false, 'ID inválido.', null, 400);
    }

    $pdo = obter_conexao_pdo();

    $stC = $pdo->prepare("SELECT id, ativo FROM auditoria_apps_suspeitos WHERE id = :id");
    $stC->execute([':id' => $id]);
    $row = $stC->fetch(PDO::FETCH_ASSOC);
    if (!$row) {
        responder_json(false, 'Registro não encontrado.', null, 404);
    }

    $st = $pdo->prepare("UPDATE auditoria_apps_suspeitos SET ativo = 0 WHERE id = :id");
    $st->execute([':id' => $id]);

    responder_json(true, 'App desativado.', ['id' => $id, 'ativo' => 0], 200);

} catch (Throwable $e) {
    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = ['erro' => $e->getMessage(), 'arquivo' => $e->getFile(), 'linha' => $e->getLine()];
    }
    responder_json(false, 'falha ao excluir app suspeito', $dados, 500);
}
