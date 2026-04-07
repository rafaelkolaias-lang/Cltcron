<?php
// listar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $pdo = obter_conexao_pdo();

    // Compatível com MariaDB 10.4+ (sem JSON_ARRAYAGG)
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
            GROUP_CONCAT(
              CONCAT(u.id_usuario, '||', u.user_id, '||', u.nome_exibicao, '||', u.status_conta)
              SEPARATOR ';;'
            ) AS usuarios_raw
        FROM atividades a
        LEFT JOIN atividades_usuarios au ON au.id_atividade = a.id_atividade
        LEFT JOIN usuarios u ON u.id_usuario = au.id_usuario
        GROUP BY a.id_atividade
        ORDER BY a.criado_em DESC, a.id_atividade DESC
    ");
    $st->execute();

    $linhas = $st->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhas as &$linha) {
        $raw = (string)($linha['usuarios_raw'] ?? '');
        unset($linha['usuarios_raw']);

        $usuarios_filtrados = [];
        if ($raw !== '') {
            foreach (explode(';;', $raw) as $item) {
                $parts = explode('||', $item);
                if (count($parts) < 4 || (int)$parts[0] <= 0) continue;
                $usuarios_filtrados[] = [
                    'id_usuario'    => (int)$parts[0],
                    'user_id'       => $parts[1],
                    'nome_exibicao' => $parts[2],
                    'status_conta'  => $parts[3],
                ];
            }
        }
        $linha['usuarios'] = $usuarios_filtrados;
    }

    responder_json(true, 'OK', $linhas, 200);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar atividades', ['erro' => $e->getMessage()], 500);
}
