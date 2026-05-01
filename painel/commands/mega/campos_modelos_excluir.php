<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

/**
 * POST — soft-delete (ativo=0) de um modelo de campo.
 * Payload: { id_modelo }
 *
 * Não apaga: campos já criados a partir do modelo (em mega_campos_upload)
 * são linhas independentes — não há FK pro modelo.
 */
try {
    $in = ler_json_do_corpo();
    $id_modelo = (int)($in['id_modelo'] ?? 0);

    if ($id_modelo <= 0) {
        responder_json(false, 'id_modelo obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $st = $pdo->prepare("UPDATE mega_campos_modelos SET ativo=0 WHERE id_modelo=?");
    $st->execute([$id_modelo]);

    responder_json(true, 'modelo desativado', ['id_modelo' => $id_modelo]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao desativar modelo', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
