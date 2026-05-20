<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/log_atividades.php';

try {
    $id_log = (int)($_GET['id_log'] ?? 0);
    if ($id_log <= 0) {
        responder_json(false, 'id_log inválido.', null, 400);
    }

    $pdo = obter_conexao_pdo();
    log_atividades_garantir_tabela($pdo);

    $st = $pdo->prepare("
        SELECT id_log, data_hora, user_id_executor, entidade, acao,
               id_entidade, descricao, dados_antes, dados_depois, ip
        FROM log_atividades
        WHERE id_log = :id
        LIMIT 1
    ");
    $st->execute([':id' => $id_log]);
    $reg = $st->fetch(PDO::FETCH_ASSOC);

    if (!$reg) {
        responder_json(false, 'Log não encontrado.', null, 404);
    }

    // Decodifica JSON para o frontend
    $reg['dados_antes']  = $reg['dados_antes']  ? json_decode($reg['dados_antes'], true) : null;
    $reg['dados_depois'] = $reg['dados_depois'] ? json_decode($reg['dados_depois'], true) : null;

    responder_json(true, 'ok', $reg);
} catch (Throwable $e) {
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao buscar detalhe do log.', $dados, 500);
}
