<?php
declare(strict_types=1);

/**
 * _comum.php — helpers compartilhados pelos endpoints do módulo MEGA.
 */

/**
 * Normaliza o nome de pasta lógica para o formato canônico "NN - Titulo".
 *
 * Regras (alinhadas com !executar.md):
 * - número com pelo menos 2 dígitos (zero-padded, ex.: "4" -> "04");
 * - separador único " - ";
 * - primeira letra do título em maiúscula, resto preserva acentos;
 * - colapsa espaços duplos.
 *
 * Retorna string vazia se número/título inválidos.
 */
function mega_normalizar_nome_pasta(string $numero, string $titulo): string
{
    $numero = trim($numero);
    $titulo = trim((string)preg_replace('/\s+/u', ' ', $titulo));

    if ($numero === '' || $titulo === '') return '';
    if (!preg_match('/^\d{1,6}$/', $numero)) return '';

    if (strlen($numero) < 2) {
        $numero = str_pad($numero, 2, '0', STR_PAD_LEFT);
    }

    // Primeira letra maiúscula, resto preserva.
    $primeiro = mb_substr($titulo, 0, 1, 'UTF-8');
    $resto    = mb_substr($titulo, 1, null, 'UTF-8');
    $titulo   = mb_strtoupper($primeiro, 'UTF-8') . $resto;

    return $numero . ' - ' . $titulo;
}

/**
 * Valida lista de extensões (formato "mp4,zip,png") e retorna versão
 * normalizada (lowercase, sem pontos, sem espaços). Vazio = qualquer.
 */
function mega_normalizar_extensoes(?string $extensoes): ?string
{
    if ($extensoes === null) return null;
    $extensoes = trim($extensoes);
    if ($extensoes === '') return null;

    $partes = array_filter(array_map(function ($e) {
        $e = strtolower(trim($e));
        $e = ltrim($e, '.');
        return preg_replace('/[^a-z0-9]/', '', $e) ?: '';
    }, explode(',', $extensoes)));

    return $partes ? implode(',', array_values(array_unique($partes))) : null;
}
