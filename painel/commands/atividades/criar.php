<?php
// painel/commands/atividades/criar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();
require_once __DIR__ . '/../conexao/conexao.php';

function dificuldade_valida(string $v): bool
{
    return in_array($v, ['facil','media','dificil','critica'], true);
}

function status_valido(string $v): bool
{
    return in_array($v, ['aberta','em_andamento','concluida','cancelada'], true);
}

function normalizar_estimativa_horas($valor): float
{
    if (is_int($valor) || is_float($valor)) {
        $n = (float)$valor;
        return $n < 0 ? 0.0 : $n;
    }

    $s = trim((string)$valor);
    if ($s === '') return 0.0;

    $s = str_replace(['R$', ' ', "\t", "\n", "\r"], '', $s);

    $posVirgula = strrpos($s, ',');
    $posPonto = strrpos($s, '.');

    if ($posVirgula !== false && $posPonto !== false) {
        if ($posVirgula > $posPonto) {
            $s = str_replace('.', '', $s);
            $s = str_replace(',', '.', $s);
        } else {
            $s = str_replace(',', '', $s);
        }
    } elseif ($posVirgula !== false) {
        $s = str_replace('.', '', $s);
        $s = str_replace(',', '.', $s);
    }

    $s = preg_replace('/[^0-9\.\-]/', '', $s) ?? '0';
    $n = (float)$s;
    return $n < 0 ? 0.0 : $n;
}

try {
    $in = ler_json_do_corpo();

    $titulo = trim((string)($in['titulo'] ?? ''));
    $descricao = isset($in['descricao']) ? (string)$in['descricao'] : null;
    $dificuldade = trim((string)($in['dificuldade'] ?? 'media'));
    $status = trim((string)($in['status'] ?? 'aberta'));
    $estimativa_float = normalizar_estimativa_horas($in['estimativa_horas'] ?? 0);

    $ids_usuarios = $in['ids_usuarios'] ?? [];
    if (!is_array($ids_usuarios)) $ids_usuarios = [];

    if ($titulo === '' || mb_strlen($titulo) < 3) {
        responder_json(false, 'Título inválido (mínimo 3 caracteres).', null, 400);
    }
    if (!dificuldade_valida($dificuldade)) {
        responder_json(false, 'Dificuldade inválida.', null, 400);
    }
    if (!status_valido($status)) {
        responder_json(false, 'Status inválido.', null, 400);
    }

    if ($estimativa_float > 9999.99) {
        responder_json(false, 'Estimativa muito alta. Máximo permitido: 9999,99 horas.', [
            'estimativa_horas' => $estimativa_float
        ], 400);
    }

    $ids_validos = [];
    foreach ($ids_usuarios as $id) {
        $id_int = (int)$id;
        if ($id_int > 0) $ids_validos[] = $id_int;
    }
    $ids_validos = array_values(array_unique($ids_validos));

    if (count($ids_validos) < 1) {
        responder_json(false, 'Selecione ao menos 1 usuário.', null, 400);
    }

    $pdo = obter_conexao_pdo();
    $pdo->beginTransaction();

    $st = $pdo->prepare("
        INSERT INTO atividades (titulo, descricao, dificuldade, estimativa_horas, status)
        VALUES (:titulo, :descricao, :dificuldade, :estimativa_horas, :status)
    ");
    $st->execute([
        ':titulo' => $titulo,
        ':descricao' => ($descricao !== null && trim((string)$descricao) !== '') ? $descricao : null,
        ':dificuldade' => $dificuldade,
        ':estimativa_horas' => number_format($estimativa_float, 2, '.', ''),
        ':status' => $status,
    ]);

    $id_atividade = (int)$pdo->lastInsertId();

    // valida usuários
    $placeholders = implode(',', array_fill(0, count($ids_validos), '?'));
    $stU = $pdo->prepare("SELECT id_usuario FROM usuarios WHERE id_usuario IN ($placeholders)");
    $stU->execute($ids_validos);
    $encontrados = $stU->fetchAll(PDO::FETCH_COLUMN) ?: [];
    $encontrados = array_map('intval', $encontrados);

    if (count($encontrados) < 1) {
        $pdo->rollBack();
        responder_json(false, 'Nenhum usuário válido encontrado.', null, 400);
    }

    $stV = $pdo->prepare("
        INSERT INTO atividades_usuarios (id_atividade, id_usuario)
        VALUES (:id_atividade, :id_usuario)
        ON DUPLICATE KEY UPDATE atribuida_em = atribuida_em
    ");
    foreach ($encontrados as $id_usuario) {
        $stV->execute([
            ':id_atividade' => $id_atividade,
            ':id_usuario' => $id_usuario,
        ]);
    }

    $pdo->commit();

    responder_json(true, 'Atividade criada.', [
        'id_atividade' => $id_atividade,
        'titulo' => $titulo,
        'descricao' => $descricao,
        'dificuldade' => $dificuldade,
        'estimativa_horas' => number_format($estimativa_float, 2, '.', ''),
        'status' => $status,
        'ids_usuarios' => $encontrados,
    ], 201);

} catch (Throwable $e) {
    try {
        if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) $pdo->rollBack();
    } catch (Throwable $t) { /* ignore */ }

    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = [
            'erro' => $e->getMessage(),
            'arquivo' => $e->getFile(),
            'linha' => $e->getLine(),
        ];
    }

    responder_json(false, 'falha ao criar atividade', $dados, 500);
}
