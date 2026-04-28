<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/credenciais_upsert.php';

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

    // Confere existência antes do UPDATE para distinguir "não encontrado"
    // de "status já era esse" (ambos resultariam em rowCount=0).
    $st0 = $pdo->prepare("SELECT status_conta FROM usuarios WHERE user_id = :user_id LIMIT 1");
    $st0->execute([':user_id' => $user_id]);
    $atual = $st0->fetch();
    if (!$atual) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }
    $status_anterior = strtolower((string)$atual['status_conta']);

    $st = $pdo->prepare("
        UPDATE usuarios
        SET status_conta = :status_conta
        WHERE user_id = :user_id
    ");
    $st->execute([
        ':status_conta' => $status_conta,
        ':user_id' => $user_id,
    ]);

    // Sincroniza credenciais com o novo status:
    //  - Desativando (ativa -> inativa): revoga todas as credenciais ativas do usuário.
    //  - Reativando  (inativa -> ativa): reativa as que estavam revogadas.
    // Trocas no mesmo status (idempotentes) não disparam nada.
    $credenciais_afetadas = 0;
    if ($status_anterior !== $status_conta) {
        if ($status_conta === 'inativa') {
            $credenciais_afetadas = revogar_credenciais_de_usuario($pdo, $user_id);
        } elseif ($status_conta === 'ativa') {
            $credenciais_afetadas = reativar_credenciais_revogadas_de_usuario($pdo, $user_id);
        }
    }

    responder_json(true, 'Status atualizado.', [
        'user_id' => $user_id,
        'status_conta' => $status_conta,
        'credenciais_afetadas' => $credenciais_afetadas,
    ], 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao atualizar status', ['erro' => $e->getMessage()], 500);
}
