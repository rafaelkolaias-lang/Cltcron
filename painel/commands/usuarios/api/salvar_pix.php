<?php
declare(strict_types=1);

/**
 * salvar_pix.php — salva/atualiza a chave Pix do próprio usuário autenticado.
 *
 * Entrada (POST JSON ou form):
 *   { "chave_pix": "..." }   — string vazia ou null = limpa o cadastro.
 *
 * Validação espelhada de `_comum/pix.php` (CNPJ DV, celular BR 10–11, e-mail).
 * Recusa CPF e qualquer outro formato.
 *
 * Resposta:
 *   { ok: true, dados: { chave_pix: "<normalizada>"|null, tipo: "cnpj|celular|email|null" } }
 */

require_once __DIR__ . '/../../_comum/resposta.php';
require_once __DIR__ . '/../../_comum/usuarios_estrutura.php';
require_once __DIR__ . '/../../_comum/pix.php';
require_once __DIR__ . '/../../conexao/conexao.php';
require_once __DIR__ . '/../../credenciais/api/_auth_cliente.php';

try {
    $u = autenticar_cliente_ou_morrer();

    $bruto = '';
    $body = file_get_contents('php://input');
    if ($body !== false && $body !== '') {
        $j = json_decode($body, true);
        if (is_array($j) && array_key_exists('chave_pix', $j)) {
            $bruto = (string)($j['chave_pix'] ?? '');
        }
    }
    if ($bruto === '' && isset($_POST['chave_pix'])) {
        $bruto = (string)$_POST['chave_pix'];
    }

    $pdo = obter_conexao_pdo();
    usuarios_garantir_chave_pix($pdo);

    $bruto_trim = trim($bruto);
    if ($bruto_trim === '') {
        // Limpar
        $stm = $pdo->prepare("UPDATE usuarios SET chave_pix = NULL WHERE user_id = ?");
        $stm->execute([$u['user_id']]);
        responder_json(true, 'Chave Pix removida.', ['chave_pix' => null, 'tipo' => null]);
    }

    try {
        $r = pix_validar($bruto_trim);
    } catch (InvalidArgumentException $e) {
        responder_json(false, $e->getMessage(), null, 400);
    }

    $stm = $pdo->prepare("UPDATE usuarios SET chave_pix = ? WHERE user_id = ?");
    $stm->execute([$r['valor'], $u['user_id']]);

    responder_json(true, 'Chave Pix salva.', [
        'chave_pix' => $r['valor'],
        'tipo'      => $r['tipo'],
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao salvar chave Pix', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
