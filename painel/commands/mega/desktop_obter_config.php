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

    // Pastas lógicas existentes (ativas)
    $st = $pdo->prepare("
        SELECT id_pasta_logica, nome_pasta, numero_video, titulo_video, criado_em
          FROM mega_pasta_logica
         WHERE id_atividade=? AND ativo=1
         ORDER BY numero_video ASC, criado_em DESC
    ");
    $st->execute([$id_atividade]);
    $pastas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
    foreach ($pastas as &$p) {
        $p['id_pasta_logica'] = (int)$p['id_pasta_logica'];
    }

    responder_json(true, 'OK', [
        'upload_ativo'    => $upload_ativo,
        'pasta_raiz_mega' => $pasta_raiz_mega,
        'campos_exigidos' => $campos,
        'pastas_logicas'  => $pastas,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao obter config MEGA', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
