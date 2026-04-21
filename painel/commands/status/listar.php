<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    $sql = "SELECT
              u.user_id,
              u.status_conta,
              COALESCE(s.situacao, 'ocioso') AS situacao,
              COALESCE(s.atividade, '') AS atividade,
              s.inicio_em,
              s.ultimo_em,
              COALESCE(s.segundos_pausado, 0) AS segundos_pausado,
              s.apps_json
            FROM usuarios u
            LEFT JOIN usuarios_status_atual s ON s.user_id = u.user_id
            WHERE u.ocultar_dashboard = 0
            ORDER BY u.user_id ASC";

    $stm = $pdo->prepare($sql);
    $stm->execute();

    $linhas = [];
    while ($r = $stm->fetch()) {
        $apps = [];
        if (!empty($r['apps_json'])) {
            $dec = json_decode((string)$r['apps_json'], true);
            if (is_array($dec)) $apps = $dec;
        }

        $linhas[] = [
            'user_id' => (string)$r['user_id'],
            'status_conta' => (string)$r['status_conta'],
            'situacao' => (string)$r['situacao'],
            'atividade' => (string)$r['atividade'],
            'inicio_iso' => $r['inicio_em'] ? str_replace(' ', 'T', (string)$r['inicio_em']) : '',
            'ultimo_iso' => $r['ultimo_em'] ? str_replace(' ', 'T', (string)$r['ultimo_em']) : '',
            'segundos_pausado' => (int)$r['segundos_pausado'],
            'apps' => $apps,
        ];
    }

    responder_json(true, "OK", $linhas);
} catch (Throwable $e) {
    responder_json(false, "falha ao listar status", ['erro' => $e->getMessage()], 500);
}
