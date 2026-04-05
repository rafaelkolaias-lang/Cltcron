<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $user_id = trim((string)($_GET['user_id'] ?? ''));

    if ($user_id === '') {
        responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
    }

    $pdo = obter_conexao_pdo();

    $st = $pdo->prepare("
        SELECT
            p.id_pagamento,
            u.user_id,
            p.id_usuario,
            p.data_pagamento,
            p.referencia_inicio,
            p.referencia_fim,
            p.travado_ate_data,
            p.valor,
            p.observacao,
            p.criado_em
        FROM Pagamentos p
        INNER JOIN usuarios u
            ON u.id_usuario = p.id_usuario
        WHERE u.user_id = :user_id
        ORDER BY p.data_pagamento DESC, p.id_pagamento DESC
    ");
    $st->execute([
        ':user_id' => $user_id,
    ]);

    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $dados = array_map(
        static function (array $linha): array {
            return [
                'id_pagamento' => isset($linha['id_pagamento']) ? (int)$linha['id_pagamento'] : 0,
                'user_id' => (string)($linha['user_id'] ?? ''),
                'id_usuario' => isset($linha['id_usuario']) ? (int)$linha['id_usuario'] : 0,
                'data_pagamento' => $linha['data_pagamento'] ?? null,
                'referencia_inicio' => $linha['referencia_inicio'] ?? null,
                'referencia_fim' => $linha['referencia_fim'] ?? null,
                'travado_ate_data' => $linha['travado_ate_data'] ?? null,
                'valor' => isset($linha['valor']) ? (float)$linha['valor'] : 0.0,
                'observacao' => $linha['observacao'] ?? null,
                'criado_em' => $linha['criado_em'] ?? null,
            ];
        },
        $linhas
    );

    responder_json(true, 'OK', $dados, 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar pagamentos', ['erro' => $e->getMessage()], 500);
}