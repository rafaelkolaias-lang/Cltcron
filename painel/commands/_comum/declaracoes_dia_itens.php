<?php
// commands/_comum/declaracoes_dia_itens.php
//
// Espelhamento da tabela `atividades_subtarefas` em `declaracoes_dia_itens`,
// usada pelo relatório de tempo trabalhado. Replica a regra do desktop
// (`declaracoes_dia.py::_sincronizar_item_espelho_da_subtarefa`) para que
// edições feitas pelo painel mantenham gestão e relatório coerentes.
declare(strict_types=1);

/**
 * Garante que a linha-espelho em `declaracoes_dia_itens` reflita o estado
 * atual da subtarefa em `atividades_subtarefas`.
 *
 * Regra (mesma do desktop):
 * - Se a subtarefa não existe / não está concluída / não tem referencia_data,
 *   o espelho é APAGADO.
 * - Caso contrário, UPSERT pelo `id_subtarefa`, copiando
 *   `user_id`, `referencia_data`, `id_atividade`, `segundos_gastos` (em
 *   `segundos_declarados`), `titulo` (em `o_que_fez`), `canal_entrega` e
 *   `observacao`.
 *
 * Não abre transação própria — caller é responsável (chamar dentro da
 * transação principal). Falhas propagam.
 */
function declaracoes_itens_sincronizar_espelho(PDO $pdo, int $id_subtarefa): void
{
    if ($id_subtarefa <= 0) {
        return;
    }

    $st = $pdo->prepare(
        "SELECT user_id, referencia_data, id_atividade, concluida,
                segundos_gastos, titulo, canal_entrega, observacao
           FROM atividades_subtarefas
          WHERE id_subtarefa = :id
          LIMIT 1"
    );
    $st->execute([':id' => $id_subtarefa]);
    $sub = $st->fetch(PDO::FETCH_ASSOC);

    if (!$sub) {
        $stDel = $pdo->prepare(
            'DELETE FROM declaracoes_dia_itens WHERE id_subtarefa = :id'
        );
        $stDel->execute([':id' => $id_subtarefa]);
        return;
    }

    $concluida   = (int)($sub['concluida'] ?? 0) === 1;
    $referencia  = $sub['referencia_data'] ?: null; // string Y-m-d ou null
    $user_id     = trim((string)($sub['user_id'] ?? ''));

    if (!$concluida || $referencia === null || $user_id === '') {
        $stDel = $pdo->prepare(
            'DELETE FROM declaracoes_dia_itens WHERE id_subtarefa = :id'
        );
        $stDel->execute([':id' => $id_subtarefa]);
        return;
    }

    // Normalizações mínimas (espelhar tamanhos máximos da tabela). Se a coluna
    // for menor, o MySQL trunca silenciosamente — limitar aqui evita surpresas
    // com `STRICT_TRANS_TABLES`.
    $titulo     = mb_substr((string)($sub['titulo'] ?? ''), 0, 255);
    $canal_raw  = trim((string)($sub['canal_entrega'] ?? ''));
    $canal      = $canal_raw !== '' ? mb_substr($canal_raw, 0, 180) : null;
    $obs_raw    = trim((string)($sub['observacao'] ?? ''));
    $observacao = $obs_raw !== '' ? mb_substr($obs_raw, 0, 600) : null;
    $segundos   = (int)($sub['segundos_gastos'] ?? 0);
    $id_ativ    = (int)($sub['id_atividade'] ?? 0);

    $stEx = $pdo->prepare(
        'SELECT id_item FROM declaracoes_dia_itens WHERE id_subtarefa = :id LIMIT 1'
    );
    $stEx->execute([':id' => $id_subtarefa]);
    $existente = $stEx->fetchColumn();

    if ($existente !== false && $existente !== null) {
        $stUp = $pdo->prepare(
            'UPDATE declaracoes_dia_itens
                SET user_id = :uid,
                    referencia_data = :ref,
                    id_atividade = :ativ,
                    id_subtarefa = :id_sub,
                    segundos_declarados = :seg,
                    o_que_fez = :titulo,
                    canal_entrega = :canal,
                    observacao = :obs
              WHERE id_item = :id_item'
        );
        $stUp->execute([
            ':uid'     => $user_id,
            ':ref'     => $referencia,
            ':ativ'    => $id_ativ,
            ':id_sub'  => $id_subtarefa,
            ':seg'     => $segundos,
            ':titulo'  => $titulo,
            ':canal'   => $canal,
            ':obs'     => $observacao,
            ':id_item' => (int)$existente,
        ]);
        return;
    }

    $stIn = $pdo->prepare(
        'INSERT INTO declaracoes_dia_itens (
            user_id, referencia_data, id_atividade, id_subtarefa,
            segundos_declarados, o_que_fez, canal_entrega, observacao
         ) VALUES (
            :uid, :ref, :ativ, :id_sub,
            :seg, :titulo, :canal, :obs
         )'
    );
    $stIn->execute([
        ':uid'    => $user_id,
        ':ref'    => $referencia,
        ':ativ'   => $id_ativ,
        ':id_sub' => $id_subtarefa,
        ':seg'    => $segundos,
        ':titulo' => $titulo,
        ':canal'  => $canal,
        ':obs'    => $observacao,
    ]);
}
