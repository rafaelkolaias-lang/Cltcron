<?php
declare(strict_types=1);

/**
 * desktop_obter_config.php — endpoint consumido pelo app desktop.
 *
 * Auth: user_id + chave (mesmo padrão de credenciais/api/_auth_cliente.php).
 *
 * GET ?id_atividade=Y → retorna:
 *   {
 *     upload_ativo: bool,
 *     pasta_raiz_mega: string,
 *     campos_exigidos: [ {label_campo, extensoes_permitidas, quantidade_maxima, obrigatorio, ordem} ],
 *     pastas_logicas: [ {id_pasta_logica, nome_pasta, numero_video, titulo_video} ]
 *   }
 *
 * Se a atividade não tiver config, devolve upload_ativo=false e arrays vazios
 * (comportamento legado preservado — desktop cai no fluxo antigo).
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $id_atividade = isset($_GET['id_atividade']) ? (int)$_GET['id_atividade'] : 0;
    if ($id_atividade <= 0) {
        responder_json(false, 'id_atividade obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Defesa contra IDOR: o user precisa estar atribuído a essa atividade.
    if (!mega_user_pertence_atividade($pdo, $user_id, $id_atividade)) {
        responder_json(false, 'usuário não tem acesso a esta atividade', null, 403);
    }

    // Config do canal
    $st = $pdo->prepare("SELECT nome_pasta_mega, upload_ativo
                           FROM mega_canal_config
                          WHERE id_atividade=? LIMIT 1");
    $st->execute([$id_atividade]);
    $cfg = $st->fetch(PDO::FETCH_ASSOC);

    $upload_ativo    = $cfg ? ((int)$cfg['upload_ativo'] === 1) : false;
    $pasta_raiz_mega = $cfg ? (string)$cfg['nome_pasta_mega'] : '';

    // Campos exigidos para esse user+atividade (só ativos)
    $st = $pdo->prepare("
        SELECT label_campo, extensoes_permitidas, quantidade_maxima, obrigatorio, ordem
          FROM mega_campos_upload
         WHERE user_id=? AND id_atividade=? AND ativo=1
         ORDER BY ordem ASC, id_campo ASC
    ");
    $st->execute([$user_id, $id_atividade]);
    $campos = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
    foreach ($campos as &$c) {
        $c['quantidade_maxima'] = (int)$c['quantidade_maxima'];
        $c['obrigatorio']       = (int)$c['obrigatorio'] === 1;
        $c['ordem']             = (int)$c['ordem'];
    }

    // Pastas lógicas existentes (ativas), enriquecidas com o vínculo do
    // usuário corrente para que o desktop possa pintar a lista:
    //
    //   - sem subtarefa do user                → status_visual=livre   (branco)
    //   - subtarefa do user aberta/concluída   → status_visual=em_andamento ou concluida (verde)
    //   - subtarefa do user travada por pagto. → status_visual=paga    (cinza / não selecionável)
    //
    // A associação usa `s.id_atividade + s.titulo == pl.nome_pasta` porque
    // quando MEGA está ativo o título da subtarefa é exatamente o
    // `nome_pasta` retornado por `desktop_criar_pasta.php` (regra do
    // form MEGA em `app/subtarefas.py`). MAX() pra cair em uma única
    // linha por pasta caso exista duplicidade histórica.
    $st = $pdo->prepare("
        SELECT pl.id_pasta_logica,
               pl.nome_pasta,
               pl.numero_video,
               pl.titulo_video,
               pl.criado_em,
               sm.id_subtarefa AS id_subtarefa_usuario,
               sm.concluida    AS sub_concluida,
               sm.bloqueada    AS sub_bloqueada,
               sm.segundos     AS sub_segundos
          FROM mega_pasta_logica pl
          LEFT JOIN (
              SELECT s.id_atividade,
                     s.titulo,
                     MAX(s.id_subtarefa)        AS id_subtarefa,
                     MAX(s.concluida)           AS concluida,
                     MAX(s.bloqueada_pagamento) AS bloqueada,
                     MAX(s.segundos_gastos)     AS segundos
                FROM atividades_subtarefas s
               WHERE s.user_id = :user_id
               GROUP BY s.id_atividade, s.titulo
          ) sm
            ON sm.id_atividade = pl.id_atividade
           AND sm.titulo       = pl.nome_pasta
         WHERE pl.id_atividade = :id_atividade
           AND pl.ativo = 1
         ORDER BY pl.numero_video ASC, pl.criado_em DESC
    ");
    $st->execute([':user_id' => $user_id, ':id_atividade' => $id_atividade]);
    $pastas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($pastas as &$p) {
        $p['id_pasta_logica'] = (int)$p['id_pasta_logica'];

        $id_sub = (int)($p['id_subtarefa_usuario'] ?? 0);
        $concluida   = (int)($p['sub_concluida'] ?? 0) === 1;
        $bloqueada   = (int)($p['sub_bloqueada'] ?? 0) === 1;
        $segundos    = (int)($p['sub_segundos'] ?? 0);

        // Limpa campos crus do payload (mantém só os semânticos)
        unset($p['sub_concluida'], $p['sub_bloqueada'], $p['sub_segundos']);

        $p['id_subtarefa_usuario'] = $id_sub;
        $p['tem_subtarefa_usuario'] = $id_sub > 0;
        $p['concluida']             = $concluida;
        $p['bloqueada_pagamento']   = $bloqueada;
        $p['segundos_gastos']       = $segundos;

        if ($id_sub <= 0) {
            $p['status_visual'] = 'livre';
        } elseif ($bloqueada) {
            $p['status_visual'] = 'paga';
        } elseif ($concluida) {
            $p['status_visual'] = 'concluida';
        } else {
            $p['status_visual'] = 'em_andamento';
        }
    }
    unset($p);

    responder_json(true, 'OK', [
        'upload_ativo'    => $upload_ativo,
        'pasta_raiz_mega' => $pasta_raiz_mega,
        'campos_exigidos' => $campos,
        'pastas_logicas'  => $pastas,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao obter config MEGA', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
