<?php
declare(strict_types=1);

/**
 * Funções compartilhadas para aplicar/desaplicar vínculos de pagamento
 * em atividades_subtarefas e registros_tempo.
 *
 * Todas as funções assumem que já existe uma transação ativa no PDO recebido.
 */

/**
 * Remove os vínculos de um pagamento específico em subtarefas e registros_tempo.
 * Retorna ['subtarefas' => int, 'registros' => int] com as quantidades limpas.
 */
function pagamento_desvincular(PDO $pdo, int $id_pagamento): array
{
    // Destravar subtarefas
    $st = $pdo->prepare("
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 0,
            id_pagamento = NULL,
            bloqueada_em = NULL
        WHERE id_pagamento = :id_pag
    ");
    $st->execute([':id_pag' => $id_pagamento]);
    $subtarefas = $st->rowCount();

    // Limpar registros_tempo
    $registros = 0;
    try {
        $st2 = $pdo->prepare("
            UPDATE registros_tempo
            SET id_pagamento = NULL
            WHERE id_pagamento = :id_pag
        ");
        $st2->execute([':id_pag' => $id_pagamento]);
        $registros = $st2->rowCount();
    } catch (Throwable $ignore) {
        // Coluna id_pagamento pode não existir em bancos antigos
    }

    return ['subtarefas' => $subtarefas, 'registros' => $registros];
}

/**
 * Aplica os vínculos de um pagamento: trava subtarefas e marca registros_tempo
 * dentro do período correto (referencia_data entre início e fim do pagamento).
 *
 * @param PDO    $pdo
 * @param int    $id_pagamento
 * @param string $user_id           user_id textual (ex: 'richard')
 * @param string $travado_ate_data  data limite (YYYY-MM-DD)
 * @param string|null $referencia_inicio  início do período (YYYY-MM-DD), null = sem limite inferior
 * @param string|null $referencia_fim     fim do período (YYYY-MM-DD), null = usa travado_ate_data
 * @param bool   $registrar_historico  se true, insere em atividades_subtarefas_historico
 * @return array ['subtarefas' => int, 'registros' => int]
 */
function pagamento_aplicar(
    PDO $pdo,
    int $id_pagamento,
    string $user_id,
    string $travado_ate_data,
    ?string $referencia_inicio,
    ?string $referencia_fim,
    bool $registrar_historico = true
): array {
    // Determinar limites efetivos
    $limite_fim = $referencia_fim ?: $travado_ate_data;

    // --- Travar subtarefas no período ---
    $sql_sub = "
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 1,
            id_pagamento = :id_pag,
            bloqueada_em = NOW()
        WHERE user_id = :user_id
          AND referencia_data IS NOT NULL
          AND referencia_data <= :limite_fim
          AND bloqueada_pagamento = 0
    ";
    $params_sub = [
        ':id_pag'     => $id_pagamento,
        ':user_id'    => $user_id,
        ':limite_fim' => $limite_fim,
    ];

    if ($referencia_inicio !== null) {
        $sql_sub = str_replace(
            'AND bloqueada_pagamento = 0',
            'AND referencia_data >= :limite_inicio AND bloqueada_pagamento = 0',
            $sql_sub
        );
        $params_sub[':limite_inicio'] = $referencia_inicio;
    }

    $st = $pdo->prepare($sql_sub);
    $st->execute($params_sub);
    $travadas = $st->rowCount();

    // --- Registrar histórico ---
    if ($registrar_historico && $travadas > 0) {
        $stIds = $pdo->prepare("
            SELECT id_subtarefa, user_id
            FROM atividades_subtarefas
            WHERE id_pagamento = :id_pag
        ");
        $stIds->execute([':id_pag' => $id_pagamento]);
        $subtsTravadas = $stIds->fetchAll(PDO::FETCH_ASSOC);

        $stH = $pdo->prepare("
            INSERT INTO atividades_subtarefas_historico
                (id_subtarefa, acao, user_id_alvo, user_id_executor, dados_antes, dados_depois)
            VALUES
                (:id_sub, 'bloqueio_pagamento', :user_alvo, :user_exec, :antes, :depois)
        ");
        foreach ($subtsTravadas as $sub) {
            $stH->execute([
                ':id_sub'     => $sub['id_subtarefa'],
                ':user_alvo'  => $sub['user_id'],
                ':user_exec'  => $sub['user_id'],
                ':antes'      => json_encode(['bloqueada_pagamento' => false]),
                ':depois'     => json_encode(['bloqueada_pagamento' => true, 'id_pagamento' => $id_pagamento]),
            ]);
        }
    }

    // --- Marcar registros_tempo no período por referencia_data ---
    $registros = 0;
    try {
        $sql_reg = "
            UPDATE registros_tempo
            SET id_pagamento = :id_pag
            WHERE user_id = :user_id
              AND referencia_data <= :limite_fim
              AND id_pagamento IS NULL
        ";
        $params_reg = [
            ':id_pag'     => $id_pagamento,
            ':user_id'    => $user_id,
            ':limite_fim' => $limite_fim,
        ];

        if ($referencia_inicio !== null) {
            $sql_reg = str_replace(
                'AND id_pagamento IS NULL',
                'AND referencia_data >= :limite_inicio AND id_pagamento IS NULL',
                $sql_reg
            );
            $params_reg[':limite_inicio'] = $referencia_inicio;
        }

        $st2 = $pdo->prepare($sql_reg);
        $st2->execute($params_reg);
        $registros = $st2->rowCount();
    } catch (Throwable $ignore) {
        // Coluna id_pagamento pode não existir em bancos antigos
    }

    return ['subtarefas' => $travadas, 'registros' => $registros];
}

/**
 * Reprocessa TODOS os pagamentos de um usuário em ordem cronológica.
 * Usado após excluir ou editar um pagamento para garantir consistência.
 *
 * @param PDO    $pdo
 * @param int    $id_usuario  ID numérico do usuário (tabela Pagamentos)
 * @param string $user_id     user_id textual (tabela atividades_subtarefas / registros_tempo)
 */
function pagamento_reprocessar_todos(PDO $pdo, int $id_usuario, string $user_id): void
{
    // Limpar todos os vínculos de pagamento do usuário
    $pdo->prepare("
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 0,
            id_pagamento = NULL,
            bloqueada_em = NULL
        WHERE user_id = :user_id
          AND bloqueada_pagamento = 1
    ")->execute([':user_id' => $user_id]);

    try {
        $pdo->prepare("
            UPDATE registros_tempo
            SET id_pagamento = NULL
            WHERE user_id = :user_id
              AND id_pagamento IS NOT NULL
        ")->execute([':user_id' => $user_id]);
    } catch (Throwable $ignore) {}

    // Reaplicar cada pagamento em ordem cronológica
    $st = $pdo->prepare("
        SELECT id_pagamento, referencia_inicio, referencia_fim, travado_ate_data
        FROM Pagamentos
        WHERE id_usuario = :id_usuario
        ORDER BY data_pagamento ASC, id_pagamento ASC
    ");
    $st->execute([':id_usuario' => $id_usuario]);
    $pagamentos = $st->fetchAll(PDO::FETCH_ASSOC);

    foreach ($pagamentos as $pag) {
        pagamento_aplicar(
            $pdo,
            (int)$pag['id_pagamento'],
            $user_id,
            $pag['travado_ate_data'] ?? '',
            $pag['referencia_inicio'],
            $pag['referencia_fim'],
            false // sem histórico no reprocessamento
        );
    }
}
