<?php
declare(strict_types=1);

/**
 * Substitui o valor de uma credencial (ou cria, se não existir).
 * Recebe o valor em claro via POST JSON, cifra antes de persistir e NUNCA loga.
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/../_comum/cripto.php';

try {
    $in = ler_json_do_corpo();
    $user_id   = normalizar_user_id((string)($in['user_id'] ?? ''));
    $id_modelo = (int)($in['id_modelo'] ?? 0);
    $valor     = (string)($in['valor'] ?? '');

    if ($user_id === '' || $id_modelo <= 0) {
        responder_json(false, 'user_id e id_modelo obrigatórios', null, 400);
    }
    if ($valor === '') {
        responder_json(false, 'valor não pode ser vazio (use revogar para limpar)', null, 400);
    }
    if (strlen($valor) > 8192) {
        responder_json(false, 'valor acima do limite (8KB)', null, 400);
    }

    $pdo = obter_conexao_pdo();

    $stm = $pdo->prepare("SELECT user_id FROM usuarios WHERE user_id=? LIMIT 1");
    $stm->execute([$user_id]);
    if (!$stm->fetch()) {
        responder_json(false, 'usuário não encontrado', null, 404);
    }
    $stm = $pdo->prepare("SELECT id_modelo FROM credenciais_modelos WHERE id_modelo=? AND status='ativo' LIMIT 1");
    $stm->execute([$id_modelo]);
    if (!$stm->fetch()) {
        responder_json(false, 'modelo não encontrado ou inativo', null, 404);
    }

    $cif = cifrar_segredo($valor);
    $mascara = gerar_mascara_parcial($valor);
    sodium_memzero($valor);

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
    $stm = $pdo->prepare($sql);
    $stm->bindValue(1, $id_modelo, PDO::PARAM_INT);
    $stm->bindValue(2, $user_id);
    $stm->bindValue(3, $mascara);
    $stm->bindValue(4, $cif['cipher'], PDO::PARAM_LOB);
    $stm->bindValue(5, $cif['nonce'],  PDO::PARAM_LOB);
    $stm->bindValue(6, $cif['versao'], PDO::PARAM_INT);
    $stm->execute();

    responder_json(true, 'credencial salva', [
        'mascara_parcial' => $mascara,
        'estado'          => 'preenchida',
    ]);
} catch (Throwable $e) {
    // não logar valor — error_log padrão só captura a mensagem do Throwable
    responder_json(false, 'falha ao salvar credencial', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
