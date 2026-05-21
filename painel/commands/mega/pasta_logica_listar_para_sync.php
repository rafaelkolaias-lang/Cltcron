<?php
declare(strict_types=1);

/**
 * pasta_logica_listar_para_sync.php — lista TODAS as pastas lógicas ativas
 * com o nome_pasta_mega do canal, para que um script externo possa montar
 * o caminho completo no MEGA e gerar links.
 *
 * Auth: user_id + chave (desktop). SEM filtro IDOR — retorna todas as pastas
 * de todos os canais (o script precisa ver tudo).
 *
 * GET → array de { id_pasta_logica, nome_pasta, nome_pasta_mega, link_mega }
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';

try {
    autenticar_cliente_ou_morrer();

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    $sql = "
        SELECT p.id_pasta_logica,
               p.nome_pasta,
               p.link_mega,
               COALESCE(mc.nome_pasta_mega, '') AS nome_pasta_mega
        FROM mega_pasta_logica p
        JOIN atividades a ON a.id_atividade = p.id_atividade
        LEFT JOIN mega_canal_config mc ON mc.id_atividade = p.id_atividade
        WHERE p.ativo = 1
          AND a.status <> 'cancelada'
        ORDER BY mc.nome_pasta_mega ASC, p.numero_video ASC
    ";

    $st = $pdo->query($sql);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$l) {
        $l['id_pasta_logica'] = (int)$l['id_pasta_logica'];
    }

    responder_json(true, 'OK', $linhas);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar pastas para sync', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
