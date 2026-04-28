<?php
declare(strict_types=1);

/**
 * Remove a condição "global" de um modelo de credencial.
 *
 * Efeito (em uma transação):
 *  - desliga credenciais_modelos.aplicar_novos_usuarios = 0
 *    (novos usuários NÃO herdam mais essa credencial);
 *  - revoga todas as credenciais ativas desse modelo em credenciais_usuario
 *    (status='revogado'). Não apaga: clientes que estiverem com a credencial
 *    cacheada perdem acesso pelo _auth_cliente.php / pela ausência de linhas
 *    'ativo' nos endpoints de consumo, mas o histórico de cifragem/nonce fica.
 *
 * Não é o mesmo que excluir o modelo — `excluir_modelo.php` desativa o modelo
 * inteiro. Aqui o modelo permanece ativo para uso individual.
 */

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

    $stm = $pdo->prepare("SELECT identificador, aplicar_novos_usuarios
                            FROM credenciais_modelos
                           WHERE id_modelo=? LIMIT 1");
    $stm->execute([$id_modelo]);
    $modelo = $stm->fetch();
    if (!$modelo) {
        responder_json(false, 'modelo não encontrado', null, 404);
    }

    $pdo->beginTransaction();
    try {
        $stmt_flag = $pdo->prepare("UPDATE credenciais_modelos
                                       SET aplicar_novos_usuarios=0
                                     WHERE id_modelo=?");
        $stmt_flag->execute([$id_modelo]);

        $stmt_revogar = $pdo->prepare("UPDATE credenciais_usuario
                                          SET status='revogado',
                                              atualizado_em=CURRENT_TIMESTAMP
                                        WHERE id_modelo=? AND status='ativo'");
        $stmt_revogar->execute([$id_modelo]);
        $afetados = $stmt_revogar->rowCount();

        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }

    responder_json(true, "global desativado em {$afetados} usuário(s)", [
        'id_modelo' => $id_modelo,
        'identificador' => $modelo['identificador'],
        'aplicar_novos_usuarios' => 0,
        'credenciais_revogadas' => $afetados,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao remover global', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
