<?php
declare(strict_types=1);

/**
 * pasta_logica_salvar_link.php — salva o link público do MEGA de uma pasta lógica.
 *
 * Auth: user_id + chave (desktop / script local).
 *
 * POST { id_pasta_logica, link_mega }
 *   - link_mega vazio ou null = limpa o link.
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';

try {
    autenticar_cliente_ou_morrer();

    $in = ler_json_do_corpo();
    $id = (int)($in['id_pasta_logica'] ?? 0);
    $link = trim((string)($in['link_mega'] ?? ''));

    if ($id <= 0) {
        responder_json(false, 'id_pasta_logica obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $st = $pdo->prepare("UPDATE mega_pasta_logica SET link_mega = ? WHERE id_pasta_logica = ? AND ativo = 1");
    $st->execute([$link === '' ? null : $link, $id]);

    if ($st->rowCount() === 0) {
        responder_json(false, 'pasta não encontrada ou inativa', null, 404);
    }

    responder_json(true, 'link salvo');
} catch (Throwable $e) {
    responder_json(false, 'falha ao salvar link', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
