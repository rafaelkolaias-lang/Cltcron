<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function ler_json_entrada_visibilidade(): array
{
    $raw = file_get_contents('php://input');
    $obj = json_decode($raw ?: '', true);
    return is_array($obj) ? $obj : [];
}

try {
    $in = ler_json_entrada_visibilidade();

    $user_id = trim((string)($in['user_id'] ?? ''));
    if ($user_id === '') {
        responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
    }

    if (!array_key_exists('ocultar_dashboard', $in)) {
        responder_json(false, 'ocultar_dashboard é obrigatório (0 ou 1).', ['campo' => 'ocultar_dashboard'], 400);
    }
    $ocultar = (int)((bool)$in['ocultar_dashboard']);

    $pdo = obter_conexao_pdo();

    $st = $pdo->prepare("UPDATE usuarios SET ocultar_dashboard = :ocultar WHERE user_id = :user_id");
    $st->execute([
        ':ocultar' => $ocultar,
        ':user_id' => $user_id,
    ]);

    $st2 = $pdo->prepare("SELECT id_usuario FROM usuarios WHERE user_id = :user_id LIMIT 1");
    $st2->execute([':user_id' => $user_id]);
    if (!$st2->fetch()) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }

    responder_json(true, $ocultar ? 'Usuário oculto do Dashboard.' : 'Usuário visível no Dashboard.', [
        'user_id' => $user_id,
        'ocultar_dashboard' => $ocultar,
    ], 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao alterar visibilidade no Dashboard', ['erro' => $e->getMessage()], 500);
}
