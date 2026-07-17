<?php
declare(strict_types=1);

/**
 * pasta_logica_marcar_publicado.php — marca ou desmarca uma pasta lógica
 * como "vídeo publicado no YouTube".
 *
 * Auth: sessão do painel (admin).
 *
 * POST { id_pasta_logica, publicado: 1|0 }
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/../_comum/log_atividades.php';

try {
    $in = ler_json_do_corpo();
    $id = (int)($in['id_pasta_logica'] ?? 0);
    $publicado = (int)($in['publicado'] ?? 0);

    if ($id <= 0) {
        responder_json(false, 'id_pasta_logica obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Busca estado anterior para log
    $st = $pdo->prepare("SELECT id_pasta_logica, nome_pasta, video_publicado, publicado_em, video_cancelado FROM mega_pasta_logica WHERE id_pasta_logica = ? AND ativo = 1");
    $st->execute([$id]);
    $antes = $st->fetch(PDO::FETCH_ASSOC);

    if (!$antes) {
        responder_json(false, 'pasta não encontrada ou inativa', null, 404);
    }

    if ($publicado === 1 && (int)($antes['video_cancelado'] ?? 0) === 1) {
        responder_json(false, 'vídeo está cancelado — reative antes de publicar', null, 409);
    }

    $agora = $publicado === 1 ? date('Y-m-d H:i:s') : null;

    $st = $pdo->prepare("UPDATE mega_pasta_logica SET video_publicado = ?, publicado_em = ? WHERE id_pasta_logica = ?");
    $st->execute([$publicado, $agora, $id]);

    $depois = [
        'video_publicado' => $publicado,
        'publicado_em'    => $agora,
    ];

    log_registrar(
        $pdo,
        'mega_pasta_logica',
        $publicado === 1 ? 'marcar_publicado' : 'desmarcar_publicado',
        ($publicado === 1 ? 'Marcou' : 'Desmarcou') . " publicação: {$antes['nome_pasta']}",
        $depois,
        ['video_publicado' => (int)$antes['video_publicado'], 'publicado_em' => $antes['publicado_em']],
        (string)$id
    );

    responder_json(true, $publicado === 1 ? 'marcado como publicado' : 'publicação cancelada', $depois);
} catch (Throwable $e) {
    responder_json(false, 'falha ao atualizar status de publicação', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
