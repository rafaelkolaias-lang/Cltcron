<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $in = ler_json_do_corpo();
    $user_id   = normalizar_user_id((string)($in['user_id'] ?? ''));
    $id_modelo = (int)($in['id_modelo'] ?? 0);
    $apagar    = !empty($in['apagar']);

    if ($user_id === '' || $id_modelo <= 0) {
        responder_json(false, 'user_id e id_modelo obrigatórios', null, 400);
    }

    $pdo = obter_conexao_pdo();

    if ($apagar) {
        $stm = $pdo->prepare("DELETE FROM credenciais_usuario WHERE user_id=? AND id_modelo=?");
        $stm->execute([$user_id, $id_modelo]);
        responder_json(true, 'credencial removida', ['estado' => 'vazia', 'afetados' => $stm->rowCount()]);
    } else {
        $stm = $pdo->prepare("UPDATE credenciais_usuario
                                 SET status='revogado', atualizado_em=CURRENT_TIMESTAMP
                               WHERE user_id=? AND id_modelo=?");
        $stm->execute([$user_id, $id_modelo]);
        responder_json(true, 'credencial revogada', ['estado' => 'revogada', 'afetados' => $stm->rowCount()]);
    }
} catch (Throwable $e) {
    responder_json(false, 'falha ao revogar', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
