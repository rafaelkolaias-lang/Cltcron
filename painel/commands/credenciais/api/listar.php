<?php
declare(strict_types=1);

/**
 * listar.php — lista os identificadores de credenciais que o usuário autenticado
 * tem cadastradas (sem valor, sem máscara). Útil para o app saber antes de pedir.
 *
 * Entrada:
 *   GET (auth via header)
 *
 * Resposta:
 *   { ok, mensagem, dados: [ { identificador, nome_exibicao, categoria, status } ] }
 *
 * Mostra apenas as preenchidas + ativas. Revogadas e vazias são omitidas.
 */

require_once __DIR__ . '/../../_comum/resposta.php';
require_once __DIR__ . '/../../conexao/conexao.php';
require_once __DIR__ . '/_auth_cliente.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $pdo = obter_conexao_pdo();

    $sql = "SELECT m.identificador, m.nome_exibicao, m.categoria, c.status
              FROM credenciais_usuario c
              JOIN credenciais_modelos m ON m.id_modelo = c.id_modelo
             WHERE c.user_id = ? AND c.status = 'ativo' AND m.status = 'ativo'
          ORDER BY m.ordem_exibicao ASC, m.nome_exibicao ASC";
    $stm = $pdo->prepare($sql);
    $stm->execute([$u['user_id']]);
    responder_json(true, 'OK', $stm->fetchAll());
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
