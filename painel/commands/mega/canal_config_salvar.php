<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

try {
    $in = ler_json_do_corpo();
    $id_atividade    = (int)($in['id_atividade'] ?? 0);
    $nome_pasta_mega = trim((string)($in['nome_pasta_mega'] ?? ''));
    $upload_ativo    = !empty($in['upload_ativo']) ? 1 : 0;

    if ($id_atividade <= 0) {
        responder_json(false, 'id_atividade obrigatório', null, 400);
    }
    if ($nome_pasta_mega === '' && $upload_ativo === 1) {
        responder_json(false, 'nome_pasta_mega obrigatório quando upload está ativo', null, 400);
    }
    if (strlen($nome_pasta_mega) > 255) {
        responder_json(false, 'nome_pasta_mega acima do limite (255)', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Confere que a atividade existe (defensivo — UI já só mostra existentes).
    $st = $pdo->prepare("SELECT status FROM atividades WHERE id_atividade=? LIMIT 1");
    $st->execute([$id_atividade]);
    $status_atividade = $st->fetchColumn();
    if ($status_atividade === false) {
        responder_json(false, 'atividade não encontrada', null, 404);
    }
    if (strtolower((string)$status_atividade) === 'cancelada') {
        responder_json(false, 'canal cancelado não pode ser configurado no MEGA', null, 409);
    }

    $st = $pdo->prepare("
        INSERT INTO mega_canal_config (id_atividade, nome_pasta_mega, upload_ativo)
        VALUES (?, ?, ?)
        ON DUPLICATE KEY UPDATE
            nome_pasta_mega = VALUES(nome_pasta_mega),
            upload_ativo    = VALUES(upload_ativo)
    ");
    $st->execute([$id_atividade, $nome_pasta_mega, $upload_ativo]);

    responder_json(true, 'config salva', [
        'id_atividade'    => $id_atividade,
        'nome_pasta_mega' => $nome_pasta_mega,
        'upload_ativo'    => (bool)$upload_ativo,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao salvar config de canal MEGA', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
