<?php
declare(strict_types=1);

/**
 * Substitui o valor de uma credencial (ou cria, se não existir).
 *
 * Modos:
 *   - individual (padrão): aplica ao user_id informado.
 *   - global (aplicar_todos=true): aplica a TODOS os usuários com status_conta='ativa'.
 *     Cada linha é cifrada com NONCE NOVO por usuário (nunca reutilizar nonce).
 *     Sobrescreve se já existir, reativa se estiver revogada.
 *     Também marca o modelo como aplicar_novos_usuarios=1 para que usuários
 *     cadastrados depois herdem essa credencial automaticamente.
 *
 * Quando aplicar_todos=false em uma chamada para o modelo, a flag global
 * (aplicar_novos_usuarios) é DESLIGADA — assim o checkbox da UI controla
 * tanto a aplicação imediata quanto a herança futura.
 *
 * NUNCA loga o valor puro.
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/cripto.php';
require_once __DIR__ . '/../_comum/credenciais_upsert.php';

try {
    $in = ler_json_do_corpo();
    $user_id       = normalizar_user_id((string)($in['user_id'] ?? ''));
    $id_modelo     = (int)($in['id_modelo'] ?? 0);
    $valor         = (string)($in['valor'] ?? '');
    $aplicar_todos = !empty($in['aplicar_todos']);

    if ($id_modelo <= 0) {
        responder_json(false, 'id_modelo obrigatório', null, 400);
    }
    if (!$aplicar_todos && $user_id === '') {
        responder_json(false, 'user_id obrigatório (ou envie aplicar_todos=true)', null, 400);
    }
    if ($valor === '') {
        responder_json(false, 'valor não pode ser vazio (use revogar para limpar)', null, 400);
    }
    if (strlen($valor) > 8192) {
        responder_json(false, 'valor acima do limite (8KB)', null, 400);
    }

    $pdo = obter_conexao_pdo();

    $stm = $pdo->prepare("SELECT id_modelo FROM credenciais_modelos WHERE id_modelo=? AND status='ativo' LIMIT 1");
    $stm->execute([$id_modelo]);
    if (!$stm->fetch()) {
        responder_json(false, 'modelo não encontrado ou inativo', null, 404);
    }

    $mascara = gerar_mascara_parcial($valor);
    $upsert = preparar_stmt_upsert_credencial($pdo);

    if (!$aplicar_todos) {
        // ===== Modo individual =====
        $stm = $pdo->prepare("SELECT status_conta FROM usuarios WHERE user_id=? LIMIT 1");
        $stm->execute([$user_id]);
        $usr = $stm->fetch();
        if (!$usr) {
            responder_json(false, 'usuário não encontrado', null, 404);
        }
        if (strtolower((string)$usr['status_conta']) !== 'ativa') {
            sodium_memzero($valor);
            responder_json(false, 'usuário desativado — reative antes de atribuir credenciais', null, 409);
        }

        upsert_credencial_usuario_cifrada($pdo, $upsert, $id_modelo, $user_id, $valor, $mascara);
        sodium_memzero($valor);

        responder_json(true, 'credencial salva', [
            'modo'            => 'individual',
            'mascara_parcial' => $mascara,
            'estado'          => 'preenchida',
        ]);
    }

    // ===== Modo global: aplica a todos os usuários ativos e marca herança futura =====
    $usuarios = $pdo->query("SELECT user_id FROM usuarios WHERE status_conta='ativa'")
                    ->fetchAll(PDO::FETCH_COLUMN);
    if (!$usuarios) {
        sodium_memzero($valor);
        responder_json(false, 'nenhum usuário ativo encontrado', null, 404);
    }

    $stmt_flag = $pdo->prepare("UPDATE credenciais_modelos SET aplicar_novos_usuarios=1 WHERE id_modelo=?");

    $pdo->beginTransaction();
    try {
        $afetados = 0;
        foreach ($usuarios as $uid) {
            // NONCE NOVO por usuário — nunca reutilizar
            upsert_credencial_usuario_cifrada($pdo, $upsert, $id_modelo, (string)$uid, $valor, $mascara);
            $afetados++;
        }
        $stmt_flag->execute([$id_modelo]);
        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        sodium_memzero($valor);
        throw $e;
    }

    sodium_memzero($valor);

    responder_json(true, "credencial aplicada a {$afetados} usuário(s)", [
        'modo'              => 'global',
        'usuarios_afetados' => $afetados,
        'mascara_parcial'   => $mascara,
        'estado'            => 'preenchida',
        'herdar_novos'      => true,
    ]);
} catch (Throwable $e) {
    responder_json(false, 'falha ao salvar credencial', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
