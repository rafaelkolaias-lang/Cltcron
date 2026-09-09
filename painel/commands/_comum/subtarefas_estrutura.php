<?php
declare(strict_types=1);

/**
 * subtarefas_estrutura.php — garante colunas extras na tabela
 * `atividades_subtarefas`.
 *
 * Idempotente. Chamado pelos endpoints que dependem dessas colunas.
 *
 * `valor_hora` (2026-09-09): snapshot do R$/h do usuário no momento em que a
 * tarefa foi CONCLUÍDA (declarada). Antes o painel multiplicava horas antigas
 * pelo `usuarios.valor_hora` ATUAL — um reajuste de valor reprecificava todo o
 * histórico já pago e fazia o "A pagar" do filtro TUDO divergir do PENDENTE.
 * NULL = tarefa anterior ao snapshot → os cálculos caem no valor atual
 * (`COALESCE(s.valor_hora, u.valor_hora)`), preservando o comportamento antigo.
 * O desktop (`declaracoes_dia.py::_garantir_colunas_subtarefas`) cria a mesma
 * coluna; os dois lados são idempotentes.
 */

require_once __DIR__ . '/../conexao/conexao.php';

if (!function_exists('subtarefas_garantir_valor_hora')) {
    function subtarefas_garantir_valor_hora(?PDO $pdo = null): void
    {
        static $ja_garantido = false;
        if ($ja_garantido) return;

        $pdo = $pdo ?: obter_conexao_pdo();
        try {
            $linha = $pdo->query(
                "SELECT 1 FROM information_schema.COLUMNS
                  WHERE TABLE_SCHEMA = DATABASE()
                    AND TABLE_NAME = 'atividades_subtarefas'
                    AND COLUMN_NAME = 'valor_hora'
                  LIMIT 1"
            )->fetchColumn();
            if (!$linha) {
                $pdo->exec(
                    "ALTER TABLE atividades_subtarefas
                       ADD COLUMN valor_hora DECIMAL(10,2) NULL DEFAULT NULL AFTER segundos_gastos"
                );
            }
            $ja_garantido = true;
        } catch (Throwable $_e) {
            // Se a verificação/ALTER falhar, não bloqueia o endpoint — propaga só
            // se ele realmente tentar gravar/ler a coluna.
        }
    }
}
