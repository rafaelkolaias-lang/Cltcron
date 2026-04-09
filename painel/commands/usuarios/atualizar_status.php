<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function ler_json_entrada(): array
{
    $raw = file_get_contents('php://input');
    $obj = json_decode($raw ?: '', true);
    return is_array($obj) ? $obj : [];
}

function normalizar_status(string $status): string
{
    $s = strtolower(trim($status));
    if (in_array($s, ['ativa', 'inativa'], true)) return $s;
    return '';
}

try {
    $in = ler_json_entrada();

    $user_id = trim((string)($in['user_id'] ?? ''));
    $status_conta = normalizar_status((string)($in['status_conta'] ?? ''));

    if ($user_id === '') responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
    if ($status_conta === '') responder_json(false, 'status_conta inválido (ativa/inativa).', ['campo' => 'status_conta'], 400);

    $pdo = obter_conexao_pdo();

    $st = $pdo->prepare("
        UPDATE usuarios
        SET status_conta = :status_conta
        WHERE user_id = :user_id
    ");
    $st->execute([
        ':status_conta' => $status_conta,
        ':user_id' => $user_id,
    ]);

    $st2 = $pdo->prepare("SELECT id_usuario FROM usuarios WHERE user_id = :user_id LIMIT 1");
    $st2->execute([':user_id' => $user_id]);
    if (!$st2->fetch()) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }

    responder_json(true, 'Status atualizado.', [
        'user_id' => $user_id,
        'status_conta' => $status_conta,
    ], 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao atualizar status', ['erro' => $e->getMessage()], 500);
}
