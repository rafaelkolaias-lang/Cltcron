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
  <link href="./css/painel.css" rel="stylesheet">
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
            <a class="nav-link" href="#" data-aba="abaAtividades">Atividades</a>
            <ul class="submenu-nav">
              <li><a href="#" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">+ Nova Atividade</a></li>
            </ul>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" data-aba="abaGerenciarTarefas">Gerenciar Tarefas</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="#" data-aba="abaRelatorio">Relatório</a>
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
              <button class="btn btn-sm btn-outline-light" type="button" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">+ Nova Atividade</button>
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
                Dica: clique em “Gestão” para editar dados, ativar/inativar e registrar pagamentos.
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

          <div class="modal fade" id="modalGestaoUsuario" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
              <div class="modal-content bg-dark text-white border-secondary">
                <div class="modal-header border-secondary">
                  <div>
                    <h5 class="modal-title mb-0">Gestão do usuário</h5>
                    <div class="texto-fraco small" id="textoGestaoSubtitulo">—</div>
                  </div>
                  <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>

                <div class="modal-body">
                  <div class="row g-3">

                    <div class="col-12 col-lg-4">
                      <div class="cartao-grafite p-3">

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
                            <div class="text-end">
                              <div class="texto-fraco small">—</div>
                              <div class="texto-fraco small"> </div>
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

                          <div class="texto-fraco small mt-2">
                            Alterações são salvas no banco.
                          </div>
                        </div>

                      </div>
                    </div>

                    <div class="col-12 col-lg-8">

                      <!-- Resumo de horas para pagamento -->
                      <div class="cartao-grafite p-3 mb-3" id="blocoResumoHorasPagamento">
                        <h6 class="mb-2">Resumo para pagamento</h6>
                        <div class="row g-2">
                          <div class="col-6 col-md-3">
                            <div class="card-metrica">
                              <div class="card-metrica__rotulo">Trabalhado</div>
                              <div class="card-metrica__valor text-success" id="gestaoResumoTrabalhado">—</div>
                            </div>
                          </div>
                          <div class="col-6 col-md-3">
                            <div class="card-metrica">
                              <div class="card-metrica__rotulo">Declarado</div>
                              <div class="card-metrica__valor text-warning" id="gestaoResumoDeclarado">—</div>
                            </div>
                          </div>
                          <div class="col-6 col-md-3">
                            <div class="card-metrica">
                              <div class="card-metrica__rotulo">Não declarado</div>
                              <div class="card-metrica__valor" style="color:#60a5fa" id="gestaoResumoNaoDeclarado">—</div>
                            </div>
                          </div>
                          <div class="col-6 col-md-3">
                            <div class="card-metrica">
                              <div class="card-metrica__rotulo">A pagar</div>
                              <div class="card-metrica__valor text-info" id="gestaoResumoAPagar">—</div>
                            </div>
                          </div>
                        </div>
                        <div class="texto-fraco small mt-2">Apenas horas <strong>não pagas</strong> (subtarefas com <code>bloqueada_pagamento = 0</code>).</div>
                      </div>

                      <div class="cartao-grafite p-3">
                        <div class="d-flex justify-content-between align-items-center">
                          <h6 class="mb-0">Registrar pagamento</h6>
                          <span class="badge badge-suave">BANCO</span>
                        </div>

                        <div class="row g-2 mt-2">
                          <div class="col-12 col-md-3">
                            <label class="form-label texto-fraco">Data do pagamento</label>
                            <input type="date" class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoData">
                          </div>

                          <div class="col-12 col-md-3">
                            <label class="form-label texto-fraco">Referência início</label>
                            <input type="date" class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoReferenciaInicio">
                          </div>

                          <div class="col-12 col-md-3">
                            <label class="form-label texto-fraco">Referência fim</label>
                            <input type="date" class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoReferenciaFim">
                          </div>

                          <div class="col-12 col-md-3">
                            <label class="form-label texto-fraco">Travado até</label>
                            <input type="date" class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoTravadoAte">
                          </div>

                          <div class="col-12 col-md-4">
                            <label class="form-label texto-fraco">Valor (R$)</label>
                            <input class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoValor" placeholder="ex: 350,00">
                          </div>

                          <div class="col-12 col-md-8">
                            <label class="form-label texto-fraco">Observação (opcional)</label>
                            <input class="form-control bg-transparent text-white border-secondary" id="entradaPagamentoObs" placeholder="ex: pix / adiantamento / pagamento março">
                          </div>

                          <div class="col-12 d-grid">
                            <button type="button" class="btn btn-light" id="botaoRegistrarPagamento">Salvar pagamento</button>
                          </div>
                        </div>

                        <div class="texto-fraco small mt-2">
                          O campo “Travado até” define até qual data o prestador não poderá mais editar nem excluir subtarefas.
                        </div>
                      </div>

                      <div class="cartao-grafite p-3 mt-3">
                        <div class="d-flex justify-content-between align-items-center">
                          <h6 class="mb-0">Pagamentos (histórico)</h6>
                          <div class="texto-fraco small">
                            Total: <span class="fw-semibold" id="textoGestaoTotalPago">—</span>
                          </div>
                        </div>

                        <div class="table-responsive mt-2">
                          <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
                            <thead>
                              <tr class="texto-fraco small">
                                <th style="min-width: 120px;">Data pagto</th>
                                <th style="min-width: 190px;">Referência</th>
                                <th style="min-width: 130px;">Travado até</th>
                                <th class="text-end" style="min-width: 140px;">Valor</th>
                                <th style="min-width: 260px;">Obs</th>
                              </tr>
                            </thead>
                            <tbody id="tbodyGestaoPagamentos">
                              <tr>
                                <td colspan="5" class="texto-fraco">Carregando…</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>

                        <div class="texto-fraco small mt-2">
                          Pagamentos são registros reais no banco e o período travado deve aparecer aqui também.
                        </div>
                      </div>

                    </div>

                  </div>
                </div>

                <div class="modal-footer border-secondary">
                  <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Fechar</button>
                </div>
              </div>
            </div>
          </div>

          <section id="abaAtividades" class="d-none" aria-label="Atividades">
            <article class="cartao-grafite p-3">

              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Atividades</h2>
                  <span class="badge badge-suave">BANCO</span>
                </div>

                <div class="d-flex gap-2 align-items-center">
                  <div class="input-group campo-busca">
                    <span class="input-group-text bg-transparent text-white border-secondary">🔎</span>
                    <input id="entradaBuscaAtividades" class="form-control bg-transparent text-white border-secondary"
                      placeholder="Buscar por título, status, usuário...">
                  </div>

                  <button class="btn btn-light botao-mini" type="button" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">
                    + Nova atividade
                  </button>
                </div>
              </div>

              <div class="table-responsive tabela-limite" style="max-height: 680px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width: 320px;">Atividade</th>
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
                      <th style="min-width:160px;">Atividade</th>
                      <th style="min-width:200px;">Tarefa</th>
                      <th style="min-width:80px;">Tempo</th>
                      <th style="min-width:120px;">Canal</th>
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
          <h5 class="modal-title" id="tituloModalAtividade">Nova atividade</h5>
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

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

  <script src="./js/aba-usuarios.js"></script>
  <script src="./js/aba-atividades.js"></script>
  <script src="./js/aba-gerenciar-tarefas.js"></script>
  <script src="./js/aba-graficos.js"></script>
  <script src="./js/aba-relatorio.js"></script>
  <script src="./js/painel.js"></script>
</body>

</html>