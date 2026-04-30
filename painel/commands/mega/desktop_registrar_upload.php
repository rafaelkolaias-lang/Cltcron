<?php
declare(strict_types=1);

/**
 * desktop_registrar_upload.php — grava metadado de um upload feito (ou em
 * andamento) pelo desktop. Não armazena o arquivo — só registra que aconteceu.
 *
 * Auth: user_id + chave.
 *
 * POST {
 *   id_pasta_logica, nome_campo, nome_arquivo,
 *   id_subtarefa?, tamanho_bytes?, status_upload? (pendente|enviando|concluido|erro),
 *   mensagem_erro?, id_upload? (para update)
 * }
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $in = ler_json_do_corpo();
    $id_upload       = (int)($in['id_upload'] ?? 0);
    $id_pasta_logica = (int)($in['id_pasta_logica'] ?? 0);
    $id_subtarefa    = isset($in['id_subtarefa']) && $in['id_subtarefa'] !== '' ? (int)$in['id_subtarefa'] : null;
    $nome_campo      = trim((string)($in['nome_campo'] ?? ''));
    $nome_arquivo    = trim((string)($in['nome_arquivo'] ?? ''));
    $tamanho_bytes   = isset($in['tamanho_bytes']) && $in['tamanho_bytes'] !== '' ? (int)$in['tamanho_bytes'] : null;
    $status          = strtolower(trim((string)($in['status_upload'] ?? 'pendente')));
    $mensagem_erro   = isset($in['mensagem_erro']) ? trim((string)$in['mensagem_erro']) : null;

    $status_validos = ['pendente', 'enviando', 'concluido', 'erro'];
    if (!in_array($status, $status_validos, true)) {
        responder_json(false, 'status_upload inválido', null, 400);
    }
    if ($id_upload <= 0 && ($id_pasta_logica <= 0 || $nome_campo === '' || $nome_arquivo === '')) {
        responder_json(false, 'id_pasta_logica, nome_campo e nome_arquivo obrigatórios na criação', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $enviado_em = ($status === 'concluido') ? date('Y-m-d H:i:s') : null;

    if ($id_upload > 0) {
        // UPDATE: só permite atualizar registros do próprio user (defesa).
        $st = $pdo->prepare("
            UPDATE mega_uploads
               SET status_upload = ?, mensagem_erro = ?, tamanho_bytes = COALESCE(?, tamanho_bytes),
                   enviado_em = COALESCE(?, enviado_em),
                   id_subtarefa = COALESCE(?, id_subtarefa)
             WHERE id_upload = ? AND user_id = ?
        ");
        $st->execute([$status, $mensagem_erro, $tamanho_bytes, $enviado_em, $id_subtarefa, $id_upload, $user_id]);
        if ($st->rowCount() === 0) {
            responder_json(false, 'upload não encontrado para este usuário', null, 404);
        }
        responder_json(true, 'upload atualizado', ['id_upload' => $id_upload, 'status_upload' => $status]);
    }

    // Confere que a pasta lógica existe e está ativa.
    $st = $pdo->prepare("SELECT 1 FROM mega_pasta_logica WHERE id_pasta_logica=? AND ativo=1 LIMIT 1");
    $st->execute([$id_pasta_logica]);
    if (!$st->fetchColumn()) {
        responder_json(false, 'pasta lógica não encontrada ou inativa', null, 404);
    }

    $st = $pdo->prepare("
        INSERT INTO mega_uploads
            (id_pasta_logica, id_subtarefa, user_id, nome_campo, nome_arquivo,
             tamanho_bytes, status_upload, mensagem_erro, enviado_em)
        VALUES (?,?,?,?,?,?,?,?,?)
    ");
    $st->execute([
        $id_pasta_logica, $id_subtarefa, $user_id, $nome_campo, $nome_arquivo,
        $tamanho_bytes, $status, $mensagem_erro, $enviado_em,
    ]);

    responder_json(true, 'upload registrado', [
        'id_upload'     => (int)$pdo->lastInsertId(),
        'status_upload' => $status,
    ], 201);
} catch (Throwable $e) {
    responder_json(false, 'falha ao registrar upload', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
