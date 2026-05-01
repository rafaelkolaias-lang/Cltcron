<?php
declare(strict_types=1);

/**
 * desktop_pastas_logicas_para_sync.php — lista pastas lógicas ativas
 * dos canais aos quais o usuário pertence E que tenham upload_ativo=1
 * em mega_canal_config.
 *
 * Resposta agrupada por canal pra que o desktop liste a raiz uma vez por
 * canal e compare em memória, evitando N requests individuais. Cada canal
 * vem com sua `pasta_raiz_mega` e a lista de pastas lógicas que devem
 * existir no MEGA daquele canal.
 *
 * Auth: user_id + chave (mesmo padrão dos demais desktop_*).
 *
 * GET → {
 *   canais: [
 *     {
 *       id_atividade,
 *       titulo_atividade,
 *       pasta_raiz_mega,
 *       upload_ativo,           // sempre true neste endpoint
 *       pastas_logicas: [
 *         { id_pasta_logica, nome_pasta, numero_video, titulo_video }
 *       ]
 *     }, ...
 *   ]
 * }
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Canais do user com upload_ativo=1.
    $st = $pdo->prepare("
        SELECT a.id_atividade,
               a.titulo AS titulo_atividade,
               cfg.nome_pasta_mega
          FROM atividades a
          JOIN atividades_usuarios au ON au.id_atividade = a.id_atividade
          JOIN usuarios u ON u.id_usuario = au.id_usuario
          JOIN mega_canal_config cfg ON cfg.id_atividade = a.id_atividade
         WHERE u.user_id = ?
           AND a.status <> 'cancelada'
           AND cfg.upload_ativo = 1
         ORDER BY a.titulo ASC
    ");
    $st->execute([$user_id]);
    $canais = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    if (!$canais) {
        responder_json(true, 'OK', ['canais' => []]);
    }

    // Mesmo conjunto de canais usado pra puxar pastas — uma query só.
    $ids = array_map(static fn($c) => (int)$c['id_atividade'], $canais);
    $place = implode(',', array_fill(0, count($ids), '?'));
    $st = $pdo->prepare("
        SELECT id_pasta_logica, id_atividade, nome_pasta, numero_video, titulo_video
          FROM mega_pasta_logica
         WHERE ativo = 1
           AND id_atividade IN ($place)
         ORDER BY id_atividade ASC, numero_video ASC, id_pasta_logica ASC
    ");
    $st->execute($ids);
    $pastas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $por_canal = [];
    foreach ($pastas as $p) {
        $idA = (int)$p['id_atividade'];
        $por_canal[$idA][] = [
            'id_pasta_logica' => (int)$p['id_pasta_logica'],
            'nome_pasta'      => (string)$p['nome_pasta'],
            'numero_video'    => (string)$p['numero_video'],
            'titulo_video'    => (string)$p['titulo_video'],
        ];
    }

    $saida = [];
    foreach ($canais as $c) {
        $idA = (int)$c['id_atividade'];
        $saida[] = [
            'id_atividade'     => $idA,
            'titulo_atividade' => (string)$c['titulo_atividade'],
            'pasta_raiz_mega'  => (string)$c['nome_pasta_mega'],
            'upload_ativo'     => true,
            'pastas_logicas'   => $por_canal[$idA] ?? [],
        ];
    }

    responder_json(true, 'OK', ['canais' => $saida]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar pastas lógicas para sync', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
