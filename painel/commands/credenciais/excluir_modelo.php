<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $in = ler_json_do_corpo();
    $id_modelo = (int)($in['id_modelo'] ?? 0);
    if ($id_modelo <= 0) {
        responder_json(false, 'id_modelo obrigatório', null, 400);
    }
    $pdo = obter_conexao_pdo();

    // Modelos padrão do sistema não podem ser excluídos (protegidos).
    $protegidos = ['chatgpt', 'gemini', 'minimax', 'elevenlabs', 'assembly'];
    $stm = $pdo->prepare("SELECT identificador FROM credenciais_modelos WHERE id_modelo=?");
    $stm->execute([$id_modelo]);
    $ident = (string)($stm->fetchColumn() ?: '');
    if ($ident !== '' && in_array($ident, $protegidos, true)) {
        responder_json(false, 'modelo padrão do sistema — exclusão não permitida', null, 403);
    }

    // ON DELETE CASCADE derruba credenciais_usuario associadas (decisão de schema).
    $stm = $pdo->prepare("DELETE FROM credenciais_modelos WHERE id_modelo=?");
    $stm->execute([$id_modelo]);
    responder_json(true, 'modelo excluído', ['afetados' => $stm->rowCount()]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao excluir modelo', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
