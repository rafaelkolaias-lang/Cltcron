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
 * Confere se o usuário pertence à atividade (canal). Retorna true se o
 * vínculo existe em `atividades_usuarios`. Usado pelos endpoints do desktop
 * pra impedir IDOR — sem isso, qualquer user autenticado poderia consultar
 * config/criar pasta/registrar upload em canais que não tem acesso.
 *
 * NOTA SOBRE O JOIN: `atividades_usuarios` usa `id_usuario` (PK numérica de
 * `usuarios`), enquanto o `user_id` que vem do auth do desktop é a string
 * pública de identificação (ex.: "adm"). Tem que mapear via JOIN — query
 * direta com `WHERE user_id = ?` quebra com `Unknown column`.
 */
function mega_user_pertence_atividade(PDO $pdo, string $user_id, int $id_atividade): bool
{
    if ($user_id === '' || $id_atividade <= 0) return false;
    $st = $pdo->prepare("
        SELECT 1
          FROM atividades_usuarios au
          JOIN usuarios u ON u.id_usuario = au.id_usuario
         WHERE u.user_id = ? AND au.id_atividade = ?
         LIMIT 1
    ");
    $st->execute([$user_id, $id_atividade]);
    return (bool)$st->fetchColumn();
}

/**
 * Mesma checagem partindo do id_pasta_logica (lookup do id_atividade dela
 * em mega_pasta_logica). Retorna [bool ok, int id_atividade]. Se a pasta
 * lógica não existe, retorna [false, 0].
 */
function mega_user_pertence_pasta_logica(PDO $pdo, string $user_id, int $id_pasta_logica): array
{
    if ($user_id === '' || $id_pasta_logica <= 0) return [false, 0];
    $st = $pdo->prepare("
        SELECT id_atividade
          FROM mega_pasta_logica
         WHERE id_pasta_logica = ?
         LIMIT 1
    ");
    $st->execute([$id_pasta_logica]);
    $id_atividade = (int)($st->fetchColumn() ?: 0);
    if ($id_atividade <= 0) return [false, 0];
    return [mega_user_pertence_atividade($pdo, $user_id, $id_atividade), $id_atividade];
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
