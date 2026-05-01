<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

/**
 * POST — cria ou atualiza um modelo (template) de campo de upload.
 * Payload: { id_modelo?, nome_modelo, label_campo,
 *            extensoes_permitidas?, quantidade_maxima?, obrigatorio?, ativo?, ordem? }
 *
 * `nome_modelo` é único — UPDATE quando id_modelo > 0; INSERT caso contrário.
 * Conflito de nome em INSERT vira 409.
 */
try {
    $in = ler_json_do_corpo();
    $id_modelo   = (int)($in['id_modelo'] ?? 0);
    $nome        = trim((string)($in['nome_modelo'] ?? ''));
    $label       = trim((string)($in['label_campo'] ?? ''));
    $extensoes   = mega_normalizar_extensoes(isset($in['extensoes_permitidas']) ? (string)$in['extensoes_permitidas'] : null);
    $quantidade  = max(0, (int)($in['quantidade_maxima'] ?? 1));
    $obrigatorio = !empty($in['obrigatorio']) ? 1 : 0;
    $ordem       = max(0, (int)($in['ordem'] ?? 0));
    $ativo       = array_key_exists('ativo', $in) ? (!empty($in['ativo']) ? 1 : 0) : 1;

    if ($nome === '' || $label === '') {
        responder_json(false, 'nome_modelo e label_campo são obrigatórios', null, 400);
    }
    if (mb_strlen($nome) > 120 || mb_strlen($label) > 120) {
        responder_json(false, 'nome_modelo/label_campo acima do limite (120)', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    if ($id_modelo > 0) {
        // UPDATE — checa colisão de nome em outro registro ativo.
        $st = $pdo->prepare("SELECT id_modelo FROM mega_campos_modelos
                              WHERE nome_modelo = ? AND id_modelo <> ? LIMIT 1");
        $st->execute([$nome, $id_modelo]);
        if ($st->fetchColumn()) {
            responder_json(false, 'já existe outro modelo com esse nome', null, 409);
        }

        $st = $pdo->prepare("
            UPDATE mega_campos_modelos
               SET nome_modelo=?, label_campo=?, extensoes_permitidas=?,
                   quantidade_maxima=?, obrigatorio=?, ordem=?, ativo=?
             WHERE id_modelo=?
        ");
        $st->execute([$nome, $label, $extensoes, $quantidade, $obrigatorio, $ordem, $ativo, $id_modelo]);
        responder_json(true, 'modelo atualizado', ['id_modelo' => $id_modelo]);
    } else {
        $st = $pdo->prepare("
            INSERT INTO mega_campos_modelos
                (nome_modelo, label_campo, extensoes_permitidas,
                 quantidade_maxima, obrigatorio, ordem, ativo)
            VALUES (?,?,?,?,?,?,?)
        ");
        try {
            $st->execute([$nome, $label, $extensoes, $quantidade, $obrigatorio, $ordem, $ativo]);
        } catch (PDOException $e) {
            // 23000 = integrity violation (UNIQUE nome_modelo).
            if ((string)$e->getCode() === '23000') {
                responder_json(false, 'já existe um modelo com esse nome', null, 409);
            }
            throw $e;
        }
        responder_json(true, 'modelo criado', ['id_modelo' => (int)$pdo->lastInsertId()]);
    }
} catch (Throwable $e) {
    responder_json(false, 'falha ao salvar modelo de campo', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
