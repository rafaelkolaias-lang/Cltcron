<?php
declare(strict_types=1);

/**
 * pasta_logica_marcar_cancelado.php — marca ou desmarca uma pasta lógica
 * como "vídeo cancelado" (não será publicado), com nota opcional do motivo.
 *
 * Marcação apenas do painel — o app desktop não muda de comportamento.
 *
 * Auth: sessão do painel (admin).
 *
 * POST { id_pasta_logica, cancelado: 1|0, nota?: string }
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
    $cancelado = (int)($in['cancelado'] ?? 0);
    $nota = trim((string)($in['nota'] ?? ''));

    if ($id <= 0) {
        responder_json(false, 'id_pasta_logica obrigatório', null, 400);
    }

    if (mb_strlen($nota) > 500) {
        $nota = mb_substr($nota, 0, 500);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $st = $pdo->prepare("SELECT id_pasta_logica, nome_pasta, video_publicado, video_cancelado, cancelado_em, cancelado_nota FROM mega_pasta_logica WHERE id_pasta_logica = ? AND ativo = 1");
    $st->execute([$id]);
    $antes = $st->fetch(PDO::FETCH_ASSOC);

    if (!$antes) {
        responder_json(false, 'pasta não encontrada ou inativa', null, 404);
    }

    if ($cancelado === 1 && (int)$antes['video_publicado'] === 1) {
        responder_json(false, 'vídeo já publicado — despublique antes de cancelar', null, 409);
    }

    $agora = $cancelado === 1 ? date('Y-m-d H:i:s') : null;
    $notaFinal = $cancelado === 1 ? ($nota !== '' ? $nota : null) : null;

    $st = $pdo->prepare("UPDATE mega_pasta_logica SET video_cancelado = ?, cancelado_em = ?, cancelado_nota = ? WHERE id_pasta_logica = ?");
    $st->execute([$cancelado, $agora, $notaFinal, $id]);

    $depois = [
        'video_cancelado' => $cancelado,
        'cancelado_em'    => $agora,
        'cancelado_nota'  => $notaFinal,
    ];

    log_registrar(
        $pdo,
        'mega_pasta_logica',
        $cancelado === 1 ? 'cancelar_video' : 'reativar_video',
        ($cancelado === 1
            ? "Cancelou vídeo: {$antes['nome_pasta']}" . ($notaFinal !== null ? " (nota: {$notaFinal})" : '')
            : "Reativou vídeo: {$antes['nome_pasta']}"),
        $depois,
        [
            'video_cancelado' => (int)$antes['video_cancelado'],
            'cancelado_em'    => $antes['cancelado_em'],
            'cancelado_nota'  => $antes['cancelado_nota'],
        ],
        (string)$id
    );

    responder_json(true, $cancelado === 1 ? 'vídeo cancelado' : 'vídeo reativado', $depois);
} catch (Throwable $e) {
    responder_json(false, 'falha ao atualizar cancelamento do vídeo', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
