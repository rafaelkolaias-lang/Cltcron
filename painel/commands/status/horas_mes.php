<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $user_id = normalizar_user_id((string)($_GET['user_id'] ?? ''));
    if ($user_id === '') {
        responder_json(false, "user_id inválido", null, 400);
    }

    $mes = (string)($_GET['mes'] ?? '');
    if (!preg_match('/^\d{4}\-\d{2}$/', $mes)) {
        $mes = date('Y-m');
    }

    $pdo = obter_conexao_pdo();

    // Fonte REAL do cronômetro é `cronometro_relatorios` (o desktop grava aqui).
    // `registros_tempo` é tabela legada e VAZIA — a versão anterior lia dela e
    // retornava sempre 00:00 pra todo mundo. Mês derivado de
    // COALESCE(referencia_data, DATE(criado_em)), mesmo critério de
    // tempo_trabalhado.php/graficos.php para relatórios antigos sem referencia_data.
    // Obs.: cronometro_relatorios não tem marcador de pagamento por linha, então o
    // antigo filtro "excluir horas já pagas" (coluna de registros_tempo) não se
    // aplica aqui — o retorno é o total cronometrado do mês.
    $sql = "SELECT
                COALESCE(SUM(segundos_trabalhando), 0) AS trabalhando,
                COALESCE(SUM(segundos_ocioso), 0)      AS ocioso,
                COALESCE(SUM(segundos_pausado), 0)     AS pausado
            FROM cronometro_relatorios
            WHERE user_id = :user_id
              AND DATE_FORMAT(COALESCE(referencia_data, DATE(criado_em)), '%Y-%m') = :mes";

    $stm = $pdo->prepare($sql);
    $stm->execute([':user_id' => $user_id, ':mes' => $mes]);
    $r = $stm->fetch() ?: [];

    $mapa = [
        'trabalhando' => (int)($r['trabalhando'] ?? 0),
        'ocioso'      => (int)($r['ocioso'] ?? 0),
        'pausado'     => (int)($r['pausado'] ?? 0),
    ];

    responder_json(true, "OK", [
        'user_id' => $user_id,
        'mes' => $mes,
        'segundos' => $mapa,
    ]);
} catch (Throwable $e) {
    responder_json(false, "falha ao calcular horas do mês", ['erro' => $e->getMessage()], 500);
}
