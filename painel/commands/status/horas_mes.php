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

    // Tenta filtrar horas já pagas; fallback se coluna id_pagamento não existe
    try {
        $pdo->query("SELECT id_pagamento FROM registros_tempo LIMIT 0");
        $filtro_pago = " AND id_pagamento IS NULL";
    } catch (Throwable $_) {
        $filtro_pago = "";
    }

    $sql = "SELECT situacao, SUM(segundos) AS total_segundos
            FROM registros_tempo
            WHERE user_id = :user_id AND referencia_mes = :mes{$filtro_pago}
            GROUP BY situacao";

    $stm = $pdo->prepare($sql);
    $stm->execute([':user_id' => $user_id, ':mes' => $mes]);

    $mapa = ['trabalhando' => 0, 'ocioso' => 0, 'pausado' => 0];
    while ($r = $stm->fetch()) {
        $sit = (string)$r['situacao'];
        $mapa[$sit] = (int)($r['total_segundos'] ?? 0);
    }

    responder_json(true, "OK", [
        'user_id' => $user_id,
        'mes' => $mes,
        'segundos' => $mapa,
    ]);
} catch (Throwable $e) {
    responder_json(false, "falha ao calcular horas do mês", ['erro' => $e->getMessage()], 500);
}
