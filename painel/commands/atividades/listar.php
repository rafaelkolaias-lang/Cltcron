<?php
// listar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    $st = $pdo->prepare("
        SELECT
            a.id_atividade,
            a.titulo,
            a.descricao,
            a.dificuldade,
            a.estimativa_horas,
            a.status,
            a.criado_em,
            a.atualizado_em,
            COALESCE(
              JSON_ARRAYAGG(
                JSON_OBJECT(
                  'id_usuario', u.id_usuario,
                  'user_id', u.user_id,
                  'nome_exibicao', u.nome_exibicao,
                  'status_conta', u.status_conta
                )
              ),
              JSON_ARRAY()
            ) AS usuarios
        FROM atividades a
        LEFT JOIN atividades_usuarios au ON au.id_atividade = a.id_atividade
        LEFT JOIN usuarios u ON u.id_usuario = au.id_usuario
        GROUP BY a.id_atividade
        ORDER BY a.criado_em DESC, a.id_atividade DESC
    ");
    $st->execute();

    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$linha) {
        $usuarios = json_decode((string)($linha['usuarios'] ?? '[]'), true);
        if (!is_array($usuarios)) $usuarios = [];

        // remove itens "nulos" (quando não tem join)
        $usuarios_filtrados = [];
        foreach ($usuarios as $u) {
            if (!is_array($u)) continue;
            $id_usuario = (int)($u['id_usuario'] ?? 0);
            if ($id_usuario <= 0) continue;
            $usuarios_filtrados[] = $u;
        }

        $linha['usuarios'] = $usuarios_filtrados;
    }

    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar atividades', ['erro' => $e->getMessage()], 500);
}
