<?php
// painel/commands/auditoria/salvar_app_suspeito.php
// POST JSON:
//   - Criar:  { nome_app: "gs-auto-clicker", motivo: "...", ativo: 1 }
//   - Editar: { id: 5, nome_app: "...", motivo: "...", ativo: 0|1 }
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function normalizar_nome_app(string $valor): string
{
    // Match é por LIKE '%substring%' — então guardamos em lower-case e trim,
    // sem precisar de regex complexo. Mantemos pontos/hifens/underscores.
    $v = strtolower(trim($valor));
    $v = preg_replace('/\s+/', ' ', $v) ?? '';
    return $v;
}

try {
    $in = ler_json_do_corpo();

    $id        = isset($in['id']) ? (int)$in['id'] : 0;
    $nome_app  = normalizar_nome_app((string)($in['nome_app'] ?? ''));
    $motivo    = trim((string)($in['motivo'] ?? ''));
    $ativo     = isset($in['ativo']) ? ((int)$in['ativo'] === 1 ? 1 : 0) : 1;

    if ($nome_app === '' || mb_strlen($nome_app) < 2) {
        responder_json(false, 'Nome do app inválido (mínimo 2 caracteres).', null, 400);
    }
    if (mb_strlen($nome_app) > 180) {
        responder_json(false, 'Nome do app muito longo (máximo 180 caracteres).', null, 400);
    }
    if (mb_strlen($motivo) > 255) {
        responder_json(false, 'Motivo muito longo (máximo 255 caracteres).', null, 400);
    }
    if ($motivo === '') {
        $motivo_db = null;
    } else {
        $motivo_db = $motivo;
    }

    $pdo = obter_conexao_pdo();

    if ($id > 0) {
        // ── Edição ──
        // Garante que o ID existe
        $stC = $pdo->prepare("SELECT id FROM auditoria_apps_suspeitos WHERE id = :id");
        $stC->execute([':id' => $id]);
        if (!$stC->fetch()) {
            responder_json(false, 'Registro não encontrado.', null, 404);
        }

        // Checa se outro registro ativo tem o mesmo nome
        $stDup = $pdo->prepare("
            SELECT id FROM auditoria_apps_suspeitos
            WHERE nome_app = :nome AND id <> :id
            LIMIT 1
        ");
        $stDup->execute([':nome' => $nome_app, ':id' => $id]);
        if ($stDup->fetch()) {
            responder_json(false, 'Já existe outro registro com esse nome.', null, 409);
        }

        $st = $pdo->prepare("
            UPDATE auditoria_apps_suspeitos
            SET nome_app = :nome_app,
                motivo   = :motivo,
                ativo    = :ativo
            WHERE id = :id
        ");
        $st->execute([
            ':nome_app' => $nome_app,
            ':motivo'   => $motivo_db,
            ':ativo'    => $ativo,
            ':id'       => $id,
        ]);

        responder_json(true, 'App atualizado.', [
            'id'       => $id,
            'nome_app' => $nome_app,
            'motivo'   => $motivo_db,
            'ativo'    => $ativo,
        ], 200);
    }

    // ── Criação ──
    // Se já existe (inclusive inativo), reativa em vez de duplicar
    $stDup = $pdo->prepare("SELECT id FROM auditoria_apps_suspeitos WHERE nome_app = :nome LIMIT 1");
    $stDup->execute([':nome' => $nome_app]);
    $existe = $stDup->fetch();
    if ($existe) {
        $id_existente = (int)$existe['id'];
        $st = $pdo->prepare("
            UPDATE auditoria_apps_suspeitos
            SET motivo = :motivo, ativo = 1
            WHERE id = :id
        ");
        $st->execute([':motivo' => $motivo_db, ':id' => $id_existente]);

        responder_json(true, 'App reativado (já existia).', [
            'id'       => $id_existente,
            'nome_app' => $nome_app,
            'motivo'   => $motivo_db,
            'ativo'    => 1,
        ], 200);
    }

    $st = $pdo->prepare("
        INSERT INTO auditoria_apps_suspeitos (nome_app, motivo, ativo, criado_por)
        VALUES (:nome_app, :motivo, :ativo, :criado_por)
    ");
    $st->execute([
        ':nome_app'   => $nome_app,
        ':motivo'     => $motivo_db,
        ':ativo'      => $ativo,
        ':criado_por' => PAINEL_USUARIO,
    ]);
    $novo_id = (int)$pdo->lastInsertId();

    responder_json(true, 'App cadastrado.', [
        'id'         => $novo_id,
        'nome_app'   => $nome_app,
        'motivo'     => $motivo_db,
        'ativo'      => $ativo,
        'criado_por' => PAINEL_USUARIO,
    ], 201);

} catch (Throwable $e) {
    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = ['erro' => $e->getMessage(), 'arquivo' => $e->getFile(), 'linha' => $e->getLine()];
    }
    responder_json(false, 'falha ao salvar app suspeito', $dados, 500);
}
