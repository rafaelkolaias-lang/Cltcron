<?php
// commands/atividades_subtarefas/editar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/declaracoes_dia_itens.php';

try {
    $in = ler_json_do_corpo();

    $id_subtarefa = (int)($in['id_subtarefa'] ?? 0);
    $titulo       = trim((string)($in['titulo']       ?? ''));
    $canal        = isset($in['canal_entrega']) ? trim((string)$in['canal_entrega']) : null;
    $observacao   = isset($in['observacao'])   ? trim((string)$in['observacao'])   : null;
    $concluida    = isset($in['concluida'])    ? (bool)$in['concluida']            : null;
    $segundos     = isset($in['segundos_gastos']) ? (int)$in['segundos_gastos']    : null;

    if ($id_subtarefa <= 0) {
        responder_json(false, 'id_subtarefa inválido.', null, 400);
    }
    if ($titulo === '' || mb_strlen($titulo) < 2) {
        responder_json(false, 'Título inválido (mínimo 2 caracteres).', null, 400);
    }
    if ($segundos !== null && $segundos < 0) {
        responder_json(false, 'segundos_gastos não pode ser negativo.', null, 400);
    }

    $pdo = obter_conexao_pdo();

    // Verifica existência e trava de pagamento
    $stV = $pdo->prepare("
        SELECT id_subtarefa, bloqueada_pagamento, titulo, canal_entrega,
               concluida, segundos_gastos, observacao, user_id, id_atividade
        FROM atividades_subtarefas
        WHERE id_subtarefa = :id
        LIMIT 1
    ");
    $stV->execute([':id' => $id_subtarefa]);
    $atual = $stV->fetch(PDO::FETCH_ASSOC);

    if (!$atual) {
        responder_json(false, 'Tarefa não encontrada.', null, 404);
    }
    if ((int)($atual['bloqueada_pagamento'] ?? 0) === 1) {
        responder_json(false, 'Esta tarefa está bloqueada por pagamento e não pode ser editada.', null, 403);
    }

    // Bloqueio de renomeação para tarefas MEGA: o título de uma tarefa MEGA
    // está acoplado ao `mega_pasta_logica.nome_pasta` e ao nome da pasta no
    // servidor MEGA. Alterar só o título pelo painel deixa banco e MEGA
    // divergentes — quebra reabertura, troca de arquivo, exclusão e a
    // sincronização periódica. Enquanto o fluxo de renomeação coerente
    // (com replicação para o MEGA) não estiver implementado, recusamos a
    // alteração explicitamente. Outros campos (tempo, observação, canal,
    // status de conclusão) continuam editáveis.
    $titulo_atual = (string)($atual['titulo'] ?? '');
    if ($titulo !== '' && $titulo !== $titulo_atual) {
        try {
            $stMega = $pdo->prepare(
                'SELECT 1
                   FROM mega_pasta_logica
                  WHERE id_atividade = :id_ativ
                    AND nome_pasta   = :nome
                    AND ativo = 1
                  LIMIT 1'
            );
            $stMega->execute([
                ':id_ativ' => (int)($atual['id_atividade'] ?? 0),
                ':nome'    => $titulo_atual,
            ]);
            if ($stMega->fetchColumn()) {
                responder_json(false,
                    'Esta tarefa está vinculada a uma pasta no MEGA — alterar o nome pelo painel deixaria os arquivos do MEGA dessincronizados. Edite tempo, observação ou status normalmente; para renomear, exclua e recrie pelo app desktop.',
                    ['id_subtarefa' => $id_subtarefa, 'campo' => 'titulo'],
                    409
                );
            }
        } catch (Throwable $_) {
            // Tabela `mega_pasta_logica` pode não existir em ambientes sem
            // o módulo MEGA configurado. Sem ela, nada a bloquear.
        }
    }

    // Monta SET dinâmico apenas com campos enviados
    $sets   = ['titulo = :titulo'];
    $params = [':titulo' => $titulo, ':id' => $id_subtarefa];

    if ($canal !== null) {
        $sets[] = 'canal_entrega = :canal';
        $params[':canal'] = $canal !== '' ? $canal : null;
    }
    if ($observacao !== null) {
        $sets[] = 'observacao = :observacao';
        $params[':observacao'] = $observacao !== '' ? $observacao : null;
    }
    if ($concluida !== null) {
        $sets[] = 'concluida = :concluida';
        $sets[] = 'concluida_em = :concluida_em';
        $params[':concluida']    = $concluida ? 1 : 0;
        $params[':concluida_em'] = $concluida ? date('Y-m-d H:i:s') : null;
    }
    if ($segundos !== null) {
        // Validar: total declarado ACUMULADO (excluindo esta tarefa) + novo valor não pode exceder total trabalhado
        // Fonte primária: cronometro_relatorios.segundos_trabalhando filtrado por referencia_data (trabalho líquido real)
        $stTrab = $pdo->prepare("
            SELECT COALESCE(SUM(segundos_trabalhando), 0)
            FROM cronometro_relatorios
            WHERE user_id = :uid AND referencia_data IS NOT NULL
        ");
        $stTrab->execute([':uid' => $atual['user_id']]);
        $trabalhado_total = (int)$stTrab->fetchColumn();

        // Fallback para bases antigas que ainda não tenham registros em cronometro_relatorios
        if ($trabalhado_total === 0) {
            try {
                $stTrab = $pdo->prepare("
                    SELECT COALESCE(SUM(segundos), 0)
                    FROM registros_tempo
                    WHERE user_id = :uid AND situacao = 'trabalhando' AND id_pagamento IS NULL
                ");
                $stTrab->execute([':uid' => $atual['user_id']]);
                $trabalhado_total = (int)$stTrab->fetchColumn();
            } catch (Throwable $_) {
                $trabalhado_total = 0;
            }
        }

        $stDecl = $pdo->prepare("
            SELECT COALESCE(SUM(segundos_gastos), 0)
            FROM atividades_subtarefas
            WHERE user_id = :uid AND id_subtarefa != :id_excluir
        ");
        $stDecl->execute([':uid' => $atual['user_id'], ':id_excluir' => $id_subtarefa]);
        $declarado_outros = (int)$stDecl->fetchColumn();

        if ($trabalhado_total > 0 && ($declarado_outros + $segundos) > $trabalhado_total) {
            $disponivel = max(0, $trabalhado_total - $declarado_outros);
            $disp_h = intdiv($disponivel, 3600);
            $disp_m = intdiv($disponivel % 3600, 60);
            responder_json(false, "Tempo excede o total trabalhado. Disponível: {$disp_h}h {$disp_m}m.", [
                'segundos_trabalhados_total' => $trabalhado_total,
                'segundos_declarados_outros' => $declarado_outros,
                'segundos_disponiveis' => $disponivel,
            ], 422);
        }

        $sets[] = 'segundos_gastos = :segundos';
        $params[':segundos'] = $segundos;
    }

    $pdo->beginTransaction();

    // Snapshot antes
    $dados_antes = [
        'titulo'         => $atual['titulo'],
        'canal_entrega'  => $atual['canal_entrega'],
        'concluida'      => (bool)$atual['concluida'],
        'segundos_gastos' => (int)$atual['segundos_gastos'],
        'observacao'     => $atual['observacao'],
    ];

    $sql = 'UPDATE atividades_subtarefas SET ' . implode(', ', $sets) . ' WHERE id_subtarefa = :id';
    $stU = $pdo->prepare($sql);
    $stU->execute($params);

    // Snapshot depois
    $stD = $pdo->prepare("
        SELECT titulo, canal_entrega, concluida, segundos_gastos, observacao
        FROM atividades_subtarefas WHERE id_subtarefa = :id LIMIT 1
    ");
    $stD->execute([':id' => $id_subtarefa]);
    $depois = $stD->fetch(PDO::FETCH_ASSOC);

    $dados_depois = [
        'titulo'          => $depois['titulo'],
        'canal_entrega'   => $depois['canal_entrega'],
        'concluida'       => (bool)$depois['concluida'],
        'segundos_gastos' => (int)$depois['segundos_gastos'],
        'observacao'      => $depois['observacao'],
    ];

    // Registra histórico — user_id_executor usa o user_id do dono da tarefa
    // (painel admin edita em nome do alvo; evita FK violation com ID inexistente)
    $stH = $pdo->prepare("
        INSERT INTO atividades_subtarefas_historico
            (id_subtarefa, acao, user_id_alvo, user_id_executor, dados_antes, dados_depois)
        VALUES
            (:id_sub, 'edicao', :user_alvo, :user_exec, :antes, :depois)
    ");
    $stH->execute([
        ':id_sub'     => $id_subtarefa,
        ':user_alvo'  => (string)($atual['user_id'] ?? ''),
        ':user_exec'  => (string)($atual['user_id'] ?? ''),
        ':antes'      => json_encode($dados_antes, JSON_UNESCAPED_UNICODE),
        ':depois'     => json_encode($dados_depois, JSON_UNESCAPED_UNICODE),
    ]);

    // Espelha em `declaracoes_dia_itens` (fonte do relatório de tempo
    // trabalhado). Sem isso, edições feitas pela Gestão divergem do
    // relatório — o desktop já mantém esse espelho via
    // `declaracoes_dia.py::_sincronizar_item_espelho_da_subtarefa`.
    declaracoes_itens_sincronizar_espelho($pdo, $id_subtarefa);

    $pdo->commit();

    responder_json(true, 'Tarefa atualizada com sucesso.', ['id_subtarefa' => $id_subtarefa], 200);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        try { $pdo->rollBack(); } catch (Throwable $t) {}
    }
    $dados = debug_ativo() ? ['erro' => $e->getMessage(), 'linha' => $e->getLine()] : null;
    responder_json(false, 'Falha ao editar tarefa.', $dados, 500);
}
