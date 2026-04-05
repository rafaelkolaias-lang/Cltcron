<?php
// painel/commands/atividades/editar.php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/resposta.php';
require_once __DIR__ . '/../conexao/conexao.php';

function dificuldade_valida(string $v): bool
{
    return in_array($v, ['facil', 'media', 'dificil', 'critica'], true);
}

function status_valido(string $v): bool
{
    return in_array($v, ['aberta', 'em_andamento', 'concluida', 'cancelada'], true);
}

/**
 * Aceita:
 * - "120" / 120
 * - "120,5"
 * - "120.5"
 * - "1.234,56"
 * - "1,234.56"
 */
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

    // Se tem vírgula e ponto: o último separador é o decimal
    if ($posVirgula !== false && $posPonto !== false) {
        if ($posVirgula > $posPonto) {
            // decimal = vírgula, ponto = milhar
            $s = str_replace('.', '', $s);
            $s = str_replace(',', '.', $s);
        } else {
            // decimal = ponto, vírgula = milhar
            $s = str_replace(',', '', $s);
        }
    } elseif ($posVirgula !== false) {
        // só vírgula -> decimal
        $s = str_replace('.', '', $s); // se tiver pontos, trata como milhar
        $s = str_replace(',', '.', $s);
    } else {
        // só ponto (ou nenhum) -> ponto é decimal (não remove)
        // só remove separadores de milhar raros tipo "1 234.56" (já tiramos espaço acima)
    }

    // remove qualquer coisa que não seja número, sinal e ponto
    $s = preg_replace('/[^0-9\.\-]/', '', $s) ?? '0';

    $n = (float)$s;
    return $n < 0 ? 0.0 : $n;
}

try {
    $in = ler_json_do_corpo();

    $id_atividade = (int)($in['id_atividade'] ?? 0);
    $titulo = trim((string)($in['titulo'] ?? ''));
    $descricao = isset($in['descricao']) ? (string)$in['descricao'] : null;
    $dificuldade = trim((string)($in['dificuldade'] ?? 'media'));
    $status = trim((string)($in['status'] ?? 'aberta'));
    $estimativa_float = normalizar_estimativa_horas($in['estimativa_horas'] ?? 0);

    $ids_usuarios = $in['ids_usuarios'] ?? [];
    if (!is_array($ids_usuarios)) $ids_usuarios = [];

    if ($id_atividade <= 0) responder_json(false, 'id_atividade inválido.', null, 400);
    if ($titulo === '' || mb_strlen($titulo) < 3) responder_json(false, 'Título inválido (mínimo 3 caracteres).', null, 400);
    if (!dificuldade_valida($dificuldade)) responder_json(false, 'Dificuldade inválida.', null, 400);
    if (!status_valido($status)) responder_json(false, 'Status inválido.', null, 400);

    // DECIMAL(6,2) => máximo 9999.99
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

    // existe atividade?
    $stE = $pdo->prepare("SELECT id_atividade FROM atividades WHERE id_atividade = :id LIMIT 1");
    $stE->execute([':id' => $id_atividade]);
    if (!$stE->fetchColumn()) {
        $pdo->rollBack();
        responder_json(false, 'Atividade não encontrada.', ['id_atividade' => $id_atividade], 404);
    }

    // valida usuários (evita FK quebrar)
    $placeholders = implode(',', array_fill(0, count($ids_validos), '?'));
    $stU = $pdo->prepare("SELECT id_usuario FROM usuarios WHERE id_usuario IN ($placeholders)");
    $stU->execute($ids_validos);
    $encontrados = $stU->fetchAll(PDO::FETCH_COLUMN) ?: [];
    $encontrados = array_map('intval', $encontrados);

    if (count($encontrados) < 1) {
        $pdo->rollBack();
        responder_json(false, 'Nenhum usuário válido encontrado.', null, 400);
    }

    // atualiza atividade
    $stUp = $pdo->prepare("
        UPDATE atividades
        SET titulo = :titulo,
            descricao = :descricao,
            dificuldade = :dificuldade,
            estimativa_horas = :estimativa_horas,
            status = :status
        WHERE id_atividade = :id
    ");
    $stUp->execute([
        ':titulo' => $titulo,
        ':descricao' => ($descricao !== null && trim((string)$descricao) !== '') ? $descricao : null,
        ':dificuldade' => $dificuldade,
        ':estimativa_horas' => number_format($estimativa_float, 2, '.', ''),
        ':status' => $status,
        ':id' => $id_atividade,
    ]);

    // refaz vínculos
    $stDel = $pdo->prepare("DELETE FROM atividades_usuarios WHERE id_atividade = :id");
    $stDel->execute([':id' => $id_atividade]);

    $stIns = $pdo->prepare("
        INSERT INTO atividades_usuarios (id_atividade, id_usuario)
        VALUES (:id_atividade, :id_usuario)
        ON DUPLICATE KEY UPDATE atribuida_em = atribuida_em
    ");

    foreach ($encontrados as $id_usuario) {
        $stIns->execute([
            ':id_atividade' => $id_atividade,
            ':id_usuario' => (int)$id_usuario,
        ]);
    }

    $pdo->commit();

    responder_json(true, 'Atividade editada.', [
        'id_atividade' => $id_atividade,
        'titulo' => $titulo,
        'descricao' => $descricao,
        'dificuldade' => $dificuldade,
        'estimativa_horas' => number_format($estimativa_float, 2, '.', ''),
        'status' => $status,
        'ids_usuarios' => $encontrados,
    ], 200);
} catch (Throwable $e) {
    try {
        if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) $pdo->rollBack();
    } catch (Throwable $t) { /* ignore */
    }

    $dados = null;
    if (function_exists('debug_ativo') && debug_ativo()) {
        $dados = [
            'erro' => $e->getMessage(),
            'arquivo' => $e->getFile(),
            'linha' => $e->getLine(),
        ];
    }

    responder_json(false, 'falha ao editar atividade', $dados, 500);
}
