<?php
declare(strict_types=1);

/**
 * obter.php — entrega o payload de UMA credencial do usuário autenticado,
 * recifrado com APP_CLIENT_DECRYPT_KEY (compartilhada por todos os apps).
 *
 * Entrada:
 *   GET  ?identificador=chatgpt
 *   (auth via header — ver _auth_cliente.php)
 *
 * Resposta (ok):
 *   {
 *     "ok": true,
 *     "mensagem": "OK",
 *     "dados": {
 *       "user_id": "rafael",
 *       "identificador": "chatgpt",
 *       "id_modelo": 1,
 *       "versao_cliente": 1,
 *       "encoding": "base64",
 *       "cipher": "<base64>",    // cifrado com APP_CLIENT_DECRYPT_KEY
 *       "nonce":  "<base64>",    // 24 bytes
 *       "emitido_em": "2026-04-13T10:20:00Z"
 *     }
 *   }
 *
 * Erros:
 *   401 — não autorizado (user_id/chave inválidos)
 *   403 — conta inativa/bloqueada ou credencial revogada
 *   404 — credencial não preenchida
 */

require_once __DIR__ . '/../../_comum/resposta.php';
require_once __DIR__ . '/../../conexao/conexao.php';
require_once __DIR__ . '/../../_comum/cripto.php';
require_once __DIR__ . '/_auth_cliente.php';

try {
    $u = autenticar_cliente_ou_morrer();

    $ident = strtolower(trim((string)($_GET['identificador'] ?? '')));
    $ident = preg_replace('/[^a-z0-9_\-]/', '', $ident) ?? '';
    if ($ident === '') {
        responder_json(false, 'identificador obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    $sql = "SELECT c.id_credencial, c.id_modelo, c.valor_cifrado, c.nonce, c.versao_chave, c.status,
                   m.identificador
              FROM credenciais_usuario c
              JOIN credenciais_modelos m ON m.id_modelo = c.id_modelo
             WHERE c.user_id = ? AND m.identificador = ? AND m.status = 'ativo'
             LIMIT 1";
    $stm = $pdo->prepare($sql);
    $stm->execute([$u['user_id'], $ident]);
    $row = $stm->fetch();

    if (!$row) {
        responder_json(false, 'credencial não preenchida para este usuário', null, 404);
    }
    if ($row['status'] === 'revogado') {
        responder_json(false, 'credencial revogada', null, 403);
    }

    // 1) decifra com a chave mestra
    $puro = decifrar_segredo(
        (string)$row['valor_cifrado'],
        (string)$row['nonce'],
        (int)$row['versao_chave']
    );

    // 2) recifra com a chave fixa do cliente
    $rec = cifrar_para_cliente($puro);
    sodium_memzero($puro);

    // 3) auditoria leve (sem valor)
    try {
        $stm = $pdo->prepare("UPDATE credenciais_usuario SET ultimo_acesso_em=CURRENT_TIMESTAMP WHERE id_credencial=?");
        $stm->execute([$row['id_credencial']]);
    } catch (Throwable $_ignore) { /* não bloquear entrega por causa de auditoria */ }

    responder_json(true, 'OK', [
        'user_id'        => $u['user_id'],
        'identificador'  => $row['identificador'],
        'id_modelo'      => (int)$row['id_modelo'],
        'versao_cliente' => 1,
        'encoding'       => 'base64',
        'cipher'         => base64_encode($rec['cipher']),
        'nonce'          => base64_encode($rec['nonce']),
        'emitido_em'     => gmdate('Y-m-d\TH:i:s\Z'),
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao obter credencial', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
