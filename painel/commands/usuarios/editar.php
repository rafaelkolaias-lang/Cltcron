<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function ler_json_entrada(): array
{
    $raw = file_get_contents('php://input');
    $obj = json_decode($raw ?: '', true);
    return is_array($obj) ? $obj : [];
}

function normalizar_nivel(string $nivel): string
{
    $n = strtolower(trim($nivel));
    if (in_array($n, ['iniciante', 'intermediario', 'avancado'], true)) return $n;
    return '';
}

try {
    $in = ler_json_entrada();

    $user_id = trim((string)($in['user_id'] ?? ''));
    $nome_exibicao = trim((string)($in['nome_exibicao'] ?? ''));
    $nivel = normalizar_nivel((string)($in['nivel'] ?? ''));
    $valor_hora = (float)($in['valor_hora'] ?? 0);

    if ($user_id === '') responder_json(false, 'user_id é obrigatório.', ['campo' => 'user_id'], 400);
    if ($nome_exibicao === '') responder_json(false, 'nome_exibicao é obrigatório.', ['campo' => 'nome_exibicao'], 400);
    if ($nivel === '') responder_json(false, 'nivel inválido.', ['campo' => 'nivel'], 400);
    if ($valor_hora <= 0) responder_json(false, 'valor_hora deve ser maior que zero.', ['campo' => 'valor_hora'], 400);

    if (mb_strlen($nome_exibicao) > 120) $nome_exibicao = mb_substr($nome_exibicao, 0, 120);

    $pdo = obter_conexao_pdo();

    $st = $pdo->prepare("
        UPDATE usuarios
        SET nome_exibicao = :nome_exibicao,
            nivel = :nivel,
            valor_hora = :valor_hora
        WHERE user_id = :user_id
    ");

    $st->execute([
        ':nome_exibicao' => $nome_exibicao,
        ':nivel' => $nivel,
        ':valor_hora' => $valor_hora,
        ':user_id' => $user_id,
    ]);

    // valida existência
    $st2 = $pdo->prepare("SELECT id_usuario FROM usuarios WHERE user_id = :user_id LIMIT 1");
    $st2->execute([':user_id' => $user_id]);
    if (!$st2->fetch()) {
        responder_json(false, 'Usuário não encontrado.', ['user_id' => $user_id], 404);
    }

    responder_json(true, 'Usuário atualizado.', [
        'user_id' => $user_id,
        'nome_exibicao' => $nome_exibicao,
        'nivel' => $nivel,
        'valor_hora' => round($valor_hora, 2),
    ], 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao editar usuário', ['erro' => $e->getMessage()], 500);
}
