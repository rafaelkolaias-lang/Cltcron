<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/usuarios_estrutura.php';

try {
    $pdo = obter_conexao_pdo();
    usuarios_garantir_chave_pix($pdo);

    // Ordena por status_conta (ativa primeiro, depois inativa/bloqueada),
    // empate por nome_exibicao. FIELD() força a ordem do enum.
    $sql = "SELECT id_usuario, user_id, nome_exibicao, nivel, valor_hora, chave, chave_pix, status_conta, ocultar_dashboard, criado_em, atualizado_em
            FROM usuarios
            ORDER BY FIELD(status_conta, 'ativa', 'inativa', 'bloqueada'), nome_exibicao ASC, user_id ASC";
    $stm = $pdo->prepare($sql);
    $stm->execute();

    $dados = $stm->fetchAll();
    responder_json(true, "OK", $dados);
} catch (Throwable $e) {
    responder_json(false, "falha na conexao", ['erro' => $e->getMessage()], 500);
}
