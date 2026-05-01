<?php
declare(strict_types=1);

/**
 * desktop_marcar_pasta_logica_inativa.php — soft-delete da pasta lógica.
 *
 * Chamado pelo desktop quando ele removeu a pasta inteira do MEGA (porque
 * não havia mais nenhuma subtarefa vinculada). Mantém o registro no banco
 * mas marca ativo=0, então deixa de aparecer em "Selecionar existente".
 *
 * Auth: user_id + chave.
 *
 * POST { id_pasta_logica }
 *
 * Resposta: 200 com { id_pasta_logica, ativo:0 }.
 *
 * Idempotente: se já estiver inativa, retorna 200 sem erro.
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $in = ler_json_do_corpo();
    $id_pasta_logica = (int)($in['id_pasta_logica'] ?? 0);
    if ($id_pasta_logica <= 0) {
        responder_json(false, 'id_pasta_logica obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Defesa contra IDOR: só pode inativar pastas de canais aos quais o user
    // pertence. Sem isso, qualquer user autenticado poderia desativar pastas
    // de outros canais e bagunçar o trabalho dos colegas.
    [$ok, $id_atividade] = mega_user_pertence_pasta_logica($pdo, $user_id, $id_pasta_logica);
    if ($id_atividade <= 0) {
        responder_json(false, 'pasta lógica não encontrada', null, 404);
    }
    if (!$ok) {
        responder_json(false, 'usuário não tem acesso a esta atividade', null, 403);
    }

    $st = $pdo->prepare("UPDATE mega_pasta_logica SET ativo=0 WHERE id_pasta_logica=?");
    $st->execute([$id_pasta_logica]);

    responder_json(true, 'pasta lógica marcada como inativa', [
        'id_pasta_logica' => $id_pasta_logica,
        'ativo'           => 0,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao marcar pasta lógica inativa', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
