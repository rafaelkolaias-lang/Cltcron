<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $in = ler_json_do_corpo();
    $id_modelo     = isset($in['id_modelo']) ? (int)$in['id_modelo'] : 0;
    $identificador = strtolower(trim((string)($in['identificador'] ?? '')));
    $nome          = trim((string)($in['nome_exibicao'] ?? ''));
    $categoria     = trim((string)($in['categoria'] ?? 'api'));
    $descricao     = trim((string)($in['descricao'] ?? ''));
    $ordem         = (int)($in['ordem_exibicao'] ?? 0);

    $identificador = preg_replace('/[^a-z0-9_\-]/', '', $identificador) ?? '';
    if ($identificador === '' || $nome === '') {
        responder_json(false, 'identificador e nome_exibicao são obrigatórios', null, 400);
    }
    if (strlen($identificador) > 60 || strlen($nome) > 120) {
        responder_json(false, 'campo acima do limite', null, 400);
    }

    $pdo = obter_conexao_pdo();

    if ($id_modelo > 0) {
        $stm = $pdo->prepare("UPDATE credenciais_modelos
                                 SET identificador=?, nome_exibicao=?, categoria=?, descricao=?, ordem_exibicao=?
                               WHERE id_modelo=?");
        $stm->execute([$identificador, $nome, $categoria, $descricao !== '' ? $descricao : null, $ordem, $id_modelo]);
        responder_json(true, 'modelo atualizado', ['id_modelo' => $id_modelo]);
    } else {
        $stm = $pdo->prepare("INSERT INTO credenciais_modelos
                                (identificador, nome_exibicao, categoria, descricao, ordem_exibicao)
                              VALUES (?,?,?,?,?)");
        $stm->execute([$identificador, $nome, $categoria, $descricao !== '' ? $descricao : null, $ordem]);
        responder_json(true, 'modelo criado', ['id_modelo' => (int)$pdo->lastInsertId()]);
    }
} catch (Throwable $e) {
    $msg = $e->getMessage();
    if (stripos($msg, 'duplicate') !== false || stripos($msg, '1062') !== false) {
        responder_json(false, 'identificador já existe', null, 409);
    }
    responder_json(false, 'falha ao salvar modelo', debug_ativo() ? ['erro' => $msg] : null, 500);
}
