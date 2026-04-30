<?php
declare(strict_types=1);

/**
 * Funções compartilhadas para aplicar/desaplicar vínculos de pagamento
 * em atividades_subtarefas, registros_tempo e pagamento_abatimentos.
 *
 * Todas as funções assumem que já existe uma transação ativa no PDO recebido.
 */

/**
 * Verifica se a tabela pagamento_abatimentos existe (criada pelo desktop em
 * declaracoes_dia.py::_garantir_estrutura). Se ainda não existe, retorna false
 * e o caller pula o tratamento de abatimentos sem derrubar o pagamento.
 */
function pagamento_tabela_abatimentos_existe(PDO $pdo): bool
{
    static $cache = null;
    if ($cache !== null) {
        return $cache;
    }
    try {
        $pdo->query("SELECT 1 FROM pagamento_abatimentos LIMIT 0");
        $cache = true;
    } catch (PDOException $ignore) {
        $cache = false;
    }
    return $cache;
}

/**
 * Apaga todas as linhas de pagamento_abatimentos vinculadas a um pagamento.
 * Retorna a quantidade apagada (ou 0 se a tabela ainda não existe).
 */
function pagamento_apagar_abatimentos_pagamento(PDO $pdo, int $id_pagamento): int
{
    if (!pagamento_tabela_abatimentos_existe($pdo)) {
        return 0;
    }
    $st = $pdo->prepare("DELETE FROM pagamento_abatimentos WHERE id_pagamento = :id_pag");
    $st->execute([':id_pag' => $id_pagamento]);
    return $st->rowCount();
}

/**
 * Apaga todos os abatimentos de um usuário (usado no reprocessamento).
 */
function pagamento_apagar_abatimentos_usuario(PDO $pdo, string $user_id): int
{
    if (!pagamento_tabela_abatimentos_existe($pdo)) {
        return 0;
    }
    $st = $pdo->prepare("DELETE FROM pagamento_abatimentos WHERE user_id = :user_id");
    $st->execute([':user_id' => $user_id]);
    return $st->rowCount();
}

/**
 * Snapshot do saldo pendente por atividade no momento do pagamento.
 * Para cada atividade do usuário com saldo > 0, insere uma linha em
 * pagamento_abatimentos com o pendente = monitorado − declarado − abatido_anterior.
 *
 * Idempotente: a UNIQUE KEY (id_pagamento, user_id, id_atividade) protege
 * contra dupla execução. Diferente de INSERT IGNORE, aqui distinguimos
 * duplicate key (SQLSTATE 23000, ignorado) de outros erros (re-lançados).
 */
function pagamento_registrar_abatimentos(PDO $pdo, int $id_pagamento, string $user_id): int
{
    if (!pagamento_tabela_abatimentos_existe($pdo)) {
        return 0;
    }

    $st = $pdo->prepare("
        SELECT
          r.id_atividade,
          COALESCE(SUM(r.segundos_trabalhando), 0) AS monitorado,
          COALESCE((
            SELECT SUM(s.segundos_gastos)
            FROM atividades_subtarefas s
            WHERE s.user_id = r.user_id
              AND s.id_atividade = r.id_atividade
              AND s.concluida = 1
          ), 0) AS declarado,
          COALESCE((
            SELECT SUM(a.segundos_abatidos)
            FROM pagamento_abatimentos a
            WHERE a.user_id = r.user_id
              AND a.id_atividade = r.id_atividade
          ), 0) AS abatido
        FROM cronometro_relatorios r
        WHERE r.user_id = :user_id
        GROUP BY r.id_atividade
    ");
    $st->execute([':user_id' => $user_id]);

    $stIns = $pdo->prepare("
        INSERT INTO pagamento_abatimentos
            (user_id, id_pagamento, id_atividade, segundos_abatidos)
        VALUES (:user_id, :id_pag, :id_ativ, :segs)
    ");

    $registrados = 0;
    while ($row = $st->fetch(PDO::FETCH_ASSOC)) {
        $monitorado = (int)($row['monitorado'] ?? 0);
        $declarado  = (int)($row['declarado'] ?? 0);
        $abatido    = (int)($row['abatido'] ?? 0);
        $pendente   = max(0, $monitorado - $declarado - $abatido);
        if ($pendente <= 0) {
            continue;
        }
        try {
            $stIns->execute([
                ':user_id' => $user_id,
                ':id_pag'  => $id_pagamento,
                ':id_ativ' => (int)$row['id_atividade'],
                ':segs'    => $pendente,
            ]);
            $registrados++;
        } catch (PDOException $e) {
            // Só engole MySQL errno 1062 (duplicate entry) — re-execução após retry.
            // Qualquer outro erro de integridade (FK 1452, NOT NULL 1048, etc.) sobe.
            $errno = (int)($e->errorInfo[1] ?? 0);
            if ($errno !== 1062) {
                throw $e;
            }
        }
    }
    return $registrados;
}

/**
 * Remove os vínculos de um pagamento específico em subtarefas, registros_tempo
 * e abatimentos. Retorna ['subtarefas' => int, 'registros' => int, 'abatimentos' => int].
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

    // Apagar abatimentos do pagamento (libera saldo da atividade)
    $abatimentos = pagamento_apagar_abatimentos_pagamento($pdo, $id_pagamento);

    return [
        'subtarefas'  => $subtarefas,
        'registros'   => $registros,
        'abatimentos' => $abatimentos,
    ];
}

/**
 * Aplica os vínculos de um pagamento: trava subtarefas, marca registros_tempo
 * e (opcional) registra abatimento do saldo pendente.
 *
 * @param bool $registrar_historico    se true, insere em atividades_subtarefas_historico
 * @param bool $registrar_abatimento   se true, faz snapshot em pagamento_abatimentos
 */
function pagamento_aplicar(
    PDO $pdo,
    int $id_pagamento,
    string $user_id,
    string $travado_ate_data,
    ?string $referencia_inicio,
    ?string $referencia_fim,
    bool $registrar_historico = true,
    bool $registrar_abatimento = true
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

    // --- Registrar snapshot de abatimento (saldo pendente por atividade) ---
    $abatimentos = 0;
    if ($registrar_abatimento) {
        $abatimentos = pagamento_registrar_abatimentos($pdo, $id_pagamento, $user_id);
    }

    return [
        'subtarefas'  => $travadas,
        'registros'   => $registros,
        'abatimentos' => $abatimentos,
    ];
}

/**
 * Reprocessa TODOS os pagamentos de um usuário em ordem cronológica.
 * Usado após excluir ou editar um pagamento para garantir consistência
 * dos BLOQUEIOS de subtarefas e registros_tempo.
 *
 * Abatimentos são IMUTÁVEIS: criados uma vez no pagamento_aplicar() e
 * apagados só quando o pagamento é excluído (via pagamento_desvincular()).
 * Reprocessamento NÃO mexe em abatimentos — preserva o snapshot histórico
 * gravado no momento de cada pagamento.
 */
function pagamento_reprocessar_todos(PDO $pdo, int $id_usuario, string $user_id): void
{
    // Limpar todos os vínculos de bloqueio do usuário
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

    // Reaplicar cada pagamento em ordem cronológica — só bloqueios, sem mexer em abatimentos
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
            false, // sem histórico no reprocessamento
            false  // SEM tocar em abatimentos (snapshot original imutável)
        );
    }
}
