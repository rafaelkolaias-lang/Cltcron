<?php
declare(strict_types=1);

/**
 * desktop_uploads_orfaos_listar.php — lista uploads do usuário atual sem
 * subtarefa vinculada (id_subtarefa IS NULL).
 *
 * Usado pelo desktop após uma queda abrupta (falta de energia, erro fatal,
 * fechamento da janela durante upload) pra detectar arquivos que foram
 * registrados em mega_uploads mas nunca chegaram a ser amarrados a uma
 * subtarefa via fluxo "Salvar e Concluir". O desktop então cria uma
 * subtarefa ABERTA com esses uploads e chama desktop_registrar_upload.php
 * (UPDATE) com id_subtarefa pra vincular.
 *
 * Inclui só status que indicam "trabalho real" (concluído ou em transição):
 * pendente/enviando/concluido. Ignora 'erro' — esses não geraram resíduo no
 * MEGA, não precisam virar subtarefa.
 *
 * Auth: user_id + chave.
 *
 * GET → {
 *   pastas: [
 *     {
 *       id_pasta_logica, id_atividade, titulo_atividade,
 *       nome_pasta, numero_video, titulo_video,
 *       pasta_raiz_mega,            // pode ser '' se canal sem config
 *       uploads: [
 *         { id_upload, nome_campo, nome_arquivo, tamanho_bytes,
 *           status_upload, criado_em, atualizado_em }
 *       ]
 *     }, ...
 *   ]
 * }
 *
 * Agrupa por pasta lógica pra o desktop criar 1 subtarefa por pasta.
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $st = $pdo->prepare("
        SELECT mu.id_upload, mu.id_pasta_logica, mu.nome_campo, mu.nome_arquivo,
               mu.tamanho_bytes, mu.status_upload, mu.criado_em, mu.atualizado_em,
               pl.id_atividade, pl.nome_pasta, pl.numero_video, pl.titulo_video,
               pl.ativo AS pasta_ativa,
               a.titulo AS titulo_atividade,
               COALESCE(cfg.nome_pasta_mega, '') AS pasta_raiz_mega
          FROM mega_uploads mu
          JOIN mega_pasta_logica pl ON pl.id_pasta_logica = mu.id_pasta_logica
          JOIN atividades a ON a.id_atividade = pl.id_atividade
          LEFT JOIN mega_canal_config cfg ON cfg.id_atividade = pl.id_atividade
         WHERE mu.user_id = ?
           AND mu.id_subtarefa IS NULL
           AND mu.status_upload IN ('pendente','enviando','concluido')
           AND a.status <> 'cancelada'
         ORDER BY pl.id_atividade ASC, mu.id_pasta_logica ASC, mu.id_upload ASC
    ");
    $st->execute([$user_id]);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $agrupado = [];
    foreach ($linhas as $l) {
        $idPL = (int)$l['id_pasta_logica'];
        if (!isset($agrupado[$idPL])) {
            $agrupado[$idPL] = [
                'id_pasta_logica'  => $idPL,
                'id_atividade'     => (int)$l['id_atividade'],
                'titulo_atividade' => (string)$l['titulo_atividade'],
                'nome_pasta'       => (string)$l['nome_pasta'],
                'numero_video'     => (string)$l['numero_video'],
                'titulo_video'     => (string)$l['titulo_video'],
                'pasta_raiz_mega'  => (string)$l['pasta_raiz_mega'],
                'pasta_ativa'      => (int)$l['pasta_ativa'] === 1,
                'uploads'          => [],
            ];
        }
        $agrupado[$idPL]['uploads'][] = [
            'id_upload'     => (int)$l['id_upload'],
            'nome_campo'    => (string)$l['nome_campo'],
            'nome_arquivo'  => (string)$l['nome_arquivo'],
            'tamanho_bytes' => $l['tamanho_bytes'] === null ? null : (int)$l['tamanho_bytes'],
            'status_upload' => (string)$l['status_upload'],
            'criado_em'     => (string)$l['criado_em'],
            'atualizado_em' => (string)$l['atualizado_em'],
        ];
    }

    responder_json(true, 'OK', ['pastas' => array_values($agrupado)]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar uploads órfãos', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
