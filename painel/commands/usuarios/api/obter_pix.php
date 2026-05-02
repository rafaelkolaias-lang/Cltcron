<?php
declare(strict_types=1);

/**
 * obter_pix.php — retorna a chave Pix do próprio usuário autenticado.
 *
 * Auth: ver `painel/commands/credenciais/api/_auth_cliente.php`
 *       (Bearer user:chave OU X-User-Id+X-User-Chave OU query string).
 *
 * Resposta:
 *   { ok: true, dados: { chave_pix: "..."|null, tipo: "cnpj|celular|email|null" } }
 *
 * Nunca retorna a Pix de outro usuário — sempre a do `user_id` autenticado.
 */

require_once __DIR__ . '/../../_comum/resposta.php';
require_once __DIR__ . '/../../_comum/usuarios_estrutura.php';
require_once __DIR__ . '/../../_comum/pix.php';
require_once __DIR__ . '/../../conexao/conexao.php';
require_once __DIR__ . '/../../credenciais/api/_auth_cliente.php';

try {
    $u = autenticar_cliente_ou_morrer();

    $pdo = obter_conexao_pdo();
    usuarios_garantir_chave_pix($pdo);

    $stm = $pdo->prepare("SELECT chave_pix FROM usuarios WHERE user_id = ? LIMIT 1");
    $stm->execute([$u['user_id']]);
    $row = $stm->fetch();

    $chave = $row ? (string)($row['chave_pix'] ?? '') : '';
    $tipo = null;
    if ($chave !== '') {
        try {
            $r = pix_validar($chave);
            $tipo = $r['tipo'];
        } catch (Throwable $_e) {
            // Valor armazenado é inválido (não deveria, mas tolera) — só não classifica.
            $tipo = null;
        }
    }

    responder_json(true, 'OK', [
        'chave_pix' => $chave !== '' ? $chave : null,
        'tipo'      => $tipo,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao obter chave Pix', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
