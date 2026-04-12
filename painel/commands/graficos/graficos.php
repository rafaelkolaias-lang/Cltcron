<?php
declare(strict_types=1);

require_once __DIR__ . '/../_comum/auth.php';
verificar_sessao_painel();

header('Content-Type: application/json; charset=utf-8');
date_default_timezone_set('America/Sao_Paulo');

$caminho_conexao = __DIR__ . '/../conexao/conexao.php';
if (file_exists($caminho_conexao)) {
    require_once $caminho_conexao;
}

function graficos_responder_json(bool $ok, string $mensagem, $dados = null, int $codigo_http = 200): void
{
    http_response_code($codigo_http);
    echo json_encode(
        [
            'ok' => $ok,
            'mensagem' => $mensagem,
            'dados' => $dados,
        ],
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
    );
    exit;
}

function graficos_ler_corpo_json(): array
{
    $conteudo = (string) file_get_contents('php://input');
    if ($conteudo === '') {
        return [];
    }

    $decodificado = json_decode($conteudo, true);
    return is_array($decodificado) ? $decodificado : [];
}

function graficos_obter_parametro(array $origem, string $chave, $padrao = null)
{
    return array_key_exists($chave, $origem) ? $origem[$chave] : $padrao;
}

function graficos_normalizar_texto($valor, int $maximo = 180): string
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '') {
        return '';
    }

    if (mb_strlen($texto) > $maximo) {
        $texto = mb_substr($texto, 0, $maximo);
    }

    return $texto;
}

function graficos_normalizar_lista_array($valor, int $max_itens = 200, int $max_item = 180): array
{
    if (!is_array($valor)) {
        return [];
    }

    $unicos = [];
    foreach ($valor as $item) {
        $item = graficos_normalizar_texto($item, $max_item);
        if ($item === '') {
            continue;
        }

        $unicos[$item] = true;
        if (count($unicos) >= $max_itens) {
            break;
        }
    }

    return array_keys($unicos);
}

function graficos_validar_data_yyyy_mm_dd($valor): ?string
{
    $texto = graficos_normalizar_texto($valor, 16);
    if ($texto === '') {
        return null;
    }

    $data = DateTime::createFromFormat('Y-m-d', $texto);
    if (!$data) {
        return null;
    }

    return $data->format('Y-m-d');
}

function graficos_obter_intervalo_datas(array $entrada): array
{
    $data_inicio = graficos_validar_data_yyyy_mm_dd(graficos_obter_parametro($entrada, 'data_inicio', ''));
    $data_fim = graficos_validar_data_yyyy_mm_dd(graficos_obter_parametro($entrada, 'data_fim', ''));

    $hoje = new DateTime('today');

    if (!$data_fim) {
        $data_fim = $hoje->format('Y-m-d');
    }

    if (!$data_inicio) {
        $inicio = new DateTime($data_fim . ' 00:00:00');
        $inicio->modify('-6 days');
        $data_inicio = $inicio->format('Y-m-d');
    }

    $inicio_em = new DateTime($data_inicio . ' 00:00:00');
    $fim_exclusivo = new DateTime($data_fim . ' 00:00:00');
    $fim_exclusivo->modify('+1 day');

    return [
        'data_inicio' => $data_inicio,
        'data_fim' => $data_fim,
        'inicio_em' => $inicio_em->format('Y-m-d H:i:s'),
        'fim_exclusivo_em' => $fim_exclusivo->format('Y-m-d H:i:s'),
    ];
}

function graficos_obter_conexao_pdo(): PDO
{
    if (function_exists('obter_conexao_pdo')) {
        $pdo = obter_conexao_pdo();
        if ($pdo instanceof PDO) {
            return $pdo;
        }
    }

    if (isset($GLOBALS['pdo']) && $GLOBALS['pdo'] instanceof PDO) {
        return $GLOBALS['pdo'];
    }

    throw new RuntimeException('Conexão PDO não encontrada.');
}

function graficos_montar_in(string $prefixo, array $itens, array &$parametros): string
{
    $marcadores = [];

    foreach ($itens as $indice => $valor) {
        $chave = ':' . $prefixo . '_' . $indice;
        $marcadores[] = $chave;
        $parametros[$chave] = $valor;
    }

    return '(' . implode(',', $marcadores) . ')';
}

function graficos_montar_nome_usuario(array $linha): string
{
    $nome = graficos_normalizar_texto($linha['nome_exibicao'] ?? '', 120);
    if ($nome !== '') {
        return $nome;
    }

    return graficos_normalizar_texto($linha['user_id'] ?? '—', 120);
}

function graficos_decodificar_apps_json($valor): array
{
    $texto = trim((string)($valor ?? ''));
    if ($texto === '') {
        return [];
    }

    $dados = json_decode($texto, true);
    return is_array($dados) ? $dados : [];
}

function graficos_obter_status_atuais(PDO $conexao_banco, array $usuarios_filtro): array
{
    $parametros = [];
    $where = '1=1';

    if (!empty($usuarios_filtro)) {
        $in = graficos_montar_in('usuario_status', $usuarios_filtro, $parametros);
        $where .= " AND usa.user_id IN {$in}";
    }

    $sql = "
        SELECT
            usa.user_id,
            u.nome_exibicao,
            usa.situacao,
            usa.atividade,
            usa.inicio_em,
            usa.ultimo_em,
            usa.segundos_pausado,
            usa.apps_json
        FROM usuarios_status_atual usa
        INNER JOIN usuarios u ON u.user_id = usa.user_id
        WHERE {$where}
        ORDER BY u.nome_exibicao ASC, usa.user_id ASC
    ";

    try {
        $comando = $conexao_banco->prepare($sql);
        $comando->execute($parametros);
        return $comando->fetchAll(PDO::FETCH_ASSOC) ?: [];
    } catch (Throwable $erro) {
        return [];
    }
}

function graficos_obter_mapa_tempos_relatorio(PDO $conexao_banco, string $where_relatorios, array $parametros_relatorios): array
{
    $sql = "
        SELECT
            cr.user_id,
            SUM(cr.segundos_trabalhando) AS segundos_trabalhando,
            SUM(cr.segundos_ocioso) AS segundos_ocioso,
            SUM(cr.segundos_pausado) AS segundos_pausado
        FROM cronometro_relatorios cr
        WHERE {$where_relatorios}
        GROUP BY cr.user_id
    ";

    $cmd = $conexao_banco->prepare($sql);
    $cmd->execute($parametros_relatorios);
    $linhas = $cmd->fetchAll(PDO::FETCH_ASSOC) ?: [];

    $mapa = [];
    foreach ($linhas as $linha) {
        $mapa[(string)$linha['user_id']] = [
            'segundos_trabalhando' => (int)($linha['segundos_trabalhando'] ?? 0),
            'segundos_ocioso' => (int)($linha['segundos_ocioso'] ?? 0),
            'segundos_pausado' => (int)($linha['segundos_pausado'] ?? 0),
        ];
    }

    return $mapa;
}

function graficos_obter_usuarios_base(PDO $conexao_banco, array $usuarios_filtro): array
{
    $parametros = [];
    $where = '1=1';

    if (!empty($usuarios_filtro)) {
        $in = graficos_montar_in('usuario_base', $usuarios_filtro, $parametros);
        $where .= " AND u.user_id IN {$in}";
    }

    $sql = "
        SELECT
            u.user_id,
            u.nome_exibicao,
            u.status_conta,
            u.nivel,
            u.valor_hora
        FROM usuarios u
        WHERE {$where}
        ORDER BY u.nome_exibicao ASC, u.user_id ASC
    ";

    $cmd = $conexao_banco->prepare($sql);
    $cmd->execute($parametros);
    return $cmd->fetchAll(PDO::FETCH_ASSOC) ?: [];
}

function graficos_garantir_usuario(array &$usuarios, string $user_id, array $linha = [], array $mapa_tempos = []): void
{
    if ($user_id === '') {
        return;
    }

    if (!isset($usuarios[$user_id])) {
        $tempos = $mapa_tempos[$user_id] ?? ['segundos_trabalhando' => 0, 'segundos_ocioso' => 0, 'segundos_pausado' => 0];
        $usuarios[$user_id] = [
            'user_id' => $user_id,
            'nome_exibicao' => graficos_montar_nome_usuario($linha),
            'status_conta' => graficos_normalizar_texto($linha['status_conta'] ?? '', 30),
            'nivel' => graficos_normalizar_texto($linha['nivel'] ?? '', 30),
            'valor_hora' => (float)($linha['valor_hora'] ?? 0),
            'status_atual' => 'sem_status',
            'atividade_atual' => '',
            'status_desde_em' => '',
            'status_ultimo_em' => '',
            'segundos_pausado_atual' => 0,
            'segundos_trabalhando_total' => (int)($tempos['segundos_trabalhando'] ?? 0),
            'segundos_ocioso_total' => (int)($tempos['segundos_ocioso'] ?? 0),
            'segundos_pausado_total' => (int)($tempos['segundos_pausado'] ?? 0),
            'apps_abertos_agora' => [],
            'apps_resumo' => [],
            'periodos_foco' => [],
            'periodos_abertos' => [],
            'segundos_total_apps' => 0,
            'segundos_total_foco' => 0,
            'segundos_total_segundo_plano' => 0,
            'quantidade_apps_usados' => 0,
            'quantidade_apps_abertos_agora' => 0,
        ];
    }
}

try {
    $entrada_json = graficos_ler_corpo_json();
    $entrada = array_merge($_GET ?? [], $_POST ?? [], $entrada_json);

    $acao = graficos_normalizar_texto(graficos_obter_parametro($entrada, 'acao', 'meta'), 40);
    if ($acao === '') {
        $acao = 'meta';
    }

    $conexao_banco = graficos_obter_conexao_pdo();
    $intervalo = graficos_obter_intervalo_datas($entrada);

    $usuarios_filtro = graficos_normalizar_lista_array(graficos_obter_parametro($entrada, 'usuarios', []), 200, 60);
    $apps_filtro = graficos_normalizar_lista_array(graficos_obter_parametro($entrada, 'apps', []), 300, 180);

    if ($acao === 'meta') {
        $cmdUsuarios = $conexao_banco->query("
            SELECT user_id, nome_exibicao, status_conta, nivel
            FROM usuarios
            ORDER BY nome_exibicao ASC, user_id ASC
        ");
        $usuarios = $cmdUsuarios ? ($cmdUsuarios->fetchAll(PDO::FETCH_ASSOC) ?: []) : [];

        $cmdApps = $conexao_banco->query("
            SELECT nome_app
            FROM (
                SELECT DISTINCT nome_app FROM cronometro_apps_intervalos
                UNION
                SELECT DISTINCT nome_app FROM cronometro_foco_janela
            ) apps
            WHERE nome_app IS NOT NULL
              AND nome_app <> ''
            ORDER BY nome_app ASC
        ");
        $apps_linhas = $cmdApps ? ($cmdApps->fetchAll(PDO::FETCH_ASSOC) ?: []) : [];
        $apps = array_values(array_filter(array_map(
            static fn(array $linha): string => (string)($linha['nome_app'] ?? ''),
            $apps_linhas
        )));

        graficos_responder_json(true, 'Meta carregada.', [
            'atualizado_em' => (new DateTime())->format('Y-m-d H:i:s'),
            'usuarios' => $usuarios,
            'apps' => $apps,
        ]);
    }

    if ($acao !== 'painel') {
        graficos_responder_json(false, 'Ação inválida.', ['acao' => $acao], 400);
    }

    $parametros_intervalos = [
        ':inicio_em' => $intervalo['inicio_em'],
        ':fim_exclusivo_em' => $intervalo['fim_exclusivo_em'],
    ];
    $where_intervalos = "ai.inicio_em >= :inicio_em AND ai.inicio_em < :fim_exclusivo_em";

    if (!empty($usuarios_filtro)) {
        $in = graficos_montar_in('usuario_intervalo', $usuarios_filtro, $parametros_intervalos);
        $where_intervalos .= " AND ai.user_id IN {$in}";
    }

    if (!empty($apps_filtro)) {
        $in = graficos_montar_in('app_intervalo', $apps_filtro, $parametros_intervalos);
        $where_intervalos .= " AND ai.nome_app IN {$in}";
    }

    $parametros_foco = [
        ':inicio_em' => $intervalo['inicio_em'],
        ':fim_exclusivo_em' => $intervalo['fim_exclusivo_em'],
    ];
    $where_foco = "fj.inicio_em >= :inicio_em AND fj.inicio_em < :fim_exclusivo_em";

    if (!empty($usuarios_filtro)) {
        $in = graficos_montar_in('usuario_foco', $usuarios_filtro, $parametros_foco);
        $where_foco .= " AND fj.user_id IN {$in}";
    }

    if (!empty($apps_filtro)) {
        $in = graficos_montar_in('app_foco', $apps_filtro, $parametros_foco);
        $where_foco .= " AND fj.nome_app IN {$in}";
    }

    $parametros_relatorios = [
        ':data_inicio' => $intervalo['data_inicio'],
        ':data_fim'    => $intervalo['data_fim'],
        ':inicio_em'   => $intervalo['inicio_em'],
        ':fim_exclusivo_em' => $intervalo['fim_exclusivo_em'],
    ];
    // Usa referencia_data quando disponível (relatórios novos); fallback para criado_em (relatórios antigos sem a coluna)
    $where_relatorios = "((cr.referencia_data IS NOT NULL AND cr.referencia_data BETWEEN :data_inicio AND :data_fim)
        OR (cr.referencia_data IS NULL AND cr.criado_em >= :inicio_em AND cr.criado_em < :fim_exclusivo_em))";

    if (!empty($usuarios_filtro)) {
        $in = graficos_montar_in('usuario_relatorio', $usuarios_filtro, $parametros_relatorios);
        $where_relatorios .= " AND cr.user_id IN {$in}";
    }

    $usuarios_base = graficos_obter_usuarios_base($conexao_banco, $usuarios_filtro);
    $mapa_tempos = graficos_obter_mapa_tempos_relatorio($conexao_banco, $where_relatorios, $parametros_relatorios);
    $linhas_status_atuais = graficos_obter_status_atuais($conexao_banco, $usuarios_filtro);

    $usuarios = [];

    foreach ($usuarios_base as $linha_usuario_base) {
        $user_id = (string)($linha_usuario_base['user_id'] ?? '');
        graficos_garantir_usuario($usuarios, $user_id, $linha_usuario_base, $mapa_tempos);
    }

    foreach ($linhas_status_atuais as $linha_status) {
        $user_id = (string)($linha_status['user_id'] ?? '');
        if ($user_id === '') {
            continue;
        }

        graficos_garantir_usuario($usuarios, $user_id, $linha_status, $mapa_tempos);

        $apps_json = graficos_decodificar_apps_json($linha_status['apps_json'] ?? null);
        $em_foco = is_array($apps_json['em_foco'] ?? null) ? $apps_json['em_foco'] : [];

        // v4.9 — timeout de inatividade: se o último heartbeat tem >3 min, força "pausado"
        $status_raw = graficos_normalizar_texto($linha_status['situacao'] ?? 'sem_status', 40) ?: 'sem_status';
        $ultimo_em_str = (string)($linha_status['ultimo_em'] ?? '');
        if ($ultimo_em_str !== '' && $status_raw !== 'pausado' && $status_raw !== 'sem_status') {
            try {
                $dt_ultimo = new DateTime($ultimo_em_str);
                $segundos_desde_ultimo = time() - $dt_ultimo->getTimestamp();
                if ($segundos_desde_ultimo > 180) {
                    $status_raw = 'pausado';
                }
            } catch (Exception $e) {
                // data inválida — mantém status original
            }
        }
        $usuarios[$user_id]['status_atual'] = $status_raw;
        $usuarios[$user_id]['atividade_atual'] = graficos_normalizar_texto($linha_status['atividade'] ?? '', 255);
        $usuarios[$user_id]['status_desde_em'] = (string)($linha_status['inicio_em'] ?? '');
        $usuarios[$user_id]['status_ultimo_em'] = (string)($linha_status['ultimo_em'] ?? '');
        $usuarios[$user_id]['segundos_pausado_atual'] = (int)($linha_status['segundos_pausado'] ?? 0);

        if (!empty($em_foco)) {
            $nome_app_em_foco = graficos_normalizar_texto($em_foco['nome_app'] ?? '', 180);
            $titulo_em_foco = graficos_normalizar_texto($em_foco['titulo_janela'] ?? '', 255);

            if ($nome_app_em_foco !== '' && $nome_app_em_foco !== 'desconhecido') {
                $ja_tem = false;
                foreach ($usuarios[$user_id]['apps_abertos_agora'] as $app_aberto) {
                    if (
                        (string)($app_aberto['nome_app'] ?? '') === $nome_app_em_foco
                        && (string)($app_aberto['titulo_janela'] ?? '') === $titulo_em_foco
                    ) {
                        $ja_tem = true;
                        break;
                    }
                }

                if (!$ja_tem) {
                    $usuarios[$user_id]['apps_abertos_agora'][] = [
                        'nome_app' => $nome_app_em_foco,
                        'titulo_janela' => $titulo_em_foco,
                        'inicio_em' => (string)($linha_status['inicio_em'] ?? ''),
                    ];
                }
            }
        }
    }

    $sqlResumoApps = "
        SELECT
            ai.user_id,
            u.nome_exibicao,
            ai.nome_app,
            SUM(ai.segundos_em_foco) AS segundos_em_foco,
            SUM(ai.segundos_segundo_plano) AS segundos_segundo_plano,
            SUM(ai.segundos_em_foco + ai.segundos_segundo_plano) AS segundos_total_aberto,
            MIN(ai.inicio_em) AS primeiro_uso_em,
            MAX(COALESCE(ai.fim_em, ai.ultima_atualizacao_em, ai.inicio_em)) AS ultimo_uso_em
        FROM cronometro_apps_intervalos ai
        INNER JOIN usuarios u ON u.user_id = ai.user_id
        WHERE {$where_intervalos}
        GROUP BY ai.user_id, u.nome_exibicao, ai.nome_app
        ORDER BY u.nome_exibicao ASC, segundos_total_aberto DESC, ai.nome_app ASC
    ";
    $cmdResumoApps = $conexao_banco->prepare($sqlResumoApps);
    $cmdResumoApps->execute($parametros_intervalos);
    $linhasResumoApps = $cmdResumoApps->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhasResumoApps as $linha) {
        $user_id = (string)($linha['user_id'] ?? '');
        if ($user_id === '') {
            continue;
        }

        graficos_garantir_usuario($usuarios, $user_id, $linha, $mapa_tempos);

        $segundos_total_aberto = (int)($linha['segundos_total_aberto'] ?? 0);
        $segundos_em_foco = (int)($linha['segundos_em_foco'] ?? 0);
        $segundos_segundo_plano = (int)($linha['segundos_segundo_plano'] ?? 0);

        $usuarios[$user_id]['apps_resumo'][] = [
            'nome_app' => (string)($linha['nome_app'] ?? '—'),
            'segundos_total_aberto' => $segundos_total_aberto,
            'segundos_em_foco' => $segundos_em_foco,
            'segundos_segundo_plano' => $segundos_segundo_plano,
            'primeiro_uso_em' => (string)($linha['primeiro_uso_em'] ?? ''),
            'ultimo_uso_em' => (string)($linha['ultimo_uso_em'] ?? ''),
        ];

        $usuarios[$user_id]['segundos_total_apps'] += $segundos_total_aberto;
        $usuarios[$user_id]['segundos_total_foco'] += $segundos_em_foco;
        $usuarios[$user_id]['segundos_total_segundo_plano'] += $segundos_segundo_plano;
    }

    $sqlPeriodos = "
        SELECT
            fj.id_foco,
            fj.id_sessao,
            fj.user_id,
            u.nome_exibicao,
            fj.nome_app,
            fj.titulo_janela,
            fj.inicio_em,
            CASE
                WHEN fj.fim_em IS NOT NULL THEN fj.fim_em
                WHEN s.ultimo_em IS NOT NULL AND s.ultimo_em < NOW() - INTERVAL 5 MINUTE THEN s.ultimo_em
                ELSE NULL
            END AS fim_em,
            TIMESTAMPDIFF(
                SECOND,
                fj.inicio_em,
                CASE
                    WHEN fj.fim_em IS NOT NULL THEN fj.fim_em
                    WHEN s.ultimo_em IS NOT NULL AND s.ultimo_em < NOW() - INTERVAL 5 MINUTE THEN s.ultimo_em
                    ELSE NOW()
                END
            ) AS segundos_periodo,
            CASE
                WHEN fj.fim_em IS NOT NULL THEN 0
                WHEN s.ultimo_em IS NOT NULL AND s.ultimo_em < NOW() - INTERVAL 5 MINUTE THEN 0
                ELSE 1
            END AS aberto_agora
        FROM cronometro_foco_janela fj
        INNER JOIN usuarios u ON u.user_id = fj.user_id
        LEFT JOIN usuarios_status_atual s ON s.user_id = fj.user_id
        WHERE {$where_foco}
        ORDER BY u.nome_exibicao ASC, fj.inicio_em DESC
        LIMIT 50000
    ";
    $cmdPeriodos = $conexao_banco->prepare($sqlPeriodos);
    $cmdPeriodos->execute($parametros_foco);
    $linhasPeriodos = $cmdPeriodos->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhasPeriodos as $linha) {
        $user_id = (string)($linha['user_id'] ?? '');
        if ($user_id === '') {
            continue;
        }

        graficos_garantir_usuario($usuarios, $user_id, $linha, $mapa_tempos);

        $usuarios[$user_id]['periodos_foco'][] = [
            'id_foco' => (int)($linha['id_foco'] ?? 0),
            'id_sessao' => (int)($linha['id_sessao'] ?? 0),
            'nome_app' => (string)($linha['nome_app'] ?? '—'),
            'titulo_janela' => (string)($linha['titulo_janela'] ?? ''),
            'inicio_em' => (string)($linha['inicio_em'] ?? ''),
            'fim_em' => (string)($linha['fim_em'] ?? ''),
            'segundos_periodo' => max(0, (int)($linha['segundos_periodo'] ?? 0)),
            'aberto_agora' => (int)($linha['aberto_agora'] ?? 0) === 1,
        ];
    }

    // ── Períodos de todos os apps abertos (foco + 2.º plano) ──────────────────
    $sqlPeriodosAbertos = "
        SELECT
            ai.user_id,
            ai.nome_app,
            ai.inicio_em,
            CASE
                WHEN ai.fim_em IS NOT NULL THEN ai.fim_em
                WHEN ai.ultima_atualizacao_em IS NOT NULL THEN ai.ultima_atualizacao_em
                WHEN s.ultimo_em IS NOT NULL AND s.ultimo_em < NOW() - INTERVAL 5 MINUTE THEN s.ultimo_em
                ELSE NOW()
            END AS fim_em,
            ai.segundos_em_foco,
            ai.segundos_segundo_plano,
            (ai.segundos_em_foco + ai.segundos_segundo_plano) AS segundos_total
        FROM cronometro_apps_intervalos ai
        INNER JOIN usuarios u ON u.user_id = ai.user_id
        LEFT JOIN usuarios_status_atual s ON s.user_id = ai.user_id
        WHERE {$where_intervalos}
        ORDER BY ai.user_id ASC, ai.inicio_em DESC
        LIMIT 50000
    ";
    $cmdPeriodosAbertos = $conexao_banco->prepare($sqlPeriodosAbertos);
    $cmdPeriodosAbertos->execute($parametros_intervalos);
    foreach ($cmdPeriodosAbertos->fetchAll(PDO::FETCH_ASSOC) ?: [] as $linha) {
        $user_id = (string)($linha['user_id'] ?? '');
        if ($user_id === '' || !isset($usuarios[$user_id])) {
            continue;
        }
        $usuarios[$user_id]['periodos_abertos'][] = [
            'nome_app'            => (string)($linha['nome_app'] ?? '—'),
            'inicio_em'           => (string)($linha['inicio_em'] ?? ''),
            'fim_em'              => (string)($linha['fim_em'] ?? ''),
            'segundos_em_foco'    => max(0, (int)($linha['segundos_em_foco'] ?? 0)),
            'segundos_segundo_plano' => max(0, (int)($linha['segundos_segundo_plano'] ?? 0)),
            'segundos_total'      => max(0, (int)($linha['segundos_total'] ?? 0)),
        ];
    }

    $parametros_abertos = [];
    $where_abertos = "fj.fim_em IS NULL";

    if (!empty($usuarios_filtro)) {
        $in = graficos_montar_in('usuario_aberto', $usuarios_filtro, $parametros_abertos);
        $where_abertos .= " AND fj.user_id IN {$in}";
    }

    if (!empty($apps_filtro)) {
        $in = graficos_montar_in('app_aberto', $apps_filtro, $parametros_abertos);
        $where_abertos .= " AND fj.nome_app IN {$in}";
    }

    $sqlAbertosAgora = "
        SELECT
            fj.user_id,
            u.nome_exibicao,
            fj.nome_app,
            fj.titulo_janela,
            fj.inicio_em
        FROM cronometro_foco_janela fj
        INNER JOIN usuarios u ON u.user_id = fj.user_id
        INNER JOIN cronometro_sessoes cs ON cs.id_sessao = fj.id_sessao AND cs.finalizado_em IS NULL
        WHERE {$where_abertos}
          AND fj.nome_app <> 'desconhecido'
        ORDER BY u.nome_exibicao ASC, fj.inicio_em DESC
    ";
    $cmdAbertos = $conexao_banco->prepare($sqlAbertosAgora);
    $cmdAbertos->execute($parametros_abertos);
    $linhasAbertosAgora = $cmdAbertos->fetchAll(PDO::FETCH_ASSOC) ?: [];

    foreach ($linhasAbertosAgora as $linha) {
        $user_id = (string)($linha['user_id'] ?? '');
        if ($user_id === '') {
            continue;
        }

        graficos_garantir_usuario($usuarios, $user_id, $linha, $mapa_tempos);

        $usuarios[$user_id]['apps_abertos_agora'][] = [
            'nome_app' => (string)($linha['nome_app'] ?? '—'),
            'titulo_janela' => (string)($linha['titulo_janela'] ?? ''),
            'inicio_em' => (string)($linha['inicio_em'] ?? ''),
        ];
    }

    $contagem_status_atual = [
        'trabalhando' => 0,
        'ocioso' => 0,
        'pausado' => 0,
        'sem_status' => 0,
    ];

    foreach ($usuarios as &$usuario) {
        $apps_abertos_normalizados = [];
        $assinaturas = [];

        foreach ($usuario['apps_abertos_agora'] as $app_aberto) {
            $assinatura = (string)($app_aberto['nome_app'] ?? '') . '|' . (string)($app_aberto['titulo_janela'] ?? '');
            if (isset($assinaturas[$assinatura])) {
                continue;
            }
            $assinaturas[$assinatura] = true;
            $apps_abertos_normalizados[] = $app_aberto;
        }

        $usuario['apps_abertos_agora'] = $apps_abertos_normalizados;

        usort($usuario['apps_resumo'], static function (array $a, array $b): int {
            return $b['segundos_total_aberto'] <=> $a['segundos_total_aberto'];
        });

        usort($usuario['periodos_foco'], static function (array $a, array $b): int {
            return strcmp((string)$b['inicio_em'], (string)$a['inicio_em']);
        });

        usort($usuario['apps_abertos_agora'], static function (array $a, array $b): int {
            return strcmp((string)$b['inicio_em'], (string)$a['inicio_em']);
        });

        $usuario['quantidade_apps_usados'] = count($usuario['apps_resumo']);
        $usuario['quantidade_apps_abertos_agora'] = count($usuario['apps_abertos_agora']);

        $primeiro_app = $usuario['apps_resumo'][0] ?? null;
        $usuario['app_principal'] = $primeiro_app ? (string)($primeiro_app['nome_app'] ?? '') : '';

        $status_atual = (string)($usuario['status_atual'] ?? 'sem_status');
        if (!isset($contagem_status_atual[$status_atual])) {
            $contagem_status_atual[$status_atual] = 0;
        }
        $contagem_status_atual[$status_atual]++;
    }
    unset($usuario);

    usort($usuarios, static function (array $a, array $b): int {
        return strcmp((string)$a['nome_exibicao'], (string)$b['nome_exibicao']);
    });

    $resumo_geral = [
        'usuarios_com_dados' => count($usuarios),
        'apps_abertos_agora_total' => array_sum(array_map(
            static fn(array $u): int => (int)($u['quantidade_apps_abertos_agora'] ?? 0),
            $usuarios
        )),
        'segundos_trabalhando_total' => array_sum(array_map(
            static fn(array $u): int => (int)($u['segundos_trabalhando_total'] ?? 0),
            $usuarios
        )),
        'segundos_ocioso_total' => array_sum(array_map(
            static fn(array $u): int => (int)($u['segundos_ocioso_total'] ?? 0),
            $usuarios
        )),
        'segundos_pausado_total' => array_sum(array_map(
            static fn(array $u): int => (int)($u['segundos_pausado_total'] ?? 0),
            $usuarios
        )),
        'segundos_total_apps' => array_sum(array_map(
            static fn(array $u): int => (int)($u['segundos_total_apps'] ?? 0),
            $usuarios
        )),
        'segundos_total_foco' => array_sum(array_map(
            static fn(array $u): int => (int)($u['segundos_total_foco'] ?? 0),
            $usuarios
        )),
        'segundos_total_segundo_plano' => array_sum(array_map(
            static fn(array $u): int => (int)($u['segundos_total_segundo_plano'] ?? 0),
            $usuarios
        )),
        'status_atual' => $contagem_status_atual,
    ];

    graficos_responder_json(true, 'Painel simplificado carregado.', [
        'atualizado_em' => (new DateTime())->format('Y-m-d H:i:s'),
        'intervalo' => $intervalo,
        'resumo_geral' => $resumo_geral,
        'usuarios' => $usuarios,
    ]);
} catch (Throwable $e) {
    graficos_responder_json(false, 'Erro no servidor.', [
        'erro' => $e->getMessage(),
    ], 500);
}