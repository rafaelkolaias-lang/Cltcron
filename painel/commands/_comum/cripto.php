<?php
declare(strict_types=1);

/**
 * cripto.php — criptografia autenticada para segredos em repouso.
 *
 * Algoritmo: XSalsa20-Poly1305 (libsodium secretbox).
 * Chave mestra: APP_SECRETS_MASTER_KEY (32 bytes, codificada em base64 no .env).
 * Nonce: 24 bytes aleatórios por item (armazenado ao lado do ciphertext).
 *
 * Regras:
 *  - A chave mestra NUNCA é logada, exibida ou devolvida pela API.
 *  - Ciphertext inclui MAC (Poly1305) — integridade garantida.
 *  - Versão 1 = sodium secretbox. Reservado versao_chave para rotação futura.
 */

require_once __DIR__ . '/env.php';

if (!function_exists('sodium_crypto_secretbox')) {
    // libsodium é embutido no PHP 7.2+. Se faltar, erro imediato evita fallback inseguro.
    throw new RuntimeException('libsodium indisponível — atualizar PHP ou habilitar extensão sodium.');
}

function obter_chave_mestra_secreta(): string
{
    $bruto = getenv('APP_SECRETS_MASTER_KEY');
    if ($bruto === false || $bruto === '') {
        throw new RuntimeException('APP_SECRETS_MASTER_KEY ausente no ambiente (.env).');
    }
    $chave = base64_decode((string)$bruto, true);
    if ($chave === false || strlen($chave) !== SODIUM_CRYPTO_SECRETBOX_KEYBYTES) {
        throw new RuntimeException('APP_SECRETS_MASTER_KEY inválida — deve ser 32 bytes em base64.');
    }
    return $chave;
}

/**
 * Cifra um texto puro com a chave mestra.
 * Retorna ['cipher' => <bytes>, 'nonce' => <bytes>, 'versao' => 1].
 */
function cifrar_segredo(string $valor_puro): array
{
    $chave = obter_chave_mestra_secreta();
    $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
    $cipher = sodium_crypto_secretbox($valor_puro, $nonce, $chave);
    sodium_memzero($chave);
    return [
        'cipher' => $cipher,
        'nonce'  => $nonce,
        'versao' => 1,
    ];
}

/**
 * Decifra um ciphertext. Lança RuntimeException se MAC inválido.
 */
function decifrar_segredo(string $cipher, string $nonce, int $versao = 1): string
{
    if ($versao !== 1) {
        throw new RuntimeException("versão de chave não suportada: $versao");
    }
    if (strlen($nonce) !== SODIUM_CRYPTO_SECRETBOX_NONCEBYTES) {
        throw new RuntimeException('nonce com tamanho inválido');
    }
    $chave = obter_chave_mestra_secreta();
    $puro = sodium_crypto_secretbox_open($cipher, $nonce, $chave);
    sodium_memzero($chave);
    if ($puro === false) {
        throw new RuntimeException('falha ao decifrar — MAC inválido ou chave incorreta');
    }
    return $puro;
}

/**
 * Gera uma máscara parcial segura para exibição na UI.
 * Exemplos: 'sk-proj-abc...xyz9', 'AIza...9f2', '***(24)' (fallback).
 */
function gerar_mascara_parcial(string $valor_puro): string
{
    $len = strlen($valor_puro);
    if ($len <= 8) {
        return '***(' . $len . ')';
    }
    $inicio = substr($valor_puro, 0, 4);
    $fim    = substr($valor_puro, -3);
    return $inicio . '...' . $fim;
}
