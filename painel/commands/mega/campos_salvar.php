<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

/**
 * POST — cria ou atualiza UM campo de upload.
 * Payload: { id_campo?, user_id, id_atividade, label_campo,
 *            extensoes_permitidas?, quantidade_maxima?, obrigatorio?, ordem?, ativo? }
 */
try {
    $in = ler_json_do_corpo();
    $id_campo     = (int)($in['id_campo'] ?? 0);
    $user_id      = normalizar_user_id((string)($in['user_id'] ?? ''));
    $id_atividade = (int)($in['id_atividade'] ?? 0);
    $label        = trim((string)($in['label_campo'] ?? ''));
    $extensoes    = mega_normalizar_extensoes(isset($in['extensoes_permitidas']) ? (string)$in['extensoes_permitidas'] : null);
    // 0 = ilimitado. >=0 permitido. Sem upper bound — admin que se vire.
    $quantidade   = max(0, (int)($in['quantidade_maxima'] ?? 1));
    $obrigatorio  = !empty($in['obrigatorio']) ? 1 : 0;
    $ordem        = (int)($in['ordem'] ?? 0);
    $ativo        = array_key_exists('ativo', $in) ? (!empty($in['ativo']) ? 1 : 0) : 1;

    if ($user_id === '' || $id_atividade <= 0 || $label === '') {
        responder_json(false, 'user_id, id_atividade e label_campo são obrigatórios', null, 400);
    }
    if (mb_strlen($label) > 120) {
        responder_json(false, 'label_campo acima do limite (120)', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $st = $pdo->prepare("
        SELECT status_conta, COALESCE(ocultar_dashboard, 0) AS ocultar_dashboard
          FROM usuarios
         WHERE user_id = ?
         LIMIT 1
    ");
    $st->execute([$user_id]);
    $usuario = $st->fetch(PDO::FETCH_ASSOC);
    if (!$usuario) {
        responder_json(false, 'usuário não encontrado', null, 404);
    }
    if (strtolower((string)$usuario['status_conta']) !== 'ativa') {
        responder_json(false, 'usuário inativo não pode receber campos de upload', null, 409);
    }
    if ((int)$usuario['ocultar_dashboard'] === 1) {
        responder_json(false, 'usuário oculto não pode receber campos de upload no MEGA', null, 409);
    }

    $st = $pdo->prepare("SELECT status FROM atividades WHERE id_atividade = ? LIMIT 1");
    $st->execute([$id_atividade]);
    $status_atividade = $st->fetchColumn();
    if ($status_atividade === false) {
        responder_json(false, 'atividade não encontrada', null, 404);
    }
    if (strtolower((string)$status_atividade) === 'cancelada') {
        responder_json(false, 'canal cancelado não pode receber campos de upload', null, 409);
    }

    if ($id_campo > 0) {
        $st = $pdo->prepare("
            UPDATE mega_campos_upload
               SET user_id=?, id_atividade=?, label_campo=?, extensoes_permitidas=?,
                   quantidade_maxima=?, obrigatorio=?, ordem=?, ativo=?
             WHERE id_campo=?
        ");
        $st->execute([$user_id, $id_atividade, $label, $extensoes, $quantidade, $obrigatorio, $ordem, $ativo, $id_campo]);
        responder_json(true, 'campo atualizado', ['id_campo' => $id_campo]);
    } else {
        $st = $pdo->prepare("
            INSERT INTO mega_campos_upload
                (user_id, id_atividade, label_campo, extensoes_permitidas,
                 quantidade_maxima, obrigatorio, ordem, ativo)
            VALUES (?,?,?,?,?,?,?,?)
        ");
        $st->execute([$user_id, $id_atividade, $label, $extensoes, $quantidade, $obrigatorio, $ordem, $ativo]);
        responder_json(true, 'campo criado', ['id_campo' => (int)$pdo->lastInsertId()]);
    }
} catch (Throwable $e) {
    responder_json(false, 'falha ao salvar campo de upload', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
