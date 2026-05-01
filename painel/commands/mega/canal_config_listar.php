<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';

try {
    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // LEFT JOIN: lista TODAS as atividades, mesmo as sem config — admin precisa
    // ver os canais que ainda não foram configurados pra clicar em "ativar".
    $sql = "
        SELECT
            a.id_atividade,
            a.titulo                      AS titulo_atividade,
            a.status                      AS status_atividade,
            mc.id_config,
            COALESCE(mc.nome_pasta_mega, '') AS nome_pasta_mega,
            COALESCE(mc.upload_ativo, 0)     AS upload_ativo,
            mc.atualizado_em
        FROM atividades a
        LEFT JOIN mega_canal_config mc ON mc.id_atividade = a.id_atividade
        WHERE a.status <> 'cancelada'
        ORDER BY a.titulo ASC
    ";
    $st = $pdo->query($sql);
    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$l) {
        $l['id_atividade']   = (int)$l['id_atividade'];
        $l['id_config']      = isset($l['id_config']) ? (int)$l['id_config'] : null;
        $l['upload_ativo']   = (int)$l['upload_ativo'] === 1;
    }

    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar config de canal MEGA', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
