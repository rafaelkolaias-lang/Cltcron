<?php
declare(strict_types=1);

/**
 * Helpers compartilhados de upsert cifrado de credenciais por usuário/modelo.
 *
 * Usado por:
 *   - credenciais/salvar_valor.php (gravação manual, individual ou global)
 *   - usuarios/criar.php (herança automática de credenciais globais para novos usuários)
 *
 * Regras invioláveis:
 *   - NUNCA reutilizar o mesmo nonce entre usuários — cada upsert gera nonce novo.
 *   - NUNCA logar/retornar valor puro.
 */

require_once __DIR__ . '/cripto.php';

/**
 * Faz upsert cifrado de uma credencial para um único usuário.
 *
 * O statement preparado é compartilhado entre chamadas para evitar custo de re-prepare
 * em laços (ex.: aplicar uma credencial global a N usuários).
 *
 * @return array  ['cipher_len' => int, 'nonce_len' => int]  — só metadados, nunca o valor.
 */
function upsert_credencial_usuario_cifrada(PDO $pdo, PDOStatement $stmt_upsert, int $id_modelo, string $user_id, string $valor_puro, string $mascara_parcial): array
{
    $cif = cifrar_segredo($valor_puro);
    $stmt_upsert->bindValue(1, $id_modelo, PDO::PARAM_INT);
    $stmt_upsert->bindValue(2, $user_id);
    $stmt_upsert->bindValue(3, $mascara_parcial);
    $stmt_upsert->bindValue(4, $cif['cipher'], PDO::PARAM_LOB);
    $stmt_upsert->bindValue(5, $cif['nonce'],  PDO::PARAM_LOB);
    $stmt_upsert->bindValue(6, $cif['versao'], PDO::PARAM_INT);
    $stmt_upsert->execute();
    return [
        'cipher_len' => strlen($cif['cipher']),
        'nonce_len'  => strlen($cif['nonce']),
    ];
}

/**
 * Statement preparado padrão para upsert em credenciais_usuario.
 * Reaproveitar o mesmo statement quando aplicar a vários usuários.
 */
function preparar_stmt_upsert_credencial(PDO $pdo): PDOStatement
{
    $sql = "INSERT INTO credenciais_usuario
                (id_modelo, user_id, mascara_parcial, valor_cifrado, nonce, versao_chave, status)
            VALUES (?, ?, ?, ?, ?, ?, 'ativo')
            ON DUPLICATE KEY UPDATE
                mascara_parcial = VALUES(mascara_parcial),
                valor_cifrado   = VALUES(valor_cifrado),
                nonce           = VALUES(nonce),
                versao_chave    = VALUES(versao_chave),
                status          = 'ativo',
                atualizado_em   = CURRENT_TIMESTAMP";
    return $pdo->prepare($sql);
}

/**
 * Lista os modelos marcados como "herdar para novos usuários" e, para cada um,
 * pega uma linha-referência ATIVA de credenciais_usuario para servir de origem do
 * valor cifrado a ser propagado.
 *
 * Retorna lista de:
 *   ['id_modelo' => int, 'mascara_parcial' => string,
 *    'valor_cifrado' => bytes, 'nonce' => bytes, 'versao_chave' => int]
 *
 * Se um modelo está marcado como global mas não possui nenhuma credencial ativa
 * de referência, ele é ignorado silenciosamente (não há valor para herdar).
 */
function listar_credenciais_globais_para_herdar(PDO $pdo): array
{
    $sql = "SELECT cu.id_modelo, cu.mascara_parcial, cu.valor_cifrado, cu.nonce, cu.versao_chave
            FROM credenciais_modelos cm
            INNER JOIN credenciais_usuario cu ON cu.id_modelo = cm.id_modelo
            WHERE cm.aplicar_novos_usuarios = 1
              AND cm.status = 'ativo'
              AND cu.status = 'ativo'
              AND cu.id_credencial = (
                  SELECT MIN(cu2.id_credencial)
                  FROM credenciais_usuario cu2
                  WHERE cu2.id_modelo = cm.id_modelo AND cu2.status = 'ativo'
              )";
    $stm = $pdo->prepare($sql);
    $stm->execute();
    return $stm->fetchAll(PDO::FETCH_ASSOC);
}

/**
 * Para um novo usuário, herda todas as credenciais marcadas como globais
 * (aplicar_novos_usuarios=1). Para cada credencial herdada:
 *   - decifra o valor da linha-referência usando a chave mestra;
 *   - recifra com NONCE NOVO;
 *   - faz upsert para o novo usuário.
 *
 * Retorna a quantidade de credenciais herdadas com sucesso.
 *
 * Falhas individuais (ex.: MAC inválido em uma referência específica) são puladas
 * — não derrubam o cadastro do usuário, apenas saem do laço para o próximo modelo.
 */
function herdar_credenciais_globais_para_usuario(PDO $pdo, string $user_id): int
{
    $referencias = listar_credenciais_globais_para_herdar($pdo);
    if (!$referencias) {
        return 0;
    }

    $stmt_upsert = preparar_stmt_upsert_credencial($pdo);
    $herdadas = 0;

    foreach ($referencias as $ref) {
        try {
            $valor_puro = decifrar_segredo(
                (string)$ref['valor_cifrado'],
                (string)$ref['nonce'],
                (int)$ref['versao_chave']
            );
            upsert_credencial_usuario_cifrada(
                $pdo,
                $stmt_upsert,
                (int)$ref['id_modelo'],
                $user_id,
                $valor_puro,
                (string)$ref['mascara_parcial']
            );
            sodium_memzero($valor_puro);
            $herdadas++;
        } catch (Throwable $e) {
            // não loga valor; não derruba cadastro — segue para o próximo modelo
            continue;
        }
    }

    return $herdadas;
}
