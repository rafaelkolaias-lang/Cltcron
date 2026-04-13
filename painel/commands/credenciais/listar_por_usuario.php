<?php
declare(strict_types=1);

/**
 * Lista todos os modelos + estado da credencial do usuário (preenchida ou vazia).
 * NUNCA devolve o valor puro. Só: id, nome, categoria, status, mascara, datas.
 */

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

try {
    $user_id = normalizar_user_id((string)($_GET['user_id'] ?? ''));
    if ($user_id === '') {
        responder_json(false, 'user_id obrigatório', null, 400);
    }

    $pdo = obter_conexao_pdo();

    // Confirma que o usuário existe
    $stm = $pdo->prepare("SELECT user_id FROM usuarios WHERE user_id=? LIMIT 1");
    $stm->execute([$user_id]);
    if (!$stm->fetch()) {
        responder_json(false, 'usuário não encontrado', null, 404);
    }

    $sql = "SELECT m.id_modelo, m.identificador, m.nome_exibicao, m.categoria, m.descricao,
                   m.ordem_exibicao,
                   c.id_credencial, c.mascara_parcial, c.status AS status_credencial,
                   c.criado_em AS credencial_criado_em,
                   c.atualizado_em AS credencial_atualizado_em,
                   c.ultimo_acesso_em
              FROM credenciais_modelos m
         LEFT JOIN credenciais_usuario c
                ON c.id_modelo = m.id_modelo AND c.user_id = ?
             WHERE m.status = 'ativo'
          ORDER BY m.ordem_exibicao ASC, m.nome_exibicao ASC";
    $stm = $pdo->prepare($sql);
    $stm->execute([$user_id]);
    $linhas = $stm->fetchAll();

    // Normaliza: preenchida / vazia / revogada
    foreach ($linhas as &$l) {
        if ($l['id_credencial'] === null) {
            $l['estado'] = 'vazia';
        } elseif ($l['status_credencial'] === 'revogado') {
            $l['estado'] = 'revogada';
        } else {
            $l['estado'] = 'preenchida';
        }
    }
    unset($l);

    responder_json(true, 'OK', $linhas);
} catch (Throwable $e) {
    responder_json(false, 'falha ao listar credenciais', debug_ativo() ? ['erro' => $e->getMessage()] : null, 500);
}
