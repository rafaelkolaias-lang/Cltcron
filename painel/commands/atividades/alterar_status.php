<?php
// alterar_status.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

function ler_json_entrada(): array
{
    $raw = file_get_contents('php://input');
    $obj = json_decode($raw ?: '', true);
    return is_array($obj) ? $obj : [];
}

function status_valido(string $s): bool
{
    return in_array($s, ['aberta','em_andamento','concluida','cancelada'], true);
}

try {
    $in = ler_json_entrada();

    $id_atividade = (int)($in['id_atividade'] ?? 0);
    $status = trim((string)($in['status'] ?? ''));

    if ($id_atividade <= 0) responder_json(false, 'id_atividade inválido.', null, 400);
    if (!status_valido($status)) responder_json(false, 'status inválido.', null, 400);

    $pdo = obter_conexao_pdo();

    $stE = $pdo->prepare("SELECT id_atividade FROM atividades WHERE id_atividade = :id LIMIT 1");
    $stE->execute([':id' => $id_atividade]);
    if (!$stE->fetchColumn()) {
        responder_json(false, 'Atividade não encontrada.', ['id_atividade' => $id_atividade], 404);
    }

    $st = $pdo->prepare("UPDATE atividades SET status = :status WHERE id_atividade = :id");
    $st->execute([
        ':status' => $status,
        ':id' => $id_atividade,
    ]);

    responder_json(true, 'Status atualizado.', ['id_atividade' => $id_atividade, 'status' => $status], 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao alterar status', ['erro' => $e->getMessage()], 500);
}
