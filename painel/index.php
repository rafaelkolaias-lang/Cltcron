<?php
require_once __DIR__ . '/commands/_comum/auth.php';
if (!esta_logado()) {
    header('Location: ./login.php');
    exit;
}
header('Content-Type: text/html; charset=utf-8');
?>
<!doctype html>
<html lang="pt-br">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel ADM · RK Produções Digitais</title>

  <link rel="icon" type="image/svg+xml" href="./img/favicon.svg">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="./css/painel.css?v=7" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"></script>
</head>

<body>
  <nav class="navbar navbar-expand-lg navbar-grafite sticky-top" aria-label="Navegação principal">
    <div class="container-fluid px-3">
      <a class="navbar-brand d-flex align-items-center gap-2 text-decoration-none me-3" href="#">
        <span class="rk-logo-icon" aria-hidden="true">
          <span class="rk-play">&#9654;</span>
        </span>
        <span class="rk-logo-texto">
          <span class="rk-sigla">RK</span><span class="rk-producoes">PRODUÇÕES</span>
        </span>
        <span class="badge badge-suave fw-normal small ms-1">ADM</span>
      </a>

      <button class="navbar-toggler border-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#navbarConteudo" aria-controls="navbarConteudo" aria-expanded="false" aria-label="Abrir menu">
        <span class="navbar-toggler-icon"></span>
      </button>

      <div class="collapse navbar-collapse" id="navbarConteudo">
        <ul class="navbar-nav me-auto gap-1" id="menuAbas">
          <li class="nav-item">
            <a class="nav-link active" href="#" data-aba="abaDashboard">Dashboard</a>
          </li>
          <li class="nav-item nav-hover-submenu">
            <a class="nav-link" href="#" data-aba="abaUsuarios">Usuários</a>
            <ul class="submenu-nav">
              <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalAdicionarUsuario">+ Adicionar Usuário</a></li>
            </ul>
          </li>
          <li class="nav-item nav-hover-submenu">
            <a class="nav-link" href="#" data-aba="abaAtividades">Canal</a>
            <ul class="submenu-nav">
              <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">+ Adicionar Canal</a></li>
            </ul>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" data-aba="abaGerenciarTarefas">Gerenciar Tarefas</a>
          </li>
          <li class="nav-item nav-hover-submenu">
            <a class="nav-link" href="#" data-aba="abaCredenciais">Credenciais e APIs</a>
            <ul class="submenu-nav">
              <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalGerenciarModelos">⚙ Gerenciar modelos</a></li>
            </ul>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" data-aba="abaRelatorio">Relatório</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" data-aba="abaAuditoria" id="linkAbaAuditoria" title="Auditoria de apps suspeitos"><span id="linkAbaAuditoriaIcone" class="d-none">🚨 </span>Auditoria</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" data-aba="abaMega" title="Configuração de upload obrigatório no MEGA">MEGA</a>
          </li>
        </ul>

        <div class="d-flex align-items-center gap-2 ms-2">
          <span class="texto-fraco small d-none d-xl-block" id="textoSubtitulo">Dashboard · visão geral</span>
          <button class="btn btn-sm btn-outline-light" type="button" id="botaoRecarregarAba" title="Recarregar aba atual">&#x21BB; Recarregar</button>
          <a href="./baixar_app.php" class="btn btn-sm btn-light">Baixar App</a>
          <a href="./logout.php" class="btn btn-sm btn-outline-danger" title="Sair do painel">Sair</a>
        </div>
      </div>
    </div>
  </nav>

  <div class="container-fluid">
    <div class="p-3 p-md-4">

        <section id="areaAlertas" aria-label="Mensagens do sistema"></section>

        <main aria-label="Conteúdo principal">

          <section id="abaDashboard" aria-label="Dashboard">
            <!-- Ações rápidas -->
            <div class="d-flex flex-wrap gap-2 mb-3">
              <button class="btn btn-sm btn-outline-light" type="button" data-bs-toggle="modal" data-bs-target="#modalAdicionarUsuario">+ Adicionar Usuário</button>
              <button class="btn btn-sm btn-outline-light" type="button" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">+ Adicionar Canal</button>
            </div>

            <div class="row g-3">
              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Usuários cadastrados</div>
                  <div class="display-6 fw-bold" id="numeroUsuarios">—</div>
                  <div class="texto-fraco small">Total no banco</div>
                </article>
              </div>

              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Contas ativas</div>
                  <div class="display-6 fw-bold" id="numeroUsuariosAtivos">—</div>
                  <div class="texto-fraco small">Status = ativa</div>
                </article>
              </div>

              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Última atualização</div>
                  <div class="fw-bold" id="textoUltimaAtualizacao">—</div>
                  <div class="texto-fraco small">Horário do navegador</div>
                </article>
              </div>
            </div>

            <!-- Gráficos + Visão da Equipe (unificados no Dashboard) -->
            <div id="areaGraficos" class="mt-3"></div>

          </section>

          <section id="abaUsuarios" class="d-none" aria-label="Usuários">
            <article class="cartao-grafite p-3">

              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Usuários</h2>
                  <span class="badge badge-suave" id="badgeUsuariosStatus">BANCO</span>
                </div>

                <div class="d-flex gap-2 align-items-center">
                  <div class="input-group campo-busca">
                    <span class="input-group-text bg-transparent text-white border-secondary">🔎</span>
                    <input id="entradaBuscaUsuarios" class="form-control bg-transparent text-white border-secondary"
                      placeholder="Buscar por usuário, nome ou nível...">
                  </div>

                  <button class="btn btn-light botao-mini" type="button" data-bs-toggle="modal" data-bs-target="#modalAdicionarUsuario">
                    + Adicionar
                  </button>
                </div>
              </div>

              <div class="table-responsive tabela-limite" style="max-height: 620px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width: 260px;">Usuário</th>
                      <th class="text-center" style="min-width: 140px;">Nível</th>
                      <th class="text-center" style="min-width: 120px;">R$/hora</th>
                      <th class="text-center" style="min-width: 140px;">Status</th>
                      <th class="text-center" style="min-width: 170px;">Atualizado</th>
                      <th class="text-end" style="min-width: 220px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyUsuarios">
                    <tr>
                      <td colspan="6" class="texto-fraco">Carregando…</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="texto-fraco small mt-2">
                Dica: clique em "Gestão" para editar dados, ativar/inativar e registrar pagamentos.
              </div>
            </article>
          </section>

          <div class="modal fade" id="modalAdicionarUsuario" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
              <div class="modal-content bg-dark text-white border-secondary">
                <div class="modal-header border-secondary">
                  <h5 class="modal-title">Adicionar usuário</h5>
                  <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>

                <div class="modal-body">
                  <div class="mb-2 texto-fraco small">
                    A chave de acesso será gerada automaticamente.
                  </div>

                  <label class="form-label texto-fraco">Usuário (user_id)</label>
                  <input id="entradaNovoUsuarioId" class="form-control bg-transparent text-white border-secondary" placeholder="ex: joao">

                  <div class="mt-2">
                    <label class="form-label texto-fraco">Nome (exibição)</label>
                    <input id="entradaNovoUsuarioNome" class="form-control bg-transparent text-white border-secondary" placeholder="ex: João da Silva">
                  </div>

                  <div class="row g-2 mt-2">
                    <div class="col-6">
                      <label class="form-label texto-fraco">Nível</label>
                      <select id="entradaNovoUsuarioNivel" class="form-select bg-transparent text-white border-secondary">
                        <option value="iniciante">Iniciante</option>
                        <option value="intermediario" selected>Intermediário</option>
                        <option value="avancado">Avançado</option>
                      </select>
                    </div>

                    <div class="col-6">
                      <label class="form-label texto-fraco">Valor por hora (R$)</label>
                      <input id="entradaNovoUsuarioValorHora" class="form-control bg-transparent text-white border-secondary" placeholder="ex: 35,00">
                    </div>
                  </div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="d-flex justify-content-between align-items-center">
                    <div>
                      <div class="texto-fraco small">Chave</div>
                      <div class="texto-mono fw-bold">Gerada ao salvar</div>
                    </div>
                  </div>
                </div>

                <div class="modal-footer border-secondary">
                  <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
                  <button type="button" class="btn btn-light" id="botaoConfirmarAdicionarUsuario">Salvar</button>
                </div>
              </div>
            </div>
          </div>

          <div id="abaGestaoUsuario" class="d-none" aria-label="Gestão do Usuário">

            <div class="d-flex align-items-center gap-3 mb-3">
              <button type="button" class="btn btn-outline-light btn-sm" id="botaoVoltarUsuarios">← Voltar</button>
              <div>
                <h2 class="h5 mb-0">Gestão do usuário</h2>
                <div class="texto-fraco small" id="textoGestaoSubtitulo">—</div>
              </div>
            </div>

            <!-- Alertas de auditoria (só renderiza se houver histórico) -->
            <article id="blocoAlertasAuditoria" class="cartao-grafite p-3 mb-3 d-none" style="border-left: 3px solid var(--bs-danger, #dc3545);">
              <div class="d-flex justify-content-between align-items-center mb-2">
                <div class="d-flex align-items-center gap-2">
                  <h6 class="mb-0">🚨 Alertas de Auditoria</h6>
                </div>
                <a href="#" class="small" data-aba="abaAuditoria" id="linkIrAuditoriaGestao">Ver aba Auditoria →</a>
              </div>
              <div id="alertasAuditoriaCorpo">
                <div class="texto-fraco small">—</div>
              </div>
            </article>

            <div class="row g-3">

              <!-- Coluna esquerda: dados do usuário -->
              <div class="col-12 col-lg-4">
                <article class="cartao-grafite p-3">

                  <div class="texto-fraco small">Usuário</div>
                  <div class="fw-semibold" id="textoGestaoUsuario">—</div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="texto-fraco small">Chave de acesso</div>
                  <div class="texto-mono fw-bold" id="textoGestaoChave">—</div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="d-flex justify-content-between align-items-center">
                    <div>
                      <div class="texto-fraco small">Status da conta</div>
                      <div class="fw-semibold" id="textoGestaoStatusConta">—</div>
                    </div>
                    <div class="form-check form-switch m-0">
                      <input class="form-check-input" type="checkbox" role="switch" id="switchGestaoAtiva">
                      <label class="form-check-label texto-fraco small" for="switchGestaoAtiva">Ativa</label>
                    </div>
                  </div>

                  <hr class="border-light opacity-10 my-3">

                  <div id="blocoGestaoVisual">
                    <div class="d-flex justify-content-between">
                      <div>
                        <div class="texto-fraco small">Nome</div>
                        <div class="fw-semibold" id="textoGestaoNome">—</div>
                      </div>
                      <div class="text-end">
                        <div class="texto-fraco small">Nível</div>
                        <div class="fw-semibold" id="textoGestaoNivel">—</div>
                      </div>
                    </div>

                    <div class="d-flex justify-content-between mt-2">
                      <div>
                        <div class="texto-fraco small">R$/hora</div>
                        <div class="fw-semibold" id="textoGestaoValorHora">—</div>
                      </div>
                    </div>

                    <div class="d-grid gap-2 mt-3">
                      <button type="button" class="btn btn-outline-light" id="botaoEditarDadosUsuario">Editar dados</button>
                    </div>
                  </div>

                  <div id="blocoGestaoEdicao" class="d-none">
                    <div class="mb-2">
                      <label class="form-label texto-fraco">Nome (exibição)</label>
                      <input id="entradaEditarNome" class="form-control bg-transparent text-white border-secondary" placeholder="ex: João da Silva">
                    </div>
                    <div class="row g-2">
                      <div class="col-6">
                        <label class="form-label texto-fraco">Nível</label>
                        <select id="entradaEditarNivel" class="form-select bg-transparent text-white border-secondary">
                          <option value="iniciante">Iniciante</option>
                          <option value="intermediario">Intermediário</option>
                          <option value="avancado">Avançado</option>
                        </select>
                      </div>
                      <div class="col-6">
                        <label class="form-label texto-fraco">Valor por hora (R$)</label>
                        <input id="entradaEditarValorHora" class="form-control bg-transparent text-white border-secondary" placeholder="ex: 35,00">
                      </div>
                    </div>
                    <div class="d-flex gap-2 mt-3">
                      <button type="button" class="btn btn-light flex-fill" id="botaoSalvarEdicaoUsuario">Salvar</button>
                      <button type="button" class="btn btn-outline-light flex-fill" id="botaoCancelarEdicaoUsuario">Cancelar</button>
                    </div>
                    <div class="texto-fraco small mt-2">Alterações são salvas no banco.</div>
                  </div>

                </article>

              </div>

              <!-- Coluna direita: resumo + pagamentos -->
              <div class="col-12 col-lg-8">

                <!-- Resumo para pagamento -->
                <article class="cartao-grafite p-3 mb-3" id="blocoResumoHorasPagamento">
                  <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                    <h6 class="mb-0">Resumo para pagamento</h6>
                    <div class="btn-group btn-group-sm" role="group" aria-label="Filtro de período">
                      <button type="button" class="btn btn-light botao-mini active" data-resumo-periodo="tudo">TUDO</button>
                      <button type="button" class="btn btn-outline-light botao-mini" data-resumo-periodo="30dias">ÚLTIMOS 30 DIAS</button>
                    </div>
                  </div>
                  <div class="row g-2">
                    <div class="col-6 col-md-4 col-xl">
                      <div class="card-metrica">
                        <div class="card-metrica__rotulo">Trabalhado</div>
                        <div class="card-metrica__valor text-success" id="gestaoResumoTrabalhado">—</div>
                      </div>
                    </div>
                    <div class="col-6 col-md-4 col-xl">
                      <div class="card-metrica">
                        <div class="card-metrica__rotulo">Declarado</div>
                        <div class="card-metrica__valor text-warning" id="gestaoResumoDeclarado">—</div>
                      </div>
                    </div>
                    <div class="col-6 col-md-4 col-xl">
                      <div class="card-metrica">
                        <div class="card-metrica__rotulo">Não declarado</div>
                        <div class="card-metrica__valor" style="color:#60a5fa" id="gestaoResumoNaoDeclarado">—</div>
                      </div>
                    </div>
                    <div class="col-6 col-md-4 col-xl">
                      <div class="card-metrica">
                        <div class="card-metrica__rotulo">Tempo Ocioso</div>
                        <div class="card-metrica__valor" style="color:#fbbf24" id="gestaoResumoOcioso">—</div>
                      </div>
                    </div>
                    <div class="col-6 col-md-4 col-xl">
                      <div class="card-metrica">
                        <div class="card-metrica__rotulo">A pagar</div>
                        <div class="card-metrica__valor text-info" id="gestaoResumoAPagar">—</div>
                      </div>
                    </div>
                  </div>
                  <div class="texto-fraco small mt-2">Trabalhado = cronômetro ativo. Declarado = horas nas tarefas. Ocioso = tempo sem atividade no PC. A pagar = (declarado × R$/h) − pagamentos.</div>
                </article>

                <!-- Registrar pagamento -->
                <div class="row g-3">
                  <!-- Registrar pagamento -->
                  <div class="col-12 col-xl-6">
                    <article class="cartao-grafite p-3 h-100">
                      <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">Registrar pagamento</h6>
                        <span class="badge badge-suave">BANCO</span>
                      </div>
                      <div class="row g-2 mt-2">
                        <div class="col-6">
                          <label class="form-label texto-fraco">Data do pagamento</label>
                          <input type="date" class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoData">
                        </div>
                        <div class="col-6">
                          <label class="form-label texto-fraco">Valor (R$)</label>
                          <input class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoValor" placeholder="ex: 350,00">
                        </div>
                        <div class="col-12 col-md-8">
                          <label class="form-label texto-fraco">Observação (opcional)</label>
                          <input class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoObs" placeholder="ex: pix / março 2026 / 62h">
                        </div>
                        <div class="col-12 col-md-4 d-flex align-items-end">
                          <button type="button" class="btn btn-light w-100" id="botaoRegistrarPagamento">Salvar pagamento</button>
                        </div>
                      </div>
                    </article>
                  </div>

                  <!-- Histórico de pagamentos -->
                  <div class="col-12 col-xl-6">
                    <article class="cartao-grafite p-3 h-100">
                      <div class="d-flex justify-content-between align-items-center">
                        <h6 class="mb-0">Pagamentos (histórico)</h6>
                        <div class="texto-fraco small">Total: <span class="fw-semibold" id="textoGestaoTotalPago">—</span></div>
                      </div>
                      <div class="table-responsive mt-2" style="max-height:300px; overflow-y:auto;">
                        <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
                          <thead class="sticky-top" style="background:var(--cor-fundo);">
                            <tr class="texto-fraco small">
                              <th style="min-width:110px;">Data pagto</th>
                              <th class="text-end" style="min-width:110px;">Valor</th>
                              <th style="min-width:140px;">Obs</th>
                              <th class="text-end" style="min-width:90px;">Ações</th>
                            </tr>
                          </thead>
                          <tbody id="tbodyGestaoPagamentos">
                            <tr><td colspan="4" class="texto-fraco">Carregando…</td></tr>
                          </tbody>
                        </table>
                      </div>
                    </article>
                  </div>
                </div>

              </div>

              <!-- Tarefas declaradas (full-width abaixo) -->
              <div class="col-12 mt-3">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-0">Tarefas declaradas</h6>
                    <span class="texto-fraco small" id="textoGestaoTotalTarefas">—</span>
                  </div>
                  <div class="table-responsive mt-2" style="max-height:500px; overflow-y:auto;">
                    <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
                      <thead class="sticky-top" style="background:var(--cor-fundo);">
                        <tr class="texto-fraco small">
                          <th style="min-width:90px;">Data</th>
                          <th style="min-width:100px;">Canal</th>
                          <th style="min-width:200px;">Tarefa</th>
                          <th style="min-width:80px;">Tempo</th>
                          <th class="text-center" style="min-width:80px;">Status</th>
                          <th style="min-width:200px;">Observação</th>
                          <th class="text-end" style="min-width:80px;">Ações</th>
                        </tr>
                      </thead>
                      <tbody id="tbodyGestaoTarefas">
                        <tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>
                      </tbody>
                    </table>
                  </div>
                </article>
              </div>

              <!-- Credenciais e APIs do usuário (full-width) -->
              <div class="col-12 mt-3">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center mb-2">
                    <div class="d-flex align-items-center gap-2">
                      <h6 class="mb-0">Credenciais e APIs</h6>
                      <span class="badge badge-suave">CRIPTOGRAFADO</span>
                    </div>
                    <button class="btn btn-outline-light btn-sm" type="button" data-bs-toggle="modal" data-bs-target="#modalGerenciarModelos">⚙ Modelos globais</button>
                  </div>
                  <div class="table-responsive" style="max-height:420px;">
                    <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
                      <thead class="sticky-top" style="background:var(--cor-fundo);">
                        <tr class="texto-fraco small">
                          <th style="min-width:160px;">Serviço</th>
                          <th class="text-center" style="min-width:110px;">Estado</th>
                          <th style="min-width:180px;">Máscara</th>
                          <th style="min-width:140px;">Atualizado em</th>
                          <th class="text-end" style="min-width:220px;">Ações</th>
                        </tr>
                      </thead>
                      <tbody id="tbodyGestaoCredenciais">
                        <tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>
                      </tbody>
                    </table>
                  </div>
                </article>
              </div>
            </div>
          </div>

          <section id="abaAtividades" class="d-none" aria-label="Atividades">
            <article class="cartao-grafite p-3">

              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Canais</h2>
                  <span class="badge badge-suave">BANCO</span>
                </div>

                <div class="d-flex gap-2 align-items-center">
                  <div class="input-group campo-busca">
                    <span class="input-group-text bg-transparent text-white border-secondary">🔎</span>
                    <input id="entradaBuscaAtividades" class="form-control bg-transparent text-white border-secondary"
                      placeholder="Buscar por título, status, usuário...">
                  </div>

                  <button class="btn btn-light botao-mini" type="button" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">
                    + Adicionar Canal
                  </button>
                </div>
              </div>

              <div class="table-responsive tabela-limite" style="max-height: 680px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width: 320px;">Canal</th>
                      <th class="text-center" style="min-width: 150px;">Dificuldade</th>
                      <th class="text-center" style="min-width: 160px;">Estimativa</th>
                      <th style="min-width: 320px;">Usuários</th>
                      <th class="text-center" style="min-width: 170px;">Status</th>
                      <th class="text-end" style="min-width: 210px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyAtividades">
                    <tr>
                      <td colspan="6" class="texto-fraco">Carregando…</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="texto-fraco small mt-2">
                Dica: uma atividade pode ser atribuída para 1 ou mais usuários.
              </div>
            </article>
          </section>

          <!-- ════════════════════════════════════════════════════════════
               ABA: GERENCIAR TAREFAS DECLARADAS
               ════════════════════════════════════════════════════════════ -->
          <section id="abaGerenciarTarefas" class="d-none" aria-label="Gerenciar Tarefas Declaradas">

            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Gerenciar Tarefas Declaradas</h2>
                  <span class="badge badge-suave">declarações</span>
                </div>
                <span class="texto-fraco small" id="gtTotalRegistros"></span>
              </div>

              <hr class="border-light opacity-10 my-3">

              <!-- Filtros -->
              <div class="row g-2 align-items-end mb-3">
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Data início</label>
                  <input type="date" id="gtDataInicio" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Data fim</label>
                  <input type="date" id="gtDataFim" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-12 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Membro</label>
                  <select id="gtFiltroUsuario" class="form-select bg-transparent text-white border-secondary">
                    <option value="">Todos os membros</option>
                  </select>
                </div>
                <div class="col-12 col-md-3">
                  <label class="form-label texto-fraco small mb-1">Atividade</label>
                  <select id="gtFiltroAtividade" class="form-select bg-transparent text-white border-secondary">
                    <option value="">Todas as atividades</option>
                  </select>
                </div>
                <div class="col-12 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Canal</label>
                  <input type="text" id="gtFiltroCanal" class="form-control bg-transparent text-white border-secondary" placeholder="Filtrar por canal…">
                </div>
                <div class="col-12 col-md-1 d-flex align-items-end">
                  <button type="button" class="btn btn-light w-100" id="gtBtnBuscar">Buscar</button>
                </div>
              </div>

              <!-- Tabela -->
              <div class="table-responsive tabela-limite" style="max-height: 640px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:90px;">Data</th>
                      <th style="min-width:110px;">Membro</th>
                      <th style="min-width:120px;">Canal</th>
                      <th style="min-width:200px;">Tarefa</th>
                      <th style="min-width:80px;">Tempo</th>
                      <th style="min-width:200px;">Observação</th>
                      <th class="text-center" style="min-width:100px;">Status</th>
                      <th class="text-end" style="min-width:80px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyGerenciarTarefas">
                    <tr><td colspan="8" class="texto-fraco text-center py-3">Selecione os filtros e clique em Buscar.</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

          </section>

          <!-- Modal: Editar Tarefa Declarada -->
          <div class="modal fade" id="modalEditarTarefa" tabindex="-1" aria-labelledby="modalEditarTarefaLabel" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered">
              <div class="modal-content bg-dark text-white border-secondary">
                <div class="modal-header border-secondary">
                  <h5 class="modal-title" id="modalEditarTarefaLabel">Editar Declaração</h5>
                  <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                  <p class="texto-fraco small mb-2" id="gtEditInfo"></p>

                  <div id="gtEditHorasInfo" class="d-none mb-3 p-2 rounded" style="background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08)">
                    <div class="d-flex justify-content-between small">
                      <span class="texto-fraco">Total trabalhado:</span>
                      <span class="fw-semibold text-success" id="gtHorasTrabalhado">—</span>
                    </div>
                    <div class="d-flex justify-content-between small">
                      <span class="texto-fraco">Total declarado:</span>
                      <span class="fw-semibold text-warning" id="gtHorasDeclarado">—</span>
                    </div>
                    <div class="d-flex justify-content-between small">
                      <span class="texto-fraco">Disponível:</span>
                      <span class="fw-semibold" id="gtHorasDisponivel" style="color:#60a5fa">—</span>
                    </div>
                  </div>

                  <div class="mb-3">
                    <label class="form-label texto-fraco small">Título da tarefa</label>
                    <input type="text" id="gtEditTitulo" class="form-control bg-transparent text-white border-secondary" maxlength="220">
                  </div>
                  <div class="row g-2 mb-3">
                    <div class="col-6">
                      <label class="form-label texto-fraco small">Tempo (ex: 1h30m, 90m, 1:30:00)</label>
                      <input type="text" id="gtEditTempo" class="form-control bg-transparent text-white border-secondary" placeholder="1h30m">
                    </div>
                    <div class="col-6">
                      <label class="form-label texto-fraco small">Status</label>
                      <select id="gtEditConcluida" class="form-select bg-transparent text-white border-secondary">
                        <option value="1">Concluída</option>
                        <option value="0">Aberta</option>
                      </select>
                    </div>
                  </div>
                  <div class="mb-3">
                    <label class="form-label texto-fraco small">Canal de entrega</label>
                    <input type="text" id="gtEditCanal" class="form-control bg-transparent text-white border-secondary" maxlength="180">
                  </div>
                  <div class="mb-2">
                    <label class="form-label texto-fraco small">Observação</label>
                    <textarea id="gtEditObservacao" class="form-control bg-transparent text-white border-secondary" rows="2" maxlength="600"></textarea>
                  </div>

                  <div id="gtEditErro" class="text-danger small mt-2 d-none"></div>
                </div>
                <div class="modal-footer border-secondary">
                  <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancelar</button>
                  <button type="button" class="btn btn-light" id="gtBtnSalvar">Salvar</button>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════════════════
               ABA: RELATÓRIO DE TEMPO TRABALHADO
               ════════════════════════════════════════════════════════════ -->
          <section id="abaRelatorio" class="d-none" aria-label="Relatório de tempo trabalhado">

            <!-- filtros -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Tempo Trabalhado (declarado)</h2>
                  <span class="badge badge-suave">declarações</span>
                </div>
                <div class="texto-fraco small">
                  Soma apenas o tempo que o membro declarou — sem ocioso, sem pausa.
                </div>
              </div>

              <hr class="border-light opacity-10 my-3">

              <div class="row g-2 align-items-end">
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco">Data início</label>
                  <input type="date" id="relatorioDataInicio" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco">Data fim</label>
                  <input type="date" id="relatorioDataFim" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-12 col-md-3">
                  <label class="form-label texto-fraco">Membro</label>
                  <select id="relatorioFiltroMembro" class="form-select bg-transparent text-white border-secondary">
                    <option value="">Todos</option>
                  </select>
                </div>
                <div class="col-12 col-md-5 d-flex gap-2 align-items-end">
                  <button type="button" class="btn btn-light" id="relatorioBtnCarregar">Carregar</button>
                  <button type="button" class="btn btn-outline-light" id="relatorioBtnAlternarAgrupamento">Agrupar por dia</button>
                  <button type="button" class="btn btn-outline-warning" id="relatorioBtnCSV" title="Exportar CSV">CSV</button>
                  <div class="texto-fraco small ms-auto">Atualizado: <span id="relatorioAtualizado">—</span></div>
                </div>
              </div>
            </article>

            <!-- cards de resumo -->
            <div class="row g-3 mb-3">
              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Período</div>
                  <div class="fw-bold" id="relatorioTextoPeriodo">—</div>
                </article>
              </div>
              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Total horas declaradas (equipe)</div>
                  <div class="display-6 fw-bold" id="relatorioTotalHoras">—</div>
                  <div class="texto-fraco small mt-1"><span id="relatorioTotalEditores">—</span> membro(s) com declarações</div>
                </article>
              </div>
              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Valor total estimado a pagar</div>
                  <div class="display-6 fw-bold text-success" id="relatorioTotalValor">—</div>
                  <div class="texto-fraco small mt-1">Proporcional: (horas declaradas) × R$/h cadastrado</div>
                </article>
              </div>
            </div>

            <!-- conteúdo dinâmico (por usuário ou por dia) -->
            <div id="relatorioAreaConteudo">
              <div class="texto-fraco text-center py-4">Selecione o período e clique em Carregar.</div>
            </div>

          </section>

          <!-- ════════════════════════════════════════════════════════════
               ABA: CREDENCIAIS E APIs
               ════════════════════════════════════════════════════════════ -->
          <section id="abaCredenciais" class="d-none" aria-label="Credenciais e APIs">
            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Credenciais e APIs</h2>
                  <span class="badge badge-suave">CRIPTOGRAFADO</span>
                </div>
                <div class="d-flex gap-2 align-items-center flex-wrap">
                  <select id="credenciaisFiltroUsuario" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:260px;">
                    <option value="">Selecione um usuário…</option>
                  </select>
                  <select id="credenciaisFiltroServico" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:180px;">
                    <option value="">Todos os serviços</option>
                  </select>
                  <button class="btn btn-outline-light btn-sm" type="button" data-bs-toggle="modal" data-bs-target="#modalGerenciarModelos">⚙ Modelos</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Os valores são guardados criptografados no servidor. O painel nunca exibe o valor completo.
                Cada modelo existe globalmente; cada usuário preenche o seu.
              </div>

              <!-- APIs globais ativas (herdam para novos usuários) -->
              <div id="boxApisGlobais" class="cartao-grafite p-2 mb-3 d-none" style="background:rgba(255,255,255,0.03);">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <span class="badge bg-warning text-dark">GLOBAL</span>
                  <strong class="small">APIs aplicadas a todos os usuários</strong>
                  <span class="texto-fraco small">— novos cadastros herdam automaticamente.</span>
                </div>
                <div id="listaApisGlobais" class="d-flex flex-wrap gap-2"></div>
              </div>

              <div class="table-responsive" style="max-height:620px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:160px;">Serviço</th>
                      <th style="min-width:100px;">Categoria</th>
                      <th class="text-center" style="min-width:110px;">Estado</th>
                      <th style="min-width:180px;">Máscara</th>
                      <th style="min-width:140px;">Atualizado em</th>
                      <th class="text-end" style="min-width:220px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyCredenciais">
                    <tr><td colspan="6" class="texto-fraco">Selecione um usuário acima.</td></tr>
                  </tbody>
                </table>
              </div>
            </article>
          </section>

          <!-- ════════════════════════════════════════════════════════════
               ABA: AUDITORIA (apps suspeitos + usuários com flag)
               ════════════════════════════════════════════════════════════ -->
          <section id="abaAuditoria" class="d-none" aria-label="Auditoria">
            <!-- Bloco 1: Usuários com flag -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">🚨 Usuários com alerta</h2>
                  <span class="badge badge-suave" id="auditoriaBadgeContadorUsuarios">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <span class="texto-fraco small">Atualizado em <span id="auditoriaGeradoEm">—</span></span>
                  <button class="btn btn-sm btn-outline-light" type="button" id="auditoriaBotaoRecarregar" title="Recarregar">&#x21BB;</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Bandeira 🚩 fica ativa se o usuário utilizou algum app suspeito nos últimos 7 dias.
                O histórico completo (desde sempre) permanece registrado mesmo após a bandeira sumir.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:40px;"></th>
                      <th style="min-width:160px;">Usuário</th>
                      <th style="min-width:220px;">Apps suspeitos detectados</th>
                      <th class="text-end" style="min-width:120px;">Horas totais</th>
                      <th class="text-end" style="min-width:100px;">Sessões</th>
                      <th class="text-end" style="min-width:160px;">Último uso</th>
                      <th class="text-end" style="min-width:140px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyAuditoriaUsuarios">
                    <tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

            <!-- Bloco 2: CRUD de apps suspeitos -->
            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Apps suspeitos configurados</h2>
                  <span class="badge badge-suave" id="auditoriaBadgeContadorApps">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <div class="form-check form-switch d-flex align-items-center gap-2">
                    <input class="form-check-input" type="checkbox" id="auditoriaIncluirInativos">
                    <label class="form-check-label small texto-fraco" for="auditoriaIncluirInativos">Mostrar inativos</label>
                  </div>
                  <button class="btn btn-sm btn-light" type="button" id="auditoriaBotaoNovoApp">+ Novo app</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                A lista abaixo define quais nomes de processo levantam alerta. O match é por <em>substring</em>
                (ex: cadastrar <code>autohotkey</code> pega <code>AutoHotkeyU64.exe</code>, <code>autohotkey64.exe</code>, etc).
                Use termos curtos e específicos.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:200px;">Nome do app (substring)</th>
                      <th style="min-width:260px;">Motivo</th>
                      <th class="text-center" style="min-width:90px;">Status</th>
                      <th style="min-width:120px;">Criado por</th>
                      <th style="min-width:140px;">Atualizado em</th>
                      <th class="text-end" style="min-width:180px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyAuditoriaApps">
                    <tr><td colspan="6" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>
          </section>

          <!-- ════════════════════════════════════════════════════════════
               ABA: MEGA (config de upload obrigatório por canal/usuário)
               ════════════════════════════════════════════════════════════ -->
          <section id="abaMega" class="d-none" aria-label="MEGA">

            <!-- Bloco 1: Configuração por canal -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Configuração por canal</h2>
                  <span class="badge badge-suave" id="megaBadgeCanais">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoRecarregarCanais" title="Recarregar">&#x21BB;</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Defina a <strong>pasta raiz no MEGA</strong> de cada canal e ative o upload obrigatório. Canais sem
                configuração mantêm o fluxo antigo (checkbox "Declaro que subi os arquivos").
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:220px;">Canal</th>
                      <th style="min-width:260px;">Pasta raiz no MEGA</th>
                      <th class="text-center" style="min-width:120px;">Upload ativo</th>
                      <th style="min-width:140px;">Atualizado em</th>
                      <th class="text-end" style="min-width:120px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyMegaCanais">
                    <tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

            <!-- Bloco 2: Campos exigidos por usuário + canal -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Campos de upload por usuário + canal</h2>
                  <span class="badge badge-suave" id="megaBadgeCampos">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center flex-wrap">
                  <select id="megaFiltroUser" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:200px;">
                    <option value="">Selecione um usuário…</option>
                  </select>
                  <select id="megaFiltroCanal" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:220px;">
                    <option value="">Selecione um canal…</option>
                  </select>
                  <button class="btn btn-sm btn-light" type="button" id="megaBotaoNovoCampo" disabled>+ Novo campo</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Cada usuário pode ter campos distintos por canal (ex.: editor sobe vídeo + projeto, thumbmaker sobe só thumb).
                Sem campos configurados → nenhum upload é exigido daquele usuário no canal.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:60px;">Ordem</th>
                      <th style="min-width:200px;">Label do campo</th>
                      <th style="min-width:160px;">Extensões aceitas</th>
                      <th class="text-center" style="min-width:80px;">Qtd. máx</th>
                      <th class="text-center" style="min-width:100px;">Obrigatório</th>
                      <th class="text-center" style="min-width:80px;">Ativo</th>
                      <th class="text-end" style="min-width:140px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyMegaCampos">
                    <tr><td colspan="7" class="texto-fraco">Selecione usuário e canal acima.</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

            <!-- Bloco 3: Pastas lógicas existentes (read-only) -->
            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Pastas lógicas cadastradas</h2>
                  <span class="badge badge-suave" id="megaBadgePastas">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <select id="megaFiltroCanalPastas" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:220px;">
                    <option value="">Todos os canais</option>
                  </select>
                  <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoRecarregarPastas">&#x21BB;</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Pastas criadas pelos usuários ao declarar tarefas. O nome canônico (<code>NN - Titulo</code>) é único por canal.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:180px;">Canal</th>
                      <th style="min-width:240px;">Nome da pasta</th>
                      <th style="min-width:80px;">Nº</th>
                      <th style="min-width:160px;">Criado por</th>
                      <th style="min-width:140px;">Criado em</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyMegaPastas">
                    <tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

          </section>

        </main>

        <footer class="texto-fraco small mt-4" aria-label="Rodapé">
          © Painel ADM · versão banco
        </footer>

    </div>
  </div>

  <!-- Modal: Nova Atividade (fora do main para evitar conflito de z-index) -->
  <div class="modal fade" id="modalNovaAtividade" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title" id="tituloModalAtividade">Novo Canal</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <label class="form-label texto-fraco">Título</label>
          <input id="entradaAtividadeTitulo" class="form-control bg-transparent text-white border-secondary" placeholder="ex: Ajustar página de vendas">
          <div class="mt-2">
            <label class="form-label texto-fraco">Descrição (opcional)</label>
            <textarea id="entradaAtividadeDescricao" class="form-control bg-transparent text-white border-secondary" rows="3" placeholder="Detalhe o que precisa ser feito..."></textarea>
          </div>
          <div class="row g-2 mt-2">
            <div class="col-12 col-md-4">
              <label class="form-label texto-fraco">Dificuldade</label>
              <select id="entradaAtividadeDificuldade" class="form-select bg-transparent text-white border-secondary">
                <option value="facil">Fácil</option>
                <option value="media" selected>Média</option>
                <option value="dificil">Difícil</option>
                <option value="critica">Crítica</option>
              </select>
            </div>
            <div class="col-12 col-md-4">
              <label class="form-label texto-fraco">Estimativa (horas)</label>
              <input id="entradaAtividadeEstimativa" class="form-control bg-transparent text-white border-secondary" placeholder="ex: 6">
            </div>
            <div class="col-12 col-md-4">
              <label class="form-label texto-fraco">Status</label>
              <select id="entradaAtividadeStatus" class="form-select bg-transparent text-white border-secondary">
                <option value="aberta" selected>Aberta</option>
                <option value="em_andamento">Em andamento</option>
                <option value="concluida">Concluída</option>
                <option value="cancelada">Cancelada</option>
              </select>
            </div>
          </div>
          <hr class="border-light opacity-10 my-3">
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <div class="texto-fraco small mb-1">Atribuir para usuários (ativos)</div>
              <div class="texto-fraco small">Selecione 1 ou mais.</div>
            </div>
            <div class="input-group campo-busca" style="max-width: 320px;">
              <span class="input-group-text bg-transparent text-white border-secondary">🔎</span>
              <input id="entradaBuscaUsuariosAtividade" class="form-control bg-transparent text-white border-secondary" placeholder="Buscar usuário...">
            </div>
          </div>
          <div class="mt-2" style="max-height: 260px; overflow:auto;">
            <div id="listaUsuariosAtividade" class="d-grid gap-2">
              <div class="texto-fraco">Carregando usuários…</div>
            </div>
          </div>
          <div class="texto-fraco small mt-2">
            Obs: somente usuários com <span class="fw-semibold">status_conta = ativa</span> aparecem aqui.
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light" id="botaoSalvarAtividade">
            <span id="textoBotaoSalvarAtividade">Salvar</span>
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal: Gerenciar modelos de credenciais -->
  <div class="modal fade" id="modalGerenciarModelos" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title">Modelos globais de credenciais</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="texto-fraco small mb-2">
            Criar um modelo aqui faz ele aparecer automaticamente para TODOS os usuários (com valor vazio).
          </div>
          <div class="row g-2 align-items-end mb-3">
            <div class="col-12 col-md-3">
              <label class="form-label texto-fraco">Identificador</label>
              <input id="modeloIdentificador" class="form-control bg-transparent text-white border-secondary" placeholder="ex: chatgpt">
            </div>
            <div class="col-12 col-md-3">
              <label class="form-label texto-fraco">Nome exibição</label>
              <input id="modeloNomeExibicao" class="form-control bg-transparent text-white border-secondary" placeholder="ex: ChatGPT">
            </div>
            <div class="col-6 col-md-2">
              <label class="form-label texto-fraco">Categoria</label>
              <select id="modeloCategoria" class="form-select bg-transparent text-white border-secondary">
                <option value="api">api</option>
                <option value="llm">llm</option>
                <option value="tts">tts</option>
                <option value="stt">stt</option>
                <option value="outro">outro</option>
              </select>
            </div>
            <div class="col-6 col-md-2">
              <label class="form-label texto-fraco">Ordem</label>
              <input type="number" id="modeloOrdem" class="form-control bg-transparent text-white border-secondary" value="0">
            </div>
            <div class="col-12 col-md-2 d-flex gap-2">
              <button type="button" class="btn btn-light flex-fill" id="botaoSalvarModelo">Salvar</button>
              <button type="button" class="btn btn-outline-light" id="botaoLimparModelo" title="Limpar formulário">×</button>
            </div>
            <div class="col-12">
              <label class="form-label texto-fraco">Descrição (opcional)</label>
              <input id="modeloDescricao" class="form-control bg-transparent text-white border-secondary" placeholder="detalhe breve">
              <input type="hidden" id="modeloIdEdicao" value="0">
            </div>
          </div>
          <div class="table-responsive" style="max-height:340px;">
            <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
              <thead class="sticky-top" style="background:var(--cor-fundo);">
                <tr class="texto-fraco small">
                  <th>Identificador</th>
                  <th>Nome</th>
                  <th>Categoria</th>
                  <th class="text-center">Ordem</th>
                  <th class="text-end">Ações</th>
                </tr>
              </thead>
              <tbody id="tbodyModelos">
                <tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal: Substituir valor de credencial -->
  <div class="modal fade" id="modalSubstituirValor" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title">Substituir valor</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="texto-fraco small mb-2">
            Usuário: <span class="fw-semibold" id="textoModalSubUsuario">—</span>
            · Serviço: <span class="fw-semibold" id="textoModalSubServico">—</span>
          </div>
          <label class="form-label texto-fraco">Novo valor (será criptografado antes de salvar)</label>
          <textarea id="entradaNovoValor" rows="3" class="form-control bg-transparent text-white border-secondary" placeholder="cole a API key / token aqui"></textarea>
          <div class="texto-fraco small mt-2">
            O valor não será exibido de volta depois de salvo — só a máscara parcial.
          </div>

          <div class="form-check form-switch mt-3">
            <input class="form-check-input" type="checkbox" role="switch" id="checkAplicarTodos">
            <label class="form-check-label" for="checkAplicarTodos">
              Adicionar essa credencial a <strong>todos os usuários</strong>
            </label>
            <div class="texto-fraco small">
              Sobrescreve o valor atual de todos os usuários ativos para este serviço.
              Útil para APIs globais (ex.: Assembly) usadas por toda a equipe.
            </div>
          </div>

          <input type="hidden" id="subUserId" value="">
          <input type="hidden" id="subIdModelo" value="0">
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light" id="botaoSalvarNovoValor">Salvar</button>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal: novo / editar app suspeito -->
  <div class="modal fade" id="modalAppSuspeito" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title" id="modalAppSuspeitoTitulo">Novo app suspeito</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <input type="hidden" id="appSuspeitoId" value="">
          <div class="mb-3">
            <label class="form-label texto-fraco" for="appSuspeitoNome">Nome do app (substring)</label>
            <input type="text" id="appSuspeitoNome" class="form-control bg-transparent text-white border-secondary" placeholder="ex: autohotkey" maxlength="180">
            <div class="form-text texto-fraco small">Match por <em>substring</em> no nome do processo. Use termos curtos (sem versão/arquitetura).</div>
          </div>
          <div class="mb-3">
            <label class="form-label texto-fraco" for="appSuspeitoMotivo">Motivo (opcional)</label>
            <input type="text" id="appSuspeitoMotivo" class="form-control bg-transparent text-white border-secondary" placeholder="ex: Linguagem de automação" maxlength="255">
          </div>
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="appSuspeitoAtivo" checked>
            <label class="form-check-label" for="appSuspeitoAtivo">Ativo</label>
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light" id="botaoSalvarAppSuspeito">Salvar</button>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

  <script src="./js/aba-usuarios.js?v=7"></script>
  <script src="./js/aba-atividades.js?v=7"></script>
  <script src="./js/aba-gerenciar-tarefas.js?v=7"></script>
  <script src="./js/aba-credenciais.js?v=1"></script>
  <script src="./js/aba-auditoria.js?v=3"></script>
  <script src="./js/aba-mega.js?v=1"></script>
  <script src="./js/aba-graficos.js?v=7"></script>
  <script src="./js/aba-relatorio.js?v=7"></script>
  <script src="./js/painel.js?v=7"></script>
</body>

</html>