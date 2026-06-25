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
 * Snapshot GLOBAL do saldo pendente no momento do pagamento.
 * Calcula: monitorado_total − declarado_total − abatido_anterior e grava
 * UMA ÚNICA linha em pagamento_abatimentos (id_atividade = NULL).
 *
 * O cronômetro é neutro — conta horas do usuário sem vínculo com canal.
 * Só na declaração de subtarefa o usuário direciona horas para um canal.
 *
 * Janela temporal: monitorado é somado até o instante da última declaração
 * do usuário (qualquer atividade). Trabalho cronometrado após esse instante
 * fica como saldo disponível para o próximo ciclo.
 */
function pagamento_registrar_abatimentos(PDO $pdo, int $id_pagamento, string $user_id): int
{
    if (!pagamento_tabela_abatimentos_existe($pdo)) {
        return 0;
    }

    // Corte temporal do ciclo pago: o pagamento cobre trabalho até o FIM DO DIA
    // do período coberto (travado_ate_data) — e nunca além do MOMENTO em que o
    // pagamento foi registrado (não dá pra pagar trabalho feito depois do clique).
    // Corte = MENOR(criado_em do pagamento, fim do dia do travado_ate_data).
    //
    // ANTES o corte era MAX(concluida_em) de QUALQUER data. Isso abatia horas
    // cronometradas DEPOIS do período pago quando o usuário declarava mais tarde
    // (bug: pagamento do dia 23 registrado dia 25 abatia o trabalho do dia 24/25,
    // que é do ciclo novo). Agora o trabalho após o período/clique fica disponível.
    $stPag = $pdo->prepare("
        SELECT criado_em, travado_ate_data
        FROM Pagamentos WHERE id_pagamento = :id LIMIT 1
    ");
    $stPag->execute([':id' => $id_pagamento]);
    $pag = $stPag->fetch(PDO::FETCH_ASSOC) ?: [];
    $candidatos = [];
    if (!empty($pag['criado_em']))       { $candidatos[] = (string)$pag['criado_em']; }
    if (!empty($pag['travado_ate_data'])) { $candidatos[] = ((string)$pag['travado_ate_data']) . ' 23:59:59'; }
    // Strings 'Y-m-d H:i:s' comparam cronologicamente, então min() = o mais cedo.
    $corte = $candidatos ? min($candidatos) : date('Y-m-d H:i:s');

    // Monitorado global (cronômetro neutro — ignora id_atividade)
    $stMon = $pdo->prepare("
        SELECT COALESCE(SUM(segundos_trabalhando), 0)
        FROM cronometro_relatorios
        WHERE user_id = :uid AND criado_em <= :corte
    ");
    $stMon->execute([':uid' => $user_id, ':corte' => $corte]);
    $monitorado = (int)$stMon->fetchColumn();

    // Declarado global (subtarefas concluídas do ciclo atual — ignora já pagas)
    $stDecl = $pdo->prepare("
        SELECT COALESCE(SUM(segundos_gastos), 0)
        FROM atividades_subtarefas
        WHERE user_id = :uid AND concluida = 1 AND bloqueada_pagamento = 0
    ");
    $stDecl->execute([':uid' => $user_id]);
    $declarado = (int)$stDecl->fetchColumn();

    // Já abatido em pagamentos anteriores
    $stAbat = $pdo->prepare("
        SELECT COALESCE(SUM(segundos_abatidos), 0)
        FROM pagamento_abatimentos
        WHERE user_id = :uid
    ");
    $stAbat->execute([':uid' => $user_id]);
    $abatido = (int)$stAbat->fetchColumn();

    $pendente = max(0, $monitorado - $declarado - $abatido);
    if ($pendente <= 0) {
        return 0;
    }

    try {
        $stIns = $pdo->prepare("
            INSERT INTO pagamento_abatimentos
                (user_id, id_pagamento, id_atividade, segundos_abatidos)
            VALUES (:user_id, :id_pag, NULL, :segs)
        ");
        $stIns->execute([
            ':user_id' => $user_id,
            ':id_pag'  => $id_pagamento,
            ':segs'    => $pendente,
        ]);
        return 1;
    } catch (PDOException $e) {
        $errno = (int)($e->errorInfo[1] ?? 0);
        if ($errno !== 1062) {
            throw $e;
        }
        return 0;
    }
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

    // Carrega o `criado_em` real do pagamento (DATETIME) para distinguir, no
    // dia exato do `limite_fim`, subtarefas que já existiam quando o pagamento
    // foi registrado das que foram criadas depois. Tarefas criadas após o
    // pagamento, mesmo no mesmo dia, NÃO devem ser travadas — alinha com a
    // regra do desktop em
    // `declaracoes_dia.py::atualizar_bloqueios_por_pagamento`.
    $stCri = $pdo->prepare(
        'SELECT criado_em FROM Pagamentos WHERE id_pagamento = :id LIMIT 1'
    );
    $stCri->execute([':id' => $id_pagamento]);
    $criado_em_pag = $stCri->fetchColumn();
    if (!$criado_em_pag) {
        // Fallback defensivo: trata como agora (recém-inserido). Mantém o
        // comportamento operacional até o caller usar a versão nova.
        $criado_em_pag = date('Y-m-d H:i:s');
    }

    // --- Travar subtarefas no período ---
    //
    // Dois UPDATEs em vez de um único `referencia_data <= :limite_fim`:
    //   (a) dias estritamente anteriores ao `limite_fim`: trava tudo;
    //   (b) dia exato do `limite_fim`: trava apenas o que já existia no
    //       instante do pagamento (`criada_em <= criado_em_pag`).
    //
    // Antes a query travava o dia inteiro do `limite_fim`, incluindo
    // tarefas criadas depois do pagamento — o que fazia o reprocessamento
    // bloquear trabalho ainda válido.

    $sql_sub_anteriores = "
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 1,
            id_pagamento = :id_pag,
            bloqueada_em = NOW()
        WHERE user_id = :user_id
          AND referencia_data IS NOT NULL
          AND referencia_data < :limite_fim
          AND bloqueada_pagamento = 0
    ";
    $params_sub_anteriores = [
        ':id_pag'     => $id_pagamento,
        ':user_id'    => $user_id,
        ':limite_fim' => $limite_fim,
    ];
    if ($referencia_inicio !== null) {
        $sql_sub_anteriores = str_replace(
            'AND bloqueada_pagamento = 0',
            'AND referencia_data >= :limite_inicio AND bloqueada_pagamento = 0',
            $sql_sub_anteriores
        );
        $params_sub_anteriores[':limite_inicio'] = $referencia_inicio;
    }
    $st = $pdo->prepare($sql_sub_anteriores);
    $st->execute($params_sub_anteriores);
    $travadas = $st->rowCount();

    // Dia exato do `limite_fim`: corte por `criada_em` vs `criado_em` do
    // pagamento. Inclui a tarefa só se já tinha sido criada quando o
    // pagamento foi registrado.
    $sql_sub_dia_exato = "
        UPDATE atividades_subtarefas
        SET bloqueada_pagamento = 1,
            id_pagamento = :id_pag,
            bloqueada_em = NOW()
        WHERE user_id = :user_id
          AND referencia_data = :limite_fim
          AND criada_em <= :criado_em_pag
          AND bloqueada_pagamento = 0
    ";
    $params_sub_dia_exato = [
        ':id_pag'        => $id_pagamento,
        ':user_id'       => $user_id,
        ':limite_fim'    => $limite_fim,
        ':criado_em_pag' => $criado_em_pag,
    ];
    if ($referencia_inicio !== null && $referencia_inicio > $limite_fim) {
        // Caso degenerado: período inicia depois do limite. Pular dia exato.
    } else {
        $st = $pdo->prepare($sql_sub_dia_exato);
        $st->execute($params_sub_dia_exato);
        $travadas += $st->rowCount();
    }

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

    // --- Registrar snapshot de abatimento (saldo pendente global) ---
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
