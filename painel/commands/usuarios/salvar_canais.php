<?php
// commands/usuarios/salvar_canais.php
//
// Atualiza os vínculos `atividades_usuarios` de UM usuário a partir da Gestão
// do Usuário, sem mexer nos vínculos de outros usuários nem nos dados dos
// canais. Espelho de `atividades/editar.php` no eixo oposto: lá refazemos os
// usuários de um canal; aqui refazemos os canais de um usuário.
//
// Entrada (JSON):
//   { "user_id": "rk_xxx", "ids_atividades": [1, 2, 5] }
//
// Resposta:
//   { ok: true, mensagem: "...", dados: { user_id, id_usuario, ids_atividades, total } }
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $in = ler_json_do_corpo();

    $user_id = trim((string)($in['user_id'] ?? ''));
    if ($user_id === '') {
        responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
    }

    $ids_atividades_raw = $in['ids_atividades'] ?? [];
    if (!is_array($ids_atividades_raw)) {
        responder_json(false, 'ids_atividades deve ser uma lista.', ['campo' => 'ids_atividades'], 400);
    }

    $ids_validos = [];
    foreach ($ids_atividades_raw as $id) {
        $n = (int)$id;
        if ($n > 0) {
            $ids_validos[$n] = true;
        }
    }
    $ids_validos = array_keys($ids_validos);

    $pdo = obter_conexao_pdo();

    // user_id (string público) → id_usuario (PK numérica)
    $stU = $pdo->prepare('SELECT id_usuario FROM usuarios WHERE user_id = :uid LIMIT 1');
    $stU->execute([':uid' => $user_id]);
    $linhaU = $stU->fetch(PDO::FETCH_ASSOC);
    if (!$linhaU || !isset($linhaU['id_usuario'])) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }
    $id_usuario = (int)$linhaU['id_usuario'];

    // Filtrar canais existentes — evita FK violation e não persiste lixo se
    // o frontend mandar um id obsoleto.
    $ids_finais = [];
    if (!empty($ids_validos)) {
        $placeholders = implode(',', array_fill(0, count($ids_validos), '?'));
        $stA = $pdo->prepare("SELECT id_atividade FROM atividades WHERE id_atividade IN ($placeholders)");
        $stA->execute($ids_validos);
        $ids_finais = array_map('intval', $stA->fetchAll(PDO::FETCH_COLUMN) ?: []);
    }

    $pdo->beginTransaction();

    // Apaga só os vínculos DESTE usuário — não toca em vínculos de outros
    // usuários no mesmo canal, nem em propriedades do canal.
    $stDel = $pdo->prepare('DELETE FROM atividades_usuarios WHERE id_usuario = :uid');
    $stDel->execute([':uid' => $id_usuario]);

    $stIns = $pdo->prepare(
        'INSERT INTO atividades_usuarios (id_atividade, id_usuario)
         VALUES (:id_atividade, :id_usuario)
         ON DUPLICATE KEY UPDATE atribuida_em = atribuida_em'
    );
    foreach ($ids_finais as $id_ativ) {
        $stIns->execute([
            ':id_atividade' => (int)$id_ativ,
            ':id_usuario'   => $id_usuario,
        ]);
    }

    $pdo->commit();

    responder_json(true, 'Canais vinculados atualizados.', [
        'user_id'        => $user_id,
        'id_usuario'     => $id_usuario,
        'ids_atividades' => $ids_finais,
        'total'          => count($ids_finais),
    ], 200);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) { /* ignore */ }
    }
    $dados = (function_exists('debug_ativo') && debug_ativo())
        ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()]
        : null;
    responder_json(false, 'Falha ao atualizar canais do usuário.', $dados, 500);
}
