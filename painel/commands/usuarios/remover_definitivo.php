<?php
declare(strict_types=1);

/**
 * Remoção DEFINITIVA (hard delete) de um usuário.
 *
 * Diferente de excluir.php (que só inativa: status_conta='inativa'), este
 * endpoint apaga o usuário e TODO o rastro dele no banco — mas SÓ se a conta
 * estiver realmente vazia, pra evitar perder histórico:
 *   - 0 tarefas declaradas (concluídas) em toda a existência
 *   - 0 pagamentos
 *   - 0 arquivos enviados ao MEGA (mega_uploads)
 *
 * GET  ?user_id=...  -> retorna a elegibilidade (pra habilitar/desabilitar o botão)
 * POST {user_id}     -> remove de vez (revalida a elegibilidade no servidor)
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/log_atividades.php';

function remover_def_contar_elegibilidade(PDO $pdo, string $user_id): array
{
    $st = $pdo->prepare("SELECT COUNT(*) FROM atividades_subtarefas WHERE user_id = :u AND concluida = 1");
    $st->execute([':u' => $user_id]);
    $declaradas = (int)$st->fetchColumn();

    $st = $pdo->prepare("
        SELECT COUNT(*) FROM Pagamentos p
        JOIN usuarios u ON u.id_usuario = p.id_usuario
        WHERE u.user_id = :u
    ");
    $st->execute([':u' => $user_id]);
    $pagamentos = (int)$st->fetchColumn();

    $uploads = 0;
    try {
        $st = $pdo->prepare("SELECT COUNT(*) FROM mega_uploads WHERE user_id = :u");
        $st->execute([':u' => $user_id]);
        $uploads = (int)$st->fetchColumn();
    } catch (Throwable $ignore) {
        $uploads = 0; // tabela pode não existir em banco antigo
    }

    $motivos = [];
    if ($declaradas > 0) $motivos[] = "{$declaradas} tarefa(s) declarada(s)";
    if ($pagamentos > 0) $motivos[] = "{$pagamentos} pagamento(s)";
    if ($uploads > 0)    $motivos[] = "{$uploads} arquivo(s) no MEGA";

    return [
        'declaradas' => $declaradas,
        'pagamentos' => $pagamentos,
        'uploads'    => $uploads,
        'removivel'  => empty($motivos),
        'motivos'    => $motivos,
    ];
}

try {
    $pdo = obter_conexao_pdo();
    $metodo = strtoupper((string)($_SERVER['REQUEST_METHOD'] ?? 'GET'));

    // ---- GET: só consulta a elegibilidade ----
    if ($metodo === 'GET') {
        $user_id = normalizar_user_id((string)($_GET['user_id'] ?? ''));
        if ($user_id === '') {
            responder_json(false, "user_id inválido", null, 400);
        }
        responder_json(true, "OK", remover_def_contar_elegibilidade($pdo, $user_id));
    }

    // ---- POST: remove de vez ----
    $entrada = ler_json_do_corpo();
    $user_id = normalizar_user_id((string)($entrada['user_id'] ?? ''));
    if ($user_id === '') {
        responder_json(false, "user_id inválido", null, 400);
    }

    $stU = $pdo->prepare("SELECT id_usuario FROM usuarios WHERE user_id = :u LIMIT 1");
    $stU->execute([':u' => $user_id]);
    $id_usuario = $stU->fetchColumn();
    if ($id_usuario === false) {
        responder_json(false, "Usuário não encontrado", ['user_id' => $user_id], 404);
    }
    $id_usuario = (int)$id_usuario;

    // Revalidação autoritativa: nunca remove quem tem histórico.
    $elig = remover_def_contar_elegibilidade($pdo, $user_id);
    if (!$elig['removivel']) {
        responder_json(
            false,
            "Não dá pra remover: o usuário tem " . implode(', ', $elig['motivos']) . ".",
            $elig,
            409
        );
    }

    $pdo->beginTransaction();

    // Helper: executa DELETE tolerando tabela inexistente em bancos antigos.
    $del = function (string $sql, array $params) use ($pdo): int {
        try {
            $st = $pdo->prepare($sql);
            $st->execute($params);
            return $st->rowCount();
        } catch (Throwable $ignore) {
            return 0;
        }
    };

    $u  = [':u' => $user_id];
    $id = [':id' => $id_usuario];

    // Ordem FK-safe: filhos primeiro, usuário por último.
    $del("DELETE FROM atividades_subtarefas_historico WHERE user_id_alvo = :u OR user_id_executor = :u", $u);
    $del("DELETE FROM declaracoes_dia_itens WHERE user_id = :u", $u);
    $del("DELETE FROM atividades_subtarefas WHERE user_id = :u", $u); // só abertas (gate garante 0 declaradas)
    $del("DELETE FROM cronometro_input_stats WHERE user_id = :u", $u);
    $del("DELETE FROM cronometro_apps_intervalos WHERE user_id = :u", $u);
    $del("DELETE FROM cronometro_foco_janela WHERE user_id = :u", $u);
    $del("DELETE FROM cronometro_eventos_status WHERE user_id = :u", $u);
    $del("DELETE FROM cronometro_finalizacoes WHERE user_id = :u", $u);
    $del("DELETE FROM cronometro_relatorios WHERE user_id = :u", $u);
    $del("DELETE FROM cronometro_sessoes WHERE user_id = :u", $u);
    $del("DELETE FROM usuarios_status_atual WHERE user_id = :u", $u);
    $del("DELETE FROM registros_tempo WHERE user_id = :u", $u);
    $del("DELETE FROM pagamento_abatimentos WHERE user_id = :u", $u);
    $del("DELETE FROM mega_uploads WHERE user_id = :u", $u);          // 0 (gate)
    $del("DELETE FROM mega_campos_upload WHERE user_id = :u", $u);
    $del("DELETE FROM credenciais_usuario WHERE user_id = :u", $u);
    $del("DELETE FROM atividades_usuarios WHERE id_usuario = :id", $id);
    $del("DELETE FROM Pagamentos WHERE id_usuario = :id", $id);       // 0 (gate)

    $stDel = $pdo->prepare("DELETE FROM usuarios WHERE user_id = :u AND id_usuario = :id");
    $stDel->execute([':u' => $user_id, ':id' => $id_usuario]);
    $removidos = $stDel->rowCount();

    $pdo->commit();

    log_registrar(
        $pdo,
        'usuario',
        'removeu_definitivo',
        "Removeu DEFINITIVAMENTE o usuário {$user_id} (conta vazia: 0 declaradas, 0 pagamentos, 0 uploads)",
        ['user_id' => $user_id, 'id_usuario' => $id_usuario],
        ['user_id' => $user_id],
        $user_id
    );

    responder_json(true, "Usuário removido definitivamente.", [
        'user_id'   => $user_id,
        'removidos' => $removidos,
    ]);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = (function_exists('debug_ativo') && debug_ativo()) ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, "falha ao remover usuário", $dados, 500);
}
