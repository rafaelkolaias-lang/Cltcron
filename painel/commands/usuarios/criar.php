<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

function gerar_chave_acesso(): string
{
    try {
        $bytes = random_bytes(16);
        $hex = bin2hex($bytes);
        return 'rk_' . substr($hex, 0, 6) . '_' . substr($hex, 6, 6) . '_' . substr($hex, 12, 6);
    } catch (Throwable $e) {
        $rnd = bin2hex((string)mt_rand());
        return 'rk_' . substr($rnd, 0, 6) . '_' . substr($rnd, 6, 6) . '_' . substr($rnd, 12, 6);
    }
}

try {
    $entrada = ler_json_do_corpo();

    $user_id = normalizar_user_id((string)($entrada['user_id'] ?? ''));
    $nome_exibicao = trim((string)($entrada['nome_exibicao'] ?? ''));
    $nivel = strtolower(trim((string)($entrada['nivel'] ?? 'intermediario')));
    $valor_hora = (float)($entrada['valor_hora'] ?? 0);

    if ($user_id === '') {
        responder_json(false, "user_id inválido", null, 400);
    }
    if ($nome_exibicao === '') {
        $nome_exibicao = $user_id;
    }
    if (!nivel_valido($nivel)) {
        responder_json(false, "nivel inválido", null, 400);
    }
    if ($valor_hora <= 0) {
        responder_json(false, "valor_hora inválido", null, 400);
    }

    $pdo = obter_conexao_pdo();

    // garante unicidade
    $stm = $pdo->prepare("SELECT 1 FROM usuarios WHERE user_id = :user_id LIMIT 1");
    $stm->execute([':user_id' => $user_id]);
    if ($stm->fetchColumn()) {
        responder_json(false, "Usuário já existe", ['user_id' => $user_id], 409);
    }

    $chave = gerar_chave_acesso();

    $sql = "INSERT INTO usuarios (user_id, nome_exibicao, nivel, valor_hora, chave, status_conta)
            VALUES (:user_id, :nome_exibicao, :nivel, :valor_hora, :chave, 'ativa')";
    $stm = $pdo->prepare($sql);
    $stm->execute([
        ':user_id' => $user_id,
        ':nome_exibicao' => $nome_exibicao,
        ':nivel' => $nivel,
        ':valor_hora' => $valor_hora,
        ':chave' => $chave,
    ]);

    responder_json(true, "Usuário criado", [
        'user_id' => $user_id,
        'nome_exibicao' => $nome_exibicao,
        'nivel' => $nivel,
        'valor_hora' => (float)$valor_hora,
        'chave' => $chave,
        'status_conta' => 'ativa',
    ]);
} catch (Throwable $e) {
    responder_json(false, "falha ao criar usuário", ['erro' => $e->getMessage()], 500);
}
