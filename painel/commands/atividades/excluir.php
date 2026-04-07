<?php
// excluir.php
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

try {
    $in = ler_json_entrada();
    $id_atividade = (int)($in['id_atividade'] ?? 0);

    if ($id_atividade <= 0) responder_json(false, 'id_atividade inválido.', null, 400);

    $pdo = obter_conexao_pdo();

    // existe?
    $stE = $pdo->prepare("SELECT id_atividade FROM atividades WHERE id_atividade = :id LIMIT 1");
    $stE->execute([':id' => $id_atividade]);
    $existe = (bool)$stE->fetchColumn();

    if (!$existe) {
        responder_json(false, 'Atividade não encontrada.', ['id_atividade' => $id_atividade], 404);
    }

    // se tiver finalização, não pode (FK RESTRICT)
    $stF = $pdo->prepare("SELECT COUNT(1) FROM cronometro_finalizacoes WHERE id_atividade = :id");
    $stF->execute([':id' => $id_atividade]);
    $tem_finalizacao = ((int)$stF->fetchColumn()) > 0;

    if ($tem_finalizacao) {
        responder_json(false, 'Não é possível excluir: atividade já foi usada em finalizações.', [
            'id_atividade' => $id_atividade
        ], 409);
    }

    $st = $pdo->prepare("DELETE FROM atividades WHERE id_atividade = :id");
    $st->execute([':id' => $id_atividade]);

    responder_json(true, 'Atividade excluída.', ['id_atividade' => $id_atividade], 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao excluir atividade', ['erro' => $e->getMessage()], 500);
}
