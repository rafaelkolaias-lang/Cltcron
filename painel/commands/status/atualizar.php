<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $entrada = ler_json_do_corpo();

    $user_id = normalizar_user_id((string)($entrada['user_id'] ?? ''));
    $situacao = strtolower(trim((string)($entrada['situacao'] ?? 'ocioso')));
    $atividade = trim((string)($entrada['atividade'] ?? ''));
    $inicio_iso = trim((string)($entrada['inicio_iso'] ?? ''));
    $segundos_pausado = (int)($entrada['segundos_pausado'] ?? 0);
    $apps = $entrada['apps'] ?? [];

    if ($user_id === '') {
        responder_json(false, "user_id inválido", null, 400);
    }
    if (!situacao_valida($situacao)) {
        responder_json(false, "situacao inválida", null, 400);
    }
    if (!is_array($apps)) {
        $apps = [];
    }

    $pdo = obter_conexao_pdo();

    // garante que usuário existe e está ativo (se quiser permitir atualizar mesmo inativo, remova esse check)
    $chk = $pdo->prepare("SELECT status_conta FROM usuarios WHERE user_id = :user_id LIMIT 1");
    $chk->execute([':user_id' => $user_id]);
    $status = $chk->fetchColumn();
    if (!$status) {
        responder_json(false, "Usuário não encontrado", ['user_id' => $user_id], 404);
    }

    $inicio_em = null;
    if ($inicio_iso !== '') {
        // aceita "2026-02-03T10:00:00" ou "2026-02-03 10:00:00"
        $inicio_iso = str_replace('T', ' ', $inicio_iso);
        $inicio_em = $inicio_iso;
    }

    $apps_json = json_encode(array_values($apps), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

    // UPSERT
    $sql = "INSERT INTO usuarios_status_atual (user_id, situacao, atividade, inicio_em, ultimo_em, segundos_pausado, apps_json)
            VALUES (:user_id, :situacao, :atividade, :inicio_em, NOW(), :segundos_pausado, :apps_json)
            ON DUPLICATE KEY UPDATE
              situacao = VALUES(situacao),
              atividade = VALUES(atividade),
              inicio_em = VALUES(inicio_em),
              ultimo_em = NOW(),
              segundos_pausado = VALUES(segundos_pausado),
              apps_json = VALUES(apps_json)";

    $stm = $pdo->prepare($sql);
    $stm->execute([
        ':user_id' => $user_id,
        ':situacao' => $situacao,
        ':atividade' => $atividade,
        ':inicio_em' => $inicio_em,
        ':segundos_pausado' => $segundos_pausado,
        ':apps_json' => $apps_json,
    ]);

    responder_json(true, "Status atualizado", ['user_id' => $user_id]);
} catch (Throwable $e) {
    responder_json(false, "falha ao atualizar status", ['erro' => $e->getMessage()], 500);
}
