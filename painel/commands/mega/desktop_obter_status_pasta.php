<?php
declare(strict_types=1);

/**
 * desktop_obter_status_pasta.php — status COMPARTILHADO de uma pasta lógica
 * (vídeo), por pasta e não por subtarefa. Usado pelo desktop ao selecionar uma
 * pasta existente no formulário MEGA pra:
 *   (1) "verde compartilhado": saber se algum thumbmaker já entregou a thumb
 *       daquele vídeo (itens com tipo='thumb' de qualquer usuário);
 *   (2) "baixar arquivo": listar todos os arquivos já enviados na pasta (vídeo,
 *       narração/texto, projeto, thumb…) com o caminho remoto montado, pra o
 *       desktop baixar direto via mega-get sem abrir o site do MEGA.
 *
 * Diferente de desktop_obter_dados_subtarefa.php (que é por-usuário, hidrata só
 * o próprio progresso), este é por-pasta — funciona inclusive numa criação nova,
 * quando o thumbmaker ainda não tem subtarefa.
 *
 * Auth: user_id + chave (credenciais/api/_auth_cliente.php).
 * Defesa IDOR: mega_user_pertence_pasta_logica() exige vínculo com o canal.
 *
 * GET ?id_pasta_logica=X →
 *   {
 *     id_atividade: int,
 *     nome_pasta: string,
 *     pasta_raiz_mega: string,
 *     arquivos_pasta: [ {
 *        user_id, nome_exibicao, nome_campo, tipo, nome_arquivo,
 *        tamanho_bytes:int|null, enviado_em:string|null, caminho_remoto:string
 *     } ]
 *   }
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $id_pasta_logica = isset($_GET['id_pasta_logica']) ? (int)$_GET['id_pasta_logica'] : 0;
    if ($id_pasta_logica <= 0) {
        responder_json(false, 'id_pasta_logica obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Autorização (e descobre o id_atividade da pasta).
    [$ok, $id_atividade] = mega_user_pertence_pasta_logica($pdo, $user_id, $id_pasta_logica);
    if (!$ok || $id_atividade <= 0) {
        responder_json(false, 'pasta não encontrada ou sem acesso', null, 403);
    }

    // Nome da pasta lógica + raiz do canal no MEGA (pra montar o caminho remoto).
    $st = $pdo->prepare("SELECT nome_pasta FROM mega_pasta_logica WHERE id_pasta_logica = ? LIMIT 1");
    $st->execute([$id_pasta_logica]);
    $nome_pasta = (string)($st->fetchColumn() ?: '');

    $st = $pdo->prepare("SELECT nome_pasta_mega FROM mega_canal_config WHERE id_atividade = ? LIMIT 1");
    $st->execute([$id_atividade]);
    $pasta_raiz = (string)($st->fetchColumn() ?: '');

    // Arquivos concluídos da pasta (de QUALQUER usuário). Só o upload MAIS
    // RECENTE por (user_id, nome_campo) — o INNER JOIN com MAX(id_upload) descarta
    // re-uploads antigos ("Trocar arquivo"), cujas linhas 'concluido' ficam no
    // banco mas apontam pra arquivos já apagados do MEGA (dessincronizaria a lista
    // de download). O tipo vem de mega_campos_upload via (user_id + id_atividade +
    // label_campo = nome_campo); subquery escalar prioriza o campo ativo/mais novo.
    $st = $pdo->prepare("
        SELECT mu.user_id, mu.nome_campo, mu.nome_arquivo, mu.tamanho_bytes, mu.enviado_em,
               u.nome_exibicao,
               COALESCE((
                   SELECT mcu.tipo
                     FROM mega_campos_upload mcu
                    WHERE mcu.user_id = mu.user_id
                      AND mcu.id_atividade = :id_ativ
                      AND mcu.label_campo = mu.nome_campo
                    ORDER BY mcu.ativo DESC, mcu.id_campo DESC
                    LIMIT 1
               ), 'outro') AS tipo
          FROM mega_uploads mu
          JOIN (
              SELECT user_id, nome_campo, MAX(id_upload) AS max_id
                FROM mega_uploads
               WHERE id_pasta_logica = :id_pasta
                 AND status_upload = 'concluido'
               GROUP BY user_id, nome_campo
          ) ult ON ult.max_id = mu.id_upload
          LEFT JOIN usuarios u ON u.user_id = mu.user_id
         ORDER BY mu.enviado_em ASC, mu.id_upload ASC
    ");
    $st->execute([':id_ativ' => $id_atividade, ':id_pasta' => $id_pasta_logica]);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $raiz_limpa = trim($pasta_raiz, '/');
    $arquivos = [];
    foreach ($linhas as $l) {
        $uid  = (string)$l['user_id'];
        $arq  = (string)$l['nome_arquivo'];
        // Caminho remoto: /<raiz>/<nome_pasta>/<user_id>/<arquivo>. Só monta se
        // houver raiz + nome_pasta + arquivo; o desktop sanitiza antes do mega-get.
        $caminho = ($raiz_limpa !== '' && $nome_pasta !== '' && $arq !== '')
            ? '/' . $raiz_limpa . '/' . $nome_pasta . '/' . $uid . '/' . $arq
            : '';
        $arquivos[] = [
            'user_id'       => $uid,
            'nome_exibicao' => $l['nome_exibicao'] !== null ? (string)$l['nome_exibicao'] : $uid,
            'nome_campo'    => (string)$l['nome_campo'],
            'tipo'          => (string)($l['tipo'] ?? 'outro'),
            'nome_arquivo'  => $arq,
            'tamanho_bytes' => $l['tamanho_bytes'] !== null ? (int)$l['tamanho_bytes'] : null,
            'enviado_em'    => $l['enviado_em'] !== null ? (string)$l['enviado_em'] : null,
            'caminho_remoto'=> $caminho,
        ];
    }

    responder_json(true, 'OK', [
        'id_atividade'    => $id_atividade,
        'nome_pasta'      => $nome_pasta,
        'pasta_raiz_mega' => $pasta_raiz,
        'arquivos_pasta'  => $arquivos,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao obter status da pasta', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
