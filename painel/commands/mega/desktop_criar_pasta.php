<?php
declare(strict_types=1);

/**
 * desktop_criar_pasta.php — cria uma nova pasta lógica no banco.
 *
 * Auth: user_id + chave.
 *
 * POST { id_atividade, numero_video, titulo_video } → cria pasta com
 * nome canônico "NN - Titulo". Bloqueia duplicidade dentro do mesmo canal.
 *
 * Resposta:
 *   - 201 com { id_pasta_logica, nome_pasta } em sucesso
 *   - 409 se já existir uma ativa com o mesmo nome (devolve a existente)
 */

require_once __DIR__ . '/../credenciais/api/_auth_cliente.php';
require_once __DIR__ . '/_estrutura.php';
require_once __DIR__ . '/_comum.php';

try {
    $u = autenticar_cliente_ou_morrer();
    $user_id = (string)$u['user_id'];

    $in = ler_json_do_corpo();
    $id_atividade = (int)($in['id_atividade'] ?? 0);
    $numero       = trim((string)($in['numero_video'] ?? ''));
    $titulo       = trim((string)($in['titulo_video'] ?? ''));

    if ($id_atividade <= 0 || $numero === '' || $titulo === '') {
        responder_json(false, 'id_atividade, numero_video e titulo_video obrigatórios', null, 400);
    }

    $nome_pasta = mega_normalizar_nome_pasta($numero, $titulo);
    if ($nome_pasta === '') {
        responder_json(false, 'numero_video deve ser numérico (1-6 dígitos) e titulo_video não pode ser vazio', null, 400);
    }

    $pdo = obter_conexao_pdo();
    mega_garantir_estrutura($pdo);

    // Confere duplicidade ANTES de inserir (UX melhor que catch 1062).
    $st = $pdo->prepare("SELECT id_pasta_logica, ativo
                           FROM mega_pasta_logica
                          WHERE id_atividade=? AND nome_pasta=? LIMIT 1");
    $st->execute([$id_atividade, $nome_pasta]);
    $existente = $st->fetch(PDO::FETCH_ASSOC);
    if ($existente) {
        // Se existir desativada, reativa (admin pode ter desativado por engano).
        if ((int)$existente['ativo'] === 0) {
            $upd = $pdo->prepare("UPDATE mega_pasta_logica SET ativo=1 WHERE id_pasta_logica=?");
            $upd->execute([(int)$existente['id_pasta_logica']]);
            responder_json(true, 'pasta lógica reativada', [
                'id_pasta_logica' => (int)$existente['id_pasta_logica'],
                'nome_pasta'      => $nome_pasta,
                'reativada'       => true,
            ], 200);
        }
        responder_json(false, 'já existe uma pasta com esse nome neste canal', [
            'id_pasta_logica' => (int)$existente['id_pasta_logica'],
            'nome_pasta'      => $nome_pasta,
        ], 409);
    }

    // Mantém numero/titulo originais separados para auditoria, mas o nome
    // canônico é o que vale para duplicidade e título da subtarefa.
    $numero_padded = strlen($numero) < 2 ? str_pad($numero, 2, '0', STR_PAD_LEFT) : $numero;

    $st = $pdo->prepare("
        INSERT INTO mega_pasta_logica
            (id_atividade, nome_pasta, numero_video, titulo_video, criado_por)
        VALUES (?,?,?,?,?)
    ");
    $st->execute([$id_atividade, $nome_pasta, $numero_padded, trim((string)preg_replace('/\s+/u', ' ', $titulo)), $user_id]);

    responder_json(true, 'pasta lógica criada', [
        'id_pasta_logica' => (int)$pdo->lastInsertId(),
        'nome_pasta'      => $nome_pasta,
    ], 201);
} catch (Throwable $e) {
    $msg = $e->getMessage();
    if (stripos($msg, 'duplicate') !== false || stripos($msg, '1062') !== false) {
        responder_json(false, 'já existe uma pasta com esse nome neste canal', null, 409);
    }
    responder_json(false, 'falha ao criar pasta lógica', debug_ativo() ? ['erro' => $msg] : null, 500);
}
