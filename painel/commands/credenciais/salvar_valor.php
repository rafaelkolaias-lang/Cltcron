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
 *
 * NUNCA loga o valor puro.
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/cripto.php';

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

    // Máscara é a mesma em qualquer modo (depende do valor, não do user)
    $mascara = gerar_mascara_parcial($valor);

    // SQL de upsert compartilhado
    $sql = "INSERT INTO credenciais_usuario
                (id_modelo, user_id, mascara_parcial, valor_cifrado, nonce, versao_chave, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ativo')
            ON DUPLICATE KEY UPDATE
                mascara_parcial = VALUES(mascara_parcial),
                valor_cifrado   = VALUES(valor_cifrado),
                nonce           = VALUES(nonce),
                versao_chave    = VALUES(versao_chave),
                status          = 'ativo',
                atualizado_em   = CURRENT_TIMESTAMP";
    $upsert = $pdo->prepare($sql);

    if (!$aplicar_todos) {
        // ===== Modo individual (comportamento antigo) =====
        $stm = $pdo->prepare("SELECT user_id FROM usuarios WHERE user_id=? LIMIT 1");
        $stm->execute([$user_id]);
        if (!$stm->fetch()) {
            responder_json(false, 'usuário não encontrado', null, 404);
        }

        $cif = cifrar_segredo($valor);
        sodium_memzero($valor);

        $upsert->bindValue(1, $id_modelo, PDO::PARAM_INT);
        $upsert->bindValue(2, $user_id);
        $upsert->bindValue(3, $mascara);
        $upsert->bindValue(4, $cif['cipher'], PDO::PARAM_LOB);
        $upsert->bindValue(5, $cif['nonce'],  PDO::PARAM_LOB);
        $upsert->bindValue(6, $cif['versao'], PDO::PARAM_INT);
        $upsert->execute();

        responder_json(true, 'credencial salva', [
            'modo'            => 'individual',
            'mascara_parcial' => $mascara,
            'estado'          => 'preenchida',
        ]);
    }

    // ===== Modo global: aplica a todos os usuários ativos =====
    $usuarios = $pdo->query("SELECT user_id FROM usuarios WHERE status_conta='ativa'")
                    ->fetchAll(PDO::FETCH_COLUMN);
    if (!$usuarios) {
        sodium_memzero($valor);
        responder_json(false, 'nenhum usuário ativo encontrado', null, 404);
    }

    $pdo->beginTransaction();
    try {
        $afetados = 0;
        foreach ($usuarios as $uid) {
            // NONCE NOVO por usuário — nunca reutilizar
            $cif = cifrar_segredo($valor);
            $upsert->bindValue(1, $id_modelo, PDO::PARAM_INT);
            $upsert->bindValue(2, (string)$uid);
            $upsert->bindValue(3, $mascara);
            $upsert->bindValue(4, $cif['cipher'], PDO::PARAM_LOB);
            $upsert->bindValue(5, $cif['nonce'],  PDO::PARAM_LOB);
            $upsert->bindValue(6, $cif['versao'], PDO::PARAM_INT);
            $upsert->execute();
            $afetados++;
        }
        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        sodium_memzero($valor);
        throw $e;
    }

    sodium_memzero($valor);

    responder_json(true, "credencial aplicada a {$afetados} usuário(s)", [
        'modo'             => 'global',
        'usuarios_afetados'=> $afetados,
        'mascara_parcial'  => $mascara,
        'estado'           => 'preenchida',
    ]);
} catch (Throwable $e) {
    // não logar valor — error_log padrão só captura a mensagem do Throwable
    responder_json(false, 'falha ao salvar credencial', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
