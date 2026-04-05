<?php
header('Content-Type: text/html; charset=utf-8');
?>
<!doctype html>
<html lang="pt-br">

<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Painel ADM · Cronômetro</title>

  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="./css/painel.css" rel="stylesheet">
</head>

<body>
  <div class="container-fluid">
    <div class="row g-0">

      <aside class="col-12 col-lg-3 col-xl-2 sidebar p-3" aria-label="Menu lateral">
        <header class="d-flex align-items-center gap-2 mb-3">
          <div class="cartao-grafite d-grid place-items-center sidebar__icone">
            <span class="fw-bold">ADM</span>
          </div>
          <div>
            <div class="fw-bold">Painel Cronômetro</div>
            <div class="texto-fraco small">Dados do banco</div>
          </div>
        </header>

        <section class="cartao-grafite p-3 mb-3" aria-label="Status do ambiente">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div>
              <div class="texto-fraco small">Ambiente</div>
              <div class="small text-truncate" id="textoAmbiente" title="Local">Local</div>
            </div>
            <span class="badge badge-suave">v1</span>
          </div>

          <hr class="border-light opacity-10 my-3">

          <div class="d-flex gap-2">
            <button id="botaoAtualizarTudo" class="btn btn-sm btn-light flex-fill" type="button">Atualizar</button>
            <button id="botaoAutoAtualizacao" class="btn btn-sm btn-outline-light flex-fill" type="button" data-ativo="0">Auto: off</button>
          </div>

          <div class="texto-fraco small mt-2">
            Este painel carrega usuários e pagamentos do banco.
          </div>
        </section>

        <section class="cartao-grafite p-3 mb-3" aria-label="Download do aplicativo">
          <div class="d-flex justify-content-between align-items-start gap-2">
            <div>
              <div class="texto-fraco small">Aplicativo</div>
              <div class="small">Cronômetro do funcionário</div>
            </div>
            <span class="badge badge-suave">.exe</span>
          </div>

          <hr class="border-light opacity-10 my-3">

          <div class="d-grid gap-2">
            <a href="/baixar_app.php" class="btn btn-sm btn-light">
              Baixar aplicativo
            </a>
          </div>

          <div class="texto-fraco small mt-2">
            Baixe o executável e envie para o funcionário instalar no computador.
          </div>
        </section>

        <nav aria-label="Abas do painel">
          <ul class="nav nav-pills flex-column gap-1" id="menuAbas">
            <li class="nav-item"><a class="nav-link active" href="#" data-aba="abaDashboard">Dashboard</a></li>
            <li class="nav-item"><a class="nav-link" href="#" data-aba="abaUsuarios">Usuários</a></li>
            <li class="nav-item"><a class="nav-link" href="#" data-aba="abaAtividades">Atividades</a></li>
            <li class="nav-item"><a class="nav-link" href="#" data-aba="abaGraficos">Gráficos</a></li>
            <li class="nav-item"><a class="nav-link" href="#" data-aba="abaRelatorio">Relatório</a></li>
          </ul>
        </nav>

        <footer class="texto-fraco small mt-3">
          Próximo passo: ligar cronômetro real por usuário (API/app).
        </footer>
      </aside>

      <div class="col-12 col-lg-9 col-xl-10 p-3 p-md-4">

        <header class="d-flex flex-wrap gap-2 align-items-center justify-content-between mb-3" aria-label="Topo do painel">
          <div>
            <h1 class="h4 mb-1">Painel Administrativo</h1>
            <div id="textoSubtitulo" class="texto-fraco">Dashboard · visão geral</div>
          </div>

          <div class="d-flex gap-2">
            <button class="btn btn-light" type="button" id="botaoRecarregarAba">Recarregar aba</button>
          </div>
        </header>

        <section id="areaAlertas" aria-label="Mensagens do sistema"></section>

        <main aria-label="Conteúdo principal">

          <section id="abaDashboard" aria-label="Dashboard">
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

            <div class="row g-3 mt-1">
              <div class="col-12">
                <article class="cartao-grafite p-3">
                  <div class="linha-header-card">
                    <div class="d-flex align-items-center gap-2">
                      <h2 class="h6 mb-0">Usuários (resumo)</h2>
                      <span class="badge badge-suave" id="badgeStatus">BANCO</span>
                    </div>

                    <div class="d-flex gap-2 align-items-center">
                      <div class="input-group campo-busca">
                        <span class="input-group-text bg-transparent text-white border-secondary">🔎</span>
                        <input id="entradaBuscaGeral" class="form-control bg-transparent text-white border-secondary"
                          placeholder="Buscar por usuário, nome ou nível...">
                      </div>
                      <button class="btn btn-outline-light botao-mini" type="button" id="botaoLimparBusca">Limpar</button>
                    </div>
                  </div>

                  <div class="table-responsive tabela-limite">
                    <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                      <thead>
                        <tr class="texto-fraco small">
                          <th style="min-width: 240px;">Usuário</th>
                          <th class="text-center" style="min-width: 160px;">Status</th>
                          <th class="text-center" style="min-width: 140px;">Nível</th>
                          <th class="text-center" style="min-width: 140px;">R$/hora</th>
                          <th class="text-center" style="min-width: 180px;">Atualizado</th>
                          <th class="text-end" style="min-width: 150px;">Ações</th>
                        </tr>
                      </thead>
                      <tbody id="tbodyResumoUsuarios">
                        <tr>
                          <td colspan="6" class="texto-fraco">Carregando…</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </article>
              </div>
            </div>
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

          <section id="abaGraficos" class="d-none" aria-label="Gráficos">

            <div class="row g-3">
              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Atualização dos gráficos</div>
                  <div class="fw-bold" id="textoGraficosUltimaAtualizacao">—</div>
                  <div class="texto-fraco small">Segue o mesmo “Atualizar/Auto” do painel</div>
                </article>
              </div>

              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Usuários ativos</div>
                  <div class="display-6 fw-bold" id="numeroGraficosUsuariosAtivos">—</div>
                  <div class="texto-fraco small">Baseado no status_conta</div>
                </article>
              </div>

              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Total pago (30 dias)</div>
                  <div class="display-6 fw-bold" id="numeroGraficosTotalPago30Dias">—</div>
                  <div class="texto-fraco small">Somatório do histórico</div>
                </article>
              </div>
            </div>

            <div class="row g-3 mt-1">
              <div class="col-12">
                <article class="cartao-grafite p-3">
                  <div class="d-flex flex-wrap justify-content-between align-items-center gap-2">
                    <div class="d-flex align-items-center gap-2">
                      <h2 class="h6 mb-0">Filtros (Uso de Apps)</h2>
                      <span class="badge badge-suave">min:seg</span>
                    </div>

                    <div class="texto-fraco small">
                      Para selecionar vários: <span class="fw-semibold">Ctrl</span> (Windows) / <span class="fw-semibold">Cmd</span> (Mac)
                    </div>
                  </div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="row g-2">
                    <div class="col-12 col-md-3">
                      <label class="form-label texto-fraco">Data início</label>
                      <input type="date" id="filtroGraficosDataInicio" class="form-control bg-transparent text-white border-secondary">
                    </div>

                    <div class="col-12 col-md-3">
                      <label class="form-label texto-fraco">Data fim</label>
                      <input type="date" id="filtroGraficosDataFim" class="form-control bg-transparent text-white border-secondary">
                    </div>

                    <div class="col-12 col-md-3">
                      <label class="form-label texto-fraco">Limite (Top)</label>
                      <input type="number" id="filtroGraficosLimite" class="form-control bg-transparent text-white border-secondary" value="10" min="3" max="30">
                    </div>

                    <div class="col-12 col-md-3 d-grid">
                      <label class="form-label texto-fraco">&nbsp;</label>
                      <button type="button" class="btn btn-light" id="botaoAplicarFiltrosGraficos">Aplicar filtros</button>
                    </div>

                    <div class="col-12 col-md-6">
                      <label class="form-label texto-fraco">Usuários</label>
                      <select id="filtroGraficosUsuarios" class="form-select bg-transparent text-white border-secondary" multiple size="6"></select>
                    </div>

                    <div class="col-12 col-md-6">
                      <label class="form-label texto-fraco">Apps</label>
                      <select id="filtroGraficosApps" class="form-select bg-transparent text-white border-secondary" multiple size="6"></select>
                    </div>

                    <div class="col-12 d-flex gap-2">
                      <button type="button" class="btn btn-outline-light" id="botaoLimparFiltrosGraficos">Limpar</button>
                      <div class="texto-fraco small d-flex align-items-center">
                        Obs: o card “Atualização dos gráficos” acima mostra o horário da última atualização.
                      </div>
                    </div>
                  </div>
                </article>
              </div>
            </div>

            <div class="row g-3 mt-1">
              <div class="col-12 col-xl-6">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Top Apps (tempo)</h2>
                    <span class="badge badge-suave">min:seg</span>
                  </div>
                  <div class="mt-3" style="height: 320px;">
                    <canvas id="graficoAppsTop" aria-label="Gráfico top apps"></canvas>
                  </div>
                  <div class="texto-fraco small mt-2" id="textoGraficoAppsTopInfo">—</div>
                </article>
              </div>

              <div class="col-12 col-xl-6">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Apps por Usuário (empilhado)</h2>
                    <span class="badge badge-suave">min:seg</span>
                  </div>
                  <div class="mt-3" style="height: 320px;">
                    <canvas id="graficoAppsPorUsuario" aria-label="Gráfico apps por usuário"></canvas>
                  </div>
                  <div class="texto-fraco small mt-2" id="textoGraficoAppsPorUsuarioInfo">—</div>
                </article>
              </div>
            </div>

            <div class="row g-3 mt-1">
              <div class="col-12 col-xl-6">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Usuários por status</h2>
                    <span class="badge badge-suave">tempo real</span>
                  </div>
                  <div class="mt-3" style="height: 320px;">
                    <canvas id="graficoUsuariosStatus" aria-label="Gráfico de usuários por status"></canvas>
                  </div>
                  <div class="texto-fraco small mt-2" id="textoGraficoUsuariosStatusInfo">—</div>
                </article>
              </div>

              <div class="col-12 col-xl-6">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Usuários por nível</h2>
                    <span class="badge badge-suave">tempo real</span>
                  </div>
                  <div class="mt-3" style="height: 320px;">
                    <canvas id="graficoUsuariosNivel" aria-label="Gráfico de usuários por nível"></canvas>
                  </div>
                  <div class="texto-fraco small mt-2" id="textoGraficoUsuariosNivelInfo">—</div>
                </article>
              </div>

              <div class="col-12 col-xl-6">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Top usuários por pagamento (30 dias)</h2>
                    <span class="badge badge-suave">tempo real</span>
                  </div>
                  <div class="mt-3" style="height: 320px;">
                    <canvas id="graficoTopUsuariosPago" aria-label="Gráfico top usuários por pagamentos"></canvas>
                  </div>
                  <div class="texto-fraco small mt-2" id="textoGraficoTopUsuariosPagoInfo">—</div>
                </article>
              </div>
            </div>

            <div class="texto-fraco small mt-3">
              Obs: os gráficos “antigos” usam os dados do painel (usuários/pagamentos). Os novos “Uso de Apps” consultam direto a tabela cronometro_apps_intervalos.
              O gráfico “Pagamentos por mês” foi removido — fica apenas o card “Total pago (30 dias)”.
            </div>

            <div class="row g-3 mt-1">
              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Tempo trabalhado (período)</div>
                  <div class="fw-bold" id="textoGraficosTempoTrabalhado">—</div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="texto-fraco small">Tempo em pausa (período)</div>
                  <div class="fw-bold" id="textoGraficosTempoPausado">—</div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="texto-fraco small">Tempo ocioso (período)</div>
                  <div class="fw-bold" id="textoGraficosTempoOcioso">—</div>
                </article>
              </div>

              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Total a pagar (apenas trabalhando)</div>
                  <div class="display-6 fw-bold" id="numeroGraficosTotalAPagar">—</div>
                  <div class="texto-fraco small">Proporcional: (segundos_trabalhando / 3600) × valor_hora</div>

                  <hr class="border-light opacity-10 my-3">

                  <div class="texto-fraco small">Total horas trabalhadas (somatório usuários)</div>
                  <div class="fw-bold" id="textoGraficosHorasTrabalhadasTotal">—</div>
                </article>
              </div>

              <div class="col-12 col-md-4">
                <article class="cartao-grafite p-3 h-100">
                  <div class="texto-fraco small">Obs</div>
                  <div class="small texto-fraco">
                    • O cálculo usa <span class="fw-semibold">usuarios.valor_hora</span><br>
                    • Considera somente <span class="fw-semibold">cronometro_relatorios</span> dentro do período filtrado<br>
                    • Pausa/ocioso aparecem no relatório, mas não entram no “a pagar” (a não ser que você queira)
                  </div>
                </article>
              </div>
            </div>

            <div class="row g-3 mt-1">
              <div class="col-12 col-xl-7">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Valor a pagar por usuário (trabalhando)</h2>
                    <span class="badge badge-suave">R$</span>
                  </div>
                  <div class="mt-3" style="height: 340px;">
                    <canvas id="graficoValorAPagarUsuarios" aria-label="Gráfico valor a pagar por usuário"></canvas>
                  </div>
                  <div class="texto-fraco small mt-2" id="textoGraficoValorAPagarInfo">—</div>
                </article>
              </div>

              <div class="col-12 col-xl-5">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center">
                    <h2 class="h6 mb-0">Resumo por usuário</h2>
                    <span class="badge badge-suave">tempo + R$</span>
                  </div>

                  <div class="table-responsive mt-2" style="max-height: 360px;">
                    <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
                      <thead>
                        <tr class="texto-fraco small">
                          <th>Usuário</th>
                          <th class="text-end">Trab</th>
                          <th class="text-end">Pausa</th>
                          <th class="text-end">Ocioso</th>
                          <th class="text-end">R$</th>
                        </tr>
                      </thead>
                      <tbody id="tbodyGraficosFinanceiroUsuarios">
                        <tr>
                          <td colspan="5" class="texto-fraco">Carregando…</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div class="texto-fraco small mt-2">
                    “R$” = proporcional do tempo <span class="fw-semibold">trabalhando</span>.
                  </div>
                </article>
              </div>
            </div>
          </section>

          <div class="modal fade" id="modalNovaAtividade" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
              <div class="modal-content bg-dark text-white border-secondary">
                <div class="modal-header border-secondary">
                  <h5 class="modal-title" id="tituloModalAtividade">Nova atividade</h5>
                  <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>

                <div class="modal-body">
                  <label class="form-label texto-fraco">Título</label>
                  <input id="entradaAtividadeTitulo" class="form-control bg-transparent text-white border-secondary"
                    placeholder="ex: Ajustar página de vendas">

                  <div class="mt-2">
                    <label class="form-label texto-fraco">Descrição (opcional)</label>
                    <textarea id="entradaAtividadeDescricao" class="form-control bg-transparent text-white border-secondary"
                      rows="3" placeholder="Detalhe o que precisa ser feito..."></textarea>
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
                      <input id="entradaAtividadeEstimativa" class="form-control bg-transparent text-white border-secondary"
                        placeholder="ex: 6">
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
                      <input id="entradaBuscaUsuariosAtividade" class="form-control bg-transparent text-white border-secondary"
                        placeholder="Buscar usuário...">
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
                  Soma apenas o tempo que o editor declarou — sem ocioso, sem pausa.
                </div>
              </div>

              <hr class="border-light opacity-10 my-3">

              <div class="row g-2 align-items-end">
                <div class="col-12 col-md-3">
                  <label class="form-label texto-fraco">Data início</label>
                  <input type="date" id="relatorioDataInicio" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-12 col-md-3">
                  <label class="form-label texto-fraco">Data fim</label>
                  <input type="date" id="relatorioDataFim" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-12 col-md-3 d-flex gap-2">
                  <button type="button" class="btn btn-light flex-fill" id="relatorioBtnCarregar">Carregar</button>
                  <button type="button" class="btn btn-outline-light flex-fill" id="relatorioBtnAlternarAgrupamento">Agrupar por dia</button>
                </div>
                <div class="col-12 col-md-3 d-flex align-items-end">
                  <div class="texto-fraco small">Atualizado: <span id="relatorioAtualizado">—</span></div>
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
                  <div class="texto-fraco small">Total horas declaradas (todos editores)</div>
                  <div class="display-6 fw-bold" id="relatorioTotalHoras">—</div>
                  <div class="texto-fraco small mt-1"><span id="relatorioTotalEditores">—</span> editor(es) com declarações</div>
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
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>

  <script src="./js/aba-usuarios.js"></script>
  <script src="./js/aba-atividades.js"></script>
  <script src="./js/aba-graficos.js"></script>
  <script src="./js/aba-relatorio.js"></script>
  <script src="./js/painel.js"></script>
</body>

</html>