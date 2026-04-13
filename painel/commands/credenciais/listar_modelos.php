<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();
    $sql = "SELECT id_modelo, identificador, nome_exibicao, categoria, descricao,
                   ordem_exibicao, status, criado_em, atualizado_em
            FROM credenciais_modelos
            WHERE status = 'ativo'
            ORDER BY ordem_exibicao ASC, nome_exibicao ASC";
    $stm = $pdo->prepare($sql);
    $stm->execute();
    responder_json(true, 'OK', $stm->fetchAll());
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar modelos', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
