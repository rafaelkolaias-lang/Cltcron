<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

/**
 * POST — soft-delete (ativo=0) de um campo de upload.
 * Payload: { id_campo }
 */
try {
    $in = ler_json_do_corpo();
    $id_campo = (int)($in['id_campo'] ?? 0);

    if ($id_campo <= 0) {
        responder_json(false, 'id_campo obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $st = $pdo->prepare("UPDATE mega_campos_upload SET ativo=0 WHERE id_campo=?");
    $st->execute([$id_campo]);

    responder_json(true, 'campo desativado', ['id_campo' => $id_campo]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao desativar campo', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
