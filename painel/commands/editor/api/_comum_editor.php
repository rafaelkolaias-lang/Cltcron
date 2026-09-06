<?php
declare(strict_types=1);

/**
 * _comum_editor.php — ajudantes dos endpoints do Editor Premiere Premium
 * (gastos e produções por usuário).
 *
 * Autenticação: a mesma dos endpoints de credenciais (`_auth_cliente.php`,
 * user_id + chave do usuário logado no app). Reaproveitada de propósito —
 * o editor já manda essas credenciais por query string.
 *
 * Tabelas: `editor_gastos` e `editor_producoes` (editor_gastos_tabelas.sql).
 */

require_once __DIR__ . '/../../_comum/resposta.php';
require_once __DIR__ . '/../../conexao/conexao.php';
require_once __DIR__ . '/../../credenciais/api/_auth_cliente.php';

/** Teto de itens por lote de registro (o app manda em lotes pequenos). */
const EDITOR_MAX_LOTE = 200;

/** Teto de lançamentos devolvidos na listagem (a agregação por dia é completa). */
const EDITOR_MAX_ITENS_LISTA = 2000;

/** Teto de fichas de produção devolvidas na listagem. */
const EDITOR_MAX_PRODUCOES_LISTA = 1000;

/**
 * Mesma regra do app (`cost_tracker.is_adm`): a conta "adm" é a que tem
 * user_id OU nome de exibição igual a "adm".
 */
function editor_eh_adm(array $u): bool
{
    $uid  = strtolower(trim((string)($u['user_id'] ?? '')));
    $nome = strtolower(trim((string)($u['nome_exibicao'] ?? '')));
    return $uid === 'adm' || $nome === 'adm';
}

function editor_exigir_adm(array $u): void
{
    if (!editor_eh_adm($u)) {
        responder_json(false, 'somente a conta adm pode listar', null, 403);
    }
}

/** uuid4 em hex (32 chars) gerado pelo app. Qualquer outra coisa é rejeitada. */
function editor_uid_valido(string $uid): bool
{
    return (bool)preg_match('/^[0-9a-f]{32}$/', $uid);
}

/**
 * "AAAA-MM-DD HH:MM" (formato do app) ou "AAAA-MM-DD HH:MM:SS".
 * Devolve [datetime_sql, dia] ou null se inválido.
 */
function editor_normalizar_quando(string $quando): ?array
{
    $q = trim($quando);
    foreach (['Y-m-d H:i:s', 'Y-m-d H:i'] as $fmt) {
        $dt = DateTime::createFromFormat($fmt, $q);
        if ($dt !== false && $dt->format($fmt) === $q) {
            return [$dt->format('Y-m-d H:i:s'), $dt->format('Y-m-d')];
        }
    }
    return null;
}

function editor_texto(mixed $v, int $max): string
{
    $s = is_scalar($v) ? trim((string)$v) : '';
    if (function_exists('mb_substr')) {
        return mb_substr($s, 0, $max, 'UTF-8');
    }
    return substr($s, 0, $max);
}

function editor_numero(mixed $v, float $min = 0.0, float $max = 1.0e9): float
{
    if (!is_numeric($v)) return 0.0;
    $f = (float)$v;
    if (!is_finite($f)) return 0.0;
    return max($min, min($max, $f));
}

/** `dias` da query: 0 = tudo; senão a data mais antiga que entra. */
function editor_data_inicio_do_periodo(int $dias): ?string
{
    if ($dias <= 0) return null;
    $d = new DateTime('today');
    $d->modify('-' . ($dias - 1) . ' days');
    return $d->format('Y-m-d');
}
