<?php
declare(strict_types=1);

/**
 * desktop_obter_dados_subtarefa.php — retorna o que o desktop precisa pra
 * limpar arquivos no MEGA antes de excluir uma subtarefa.
 *
 * Auth: user_id + chave (mesmo padrão de credenciais/api/_auth_cliente.php).
 *
 * GET ?id_subtarefa=X →
 *   {
 *     id_atividade: int,
 *     titulo: string,
 *     pasta_raiz_mega: string,
 *     upload_ativo: bool,
 *     pasta_logica: { id_pasta_logica:int, nome_pasta:string, ativo:bool } | null,
 *     arquivos: [ {nome_campo, nome_arquivo, status_upload} ],
 *     outras_subtarefas_na_pasta: int  // outras subtarefas (qualquer user) com o mesmo titulo+id_atividade
 *   }
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $id_subtarefa = isset($_GET['id_subtarefa']) ? (int)$_GET['id_subtarefa'] : 0;
    if ($id_subtarefa <= 0) {
        responder_json(false, 'id_subtarefa obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Subtarefa + canal + (eventual) pasta lógica
    $st = $pdo->prepare("
        SELECT s.id_subtarefa, s.id_atividade, s.titulo,
               mc.nome_pasta_mega, mc.upload_ativo,
               pl.id_pasta_logica, pl.nome_pasta, pl.ativo AS pasta_logica_ativa
          FROM atividades_subtarefas s
          LEFT JOIN mega_canal_config mc ON mc.id_atividade = s.id_atividade
          LEFT JOIN mega_pasta_logica pl ON pl.id_atividade = s.id_atividade AND pl.nome_pasta = s.titulo
         WHERE s.id_subtarefa=? AND s.user_id=? LIMIT 1
    ");
    $st->execute([$id_subtarefa, $user_id]);
    $row = $st->fetch(PDO::FETCH_ASSOC);
    if (!$row) {
        responder_json(false, 'subtarefa não encontrada ou não pertence ao usuário', null, 404);
    }

    $id_atividade = (int)$row['id_atividade'];
    $titulo       = (string)$row['titulo'];
    $pasta_raiz   = $row['nome_pasta_mega'] !== null ? (string)$row['nome_pasta_mega'] : '';
    $upload_ativo = $row['upload_ativo'] !== null ? ((int)$row['upload_ativo'] === 1) : false;

    $pasta_logica = null;
    if ($row['id_pasta_logica'] !== null) {
        $pasta_logica = [
            'id_pasta_logica' => (int)$row['id_pasta_logica'],
            'nome_pasta'      => (string)$row['nome_pasta'],
            'ativo'           => (int)$row['pasta_logica_ativa'] === 1,
        ];
    }

    // Arquivos vinculados a essa subtarefa (qualquer status)
    $st = $pdo->prepare("
        SELECT id_upload, nome_campo, nome_arquivo, status_upload
          FROM mega_uploads
         WHERE id_subtarefa=? AND user_id=?
         ORDER BY id_upload ASC
    ");
    $st->execute([$id_subtarefa, $user_id]);
    $arquivos = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];
    foreach ($arquivos as &$a) {
        $a['id_upload'] = (int)$a['id_upload'];
    }
    unset($a);

    // Outras subtarefas (qualquer user) que reusam a mesma pasta lógica.
    // Critério: mesmo id_atividade + mesmo titulo + id_subtarefa diferente.
    $outras = 0;
    $st = $pdo->prepare("
        SELECT COUNT(*) AS n
          FROM atividades_subtarefas
         WHERE id_atividade=? AND titulo=? AND id_subtarefa<>?
    ");
    $st->execute([$id_atividade, $titulo, $id_subtarefa]);
    $rowc = $st->fetch(PDO::FETCH_ASSOC);
    if ($rowc) $outras = (int)$rowc['n'];

    responder_json(true, 'OK', [
        'id_atividade'              => $id_atividade,
        'titulo'                    => $titulo,
        'pasta_raiz_mega'           => $pasta_raiz,
        'upload_ativo'              => $upload_ativo,
        'pasta_logica'              => $pasta_logica,
        'arquivos'                  => $arquivos,
        'outras_subtarefas_na_pasta'=> $outras,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao obter dados da subtarefa', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
