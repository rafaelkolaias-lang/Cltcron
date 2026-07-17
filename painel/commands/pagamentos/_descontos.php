<?php
declare(strict_types=1);

/**
 * _descontos.php — infraestrutura da tabela `pagamento_descontos`.
 *
 * Desconto = abatimento financeiro avulso em horas (convertido em R$ pelo
 * valor/hora do usuário no momento do registro). Entra no cálculo do
 * "A pagar" da Gestão do Usuário, mas:
 *   - NÃO conta como dinheiro pago (card "Pago" e Dashboard ignoram);
 *   - NÃO trava subtarefas nem reseta o ciclo do cronômetro (por isso vive
 *     em tabela própria, fora de `Pagamentos` — o app desktop instalado
 *     consulta MAX(data_pagamento) de `Pagamentos` pra detectar ciclo novo).
 */

function pagamento_descontos_garantir_tabela(PDO $pdo): void
{
    static $verificado = false;
    if ($verificado) return;

    $pdo->exec("
        CREATE TABLE IF NOT EXISTS pagamento_descontos (
            id_desconto       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
            id_usuario        INT NOT NULL,
            data_desconto     DATE NOT NULL,
            segundos_desconto INT UNSIGNED NOT NULL DEFAULT 0,
            valor             DECIMAL(10,2) NOT NULL DEFAULT 0,
            motivo            VARCHAR(255) NOT NULL,
            criado_em         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            atualizado_em     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            KEY idx_usuario (id_usuario),
            KEY idx_data (data_desconto)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    $verificado = true;
}

/**
 * Busca id_usuario + valor_hora a partir do user_id textual.
 * Retorna null se o usuário não existir.
 */
function pagamento_descontos_buscar_usuario(PDO $pdo, string $user_id): ?array
{
    $st = $pdo->prepare("SELECT id_usuario, valor_hora FROM usuarios WHERE user_id = :uid LIMIT 1");
    $st->execute([':uid' => $user_id]);
    $linha = $st->fetch(PDO::FETCH_ASSOC);
    if (!$linha) return null;
    return [
        'id_usuario' => (int)$linha['id_usuario'],
        'valor_hora' => (float)$linha['valor_hora'],
    ];
}
