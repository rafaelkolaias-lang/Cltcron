<?php
// Página Dashboard (home do painel). Cabeçalho, menu e rodapé vêm dos partials
// compartilhados em _layout/ (ver Parte 0 da refatoração do painel). As seções
// das demais abas ainda vivem aqui e são alternadas via SPA (painel.js) até
// cada uma virar sua própria página.
$tituloPagina    = 'Painel ADM · RK Produções Digitais';
$subtituloPagina = 'Dashboard · visão geral';
$abaAtiva        = 'abaDashboard';
require __DIR__ . '/_layout/topo.php';
?>

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
                      <th class="text-center" style="min-width: 180px;">Chave Pix</th>
                      <th class="text-center" style="min-width: 140px;">Status</th>
                      <th class="text-center" style="min-width: 170px;">Atualizado</th>
                      <th class="text-end" style="min-width: 220px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyUsuarios">
                    <tr>
                      <td colspan="7" class="texto-fraco">Carregando…</td>
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
                <a href="./auditoria.php" class="small" id="linkIrAuditoriaGestao">Ver aba Auditoria →</a>
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
                    <div class="col-6 col-md-4 col-xl">
                      <div class="card-metrica">
                        <div class="card-metrica__rotulo">Pago</div>
                        <div class="card-metrica__valor" style="color:#a78bfa" id="gestaoResumoPago">—</div>
                      </div>
                    </div>
                  </div>
                  <div class="texto-fraco small mt-2">Trabalhado = cronômetro ativo. Declarado = horas nas tarefas. Ocioso = tempo sem atividade no PC. A pagar = (declarado × R$/h) − pagamentos. Pago = total já pago no período.</div>
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

              <!-- Canais vinculados (full-width) -->
              <div class="col-12 mt-3">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center flex-wrap gap-2 mb-2">
                    <div class="d-flex align-items-center gap-2">
                      <h6 class="mb-0">Canais vinculados</h6>
                      <span class="badge badge-suave" id="textoGestaoTotalCanais">—</span>
                    </div>
                    <button type="button" class="btn btn-sm btn-primary" id="btnSalvarCanaisGestao">Salvar canais</button>
                  </div>
                  <div class="texto-fraco small mb-2">
                    Marque os canais nos quais este usuário deve participar.
                    Você não precisa abrir o canal: o vínculo é gravado direto a partir daqui.
                  </div>
                  <div id="listaCanaisGestao" class="row g-2">
                    <div class="col-12"><div class="texto-fraco">Carregando canais…</div></div>
                  </div>
                </article>
              </div>

              <!-- Tarefas declaradas (full-width abaixo) -->
              <div class="col-12 mt-3">
                <article class="cartao-grafite p-3">
                  <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                    <h6 class="mb-0">Tarefas declaradas</h6>
                    <div class="d-flex align-items-center gap-2 flex-wrap">
                      <span class="texto-fraco small">Ordenar por:</span>
                      <select id="selectOrdemTarefasGestao" class="form-select form-select-sm bg-transparent text-white border-secondary" style="width:auto;min-width:160px;">
                        <option value="data">Data (mais recente)</option>
                        <option value="canal">Canal</option>
                        <option value="tarefa">Tarefa (título)</option>
                      </select>
                      <span class="texto-fraco small" id="textoGestaoTotalTarefas">—</span>
                    </div>
                  </div>
                  <div class="texto-fraco small mt-1">
                    Não pagas ficam sempre no topo; pagas (bloqueadas) ficam embaixo.
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
                  <!-- Paginação inferior. Substitui o corte silencioso de 500 itens -->
                  <nav class="mt-2 d-flex justify-content-end" id="paginacaoGestaoTarefas" aria-label="Paginação das tarefas declaradas"></nav>
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

          <!-- Aba "Canal" (Atividades) migrada para ./canal.php (Parte 5). O modalNovaAtividade
               e o script aba-atividades.js PERMANECEM neste index.php porque o atalho
               "+ Adicionar Canal" do Dashboard depende deles. -->

          <!-- ════════════════════════════════════════════════════════════
               ABA: GERENCIAR TAREFAS DECLARADAS
               ════════════════════════════════════════════════════════════ -->
          <!-- Aba "Gerenciar Tarefas" migrada para a página dedicada ./gerenciar-tarefas.php (Parte 3 da refatoração do painel). -->

          <!-- Modal "Editar Tarefa Declarada" migrado para ./gerenciar-tarefas.php (Parte 3). -->

          <!-- ════════════════════════════════════════════════════════════
               ABA: RELATÓRIO DE TEMPO TRABALHADO
               ════════════════════════════════════════════════════════════ -->
          <!-- Aba "Relatório" migrada para a página dedicada ./relatorio.php (Parte 2 da refatoração do painel). -->

          <!-- ════════════════════════════════════════════════════════════
               ABA: CREDENCIAIS E APIs
               ════════════════════════════════════════════════════════════ -->
          <!-- Aba "Credenciais e APIs" migrada para ./credenciais.php (Parte 4). Os modais
               modalGerenciarModelos/modalSubstituirValor e o script aba-credenciais.js
               PERMANECEM neste index.php porque a aba "Gestão do Usuário" ainda os usa
               (serão tratados na Parte 8, junto com Usuários+Gestão). -->

          <!-- ════════════════════════════════════════════════════════════
               ABA: AUDITORIA (apps suspeitos + usuários com flag)
               ════════════════════════════════════════════════════════════ -->
          <!-- Aba "Auditoria" migrada para ./auditoria.php (Parte 6). O script aba-auditoria.js
               PERMANECE neste index.php porque expõe o cache de flags (obterFlagUsuarioSync/
               garantirFlagsMap/renderizarAlertasNaGestao) usado pelo Dashboard e pela Gestão. -->

          <!-- ════════════════════════════════════════════════════════════
               ABA: MEGA (config de upload obrigatório por canal/usuário)
               ════════════════════════════════════════════════════════════ -->
          <section id="abaMega" class="d-none" aria-label="MEGA">

            <!-- Bloco 1 (visual): Pastas lógicas existentes -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Pastas lógicas cadastradas</h2>
                  <span class="badge badge-suave" id="megaBadgePastas">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center flex-wrap">
                  <input type="text" id="megaBuscaPastas" class="form-control form-control-sm bg-transparent text-white border-secondary" placeholder="Buscar pasta…" style="min-width:160px;max-width:220px;">
                  <select id="megaFiltroStatusPastas" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:140px;">
                    <option value="">Todos os status</option>
                    <option value="pendente">Pendentes</option>
                    <option value="publicado">Publicados</option>
                  </select>
                  <select id="megaFiltroCanalPastas" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:220px;">
                    <option value="">Todos os canais</option>
                  </select>
                  <select id="megaFiltroUpadoPor" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:160px;">
                    <option value="">Upado por</option>
                  </select>
                  <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoRecarregarPastas">&#x21BB;</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Pastas criadas pelos usuários ao declarar tarefas. O nome canônico (<code>NN - Titulo</code>) é único por canal. Clique no nome para abrir no MEGA.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:180px;cursor:pointer;user-select:none;" data-mega-sort="titulo_atividade">Canal <span class="mega-sort-icon"></span></th>
                      <th style="min-width:240px;cursor:pointer;user-select:none;" data-mega-sort="nome_pasta">Nome da pasta <span class="mega-sort-icon"></span></th>
                      <th style="min-width:140px;cursor:pointer;user-select:none;" data-mega-sort="upado_por">Upado por <span class="mega-sort-icon"></span></th>
                      <th style="min-width:80px;cursor:pointer;user-select:none;" data-mega-sort="numero_video">Nº <span class="mega-sort-icon"></span></th>
                      <th style="min-width:100px;cursor:pointer;user-select:none;" data-mega-sort="video_publicado">Status <span class="mega-sort-icon"></span></th>
                      <th style="min-width:140px;cursor:pointer;user-select:none;" data-mega-sort="criado_em">Criado em <span class="mega-sort-icon"></span></th>
                      <th style="min-width:120px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyMegaPastas">
                    <tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

            <!-- Bloco 2: Configuração por canal -->
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

            <!-- Bloco 3: Campos exigidos por usuário + canal -->
            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Campos de upload por usuário + canal</h2>
                  <span class="badge badge-suave" id="megaBadgeCampos">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center flex-wrap">
                  <select id="megaFiltroUser" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:200px;">
                    <option value="">Selecione um usuário…</option>
                  </select>
                  <select id="megaFiltroCanal" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:220px;" disabled>
                    <option value="">Selecione um usuário primeiro…</option>
                  </select>
                  <button class="btn btn-sm btn-light" type="button" id="megaBotaoNovoCampo" disabled>+ Novo campo</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Cada usuário pode ter campos distintos por canal (ex.: editor sobe vídeo + projeto, thumbmaker sobe só thumb).
                Sem campos configurados → nenhum upload é exigido daquele usuário no canal.
              </div>

              <!-- Barra de modelos (templates) reutilizáveis -->
              <div class="d-flex flex-wrap align-items-center gap-2 mb-2 p-2 rounded" style="background:rgba(255,255,255,0.04);">
                <span class="texto-fraco small">Modelos:</span>
                <select id="megaSelectModelo" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:200px;" disabled>
                  <option value="">Carregando…</option>
                </select>
                <button class="btn btn-sm btn-light" type="button" id="megaBotaoUsarModelo" disabled
                        title="Insere uma nova linha editável já preenchida com este modelo (você ainda precisa clicar em Salvar)">Usar modelo</button>
                <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoSalvarComoModelo" disabled
                        title="Salva a linha em edição como um novo modelo global">+ Salvar linha como modelo</button>
                <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoGerenciarModelos"
                        title="Listar e desativar modelos">Gerenciar</button>
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:60px;">Ordem</th>
                      <th style="min-width:200px;">Label do campo</th>
                      <th style="min-width:160px;" title="Vazio = aceita qualquer extensão">Extensões aceitas</th>
                      <th class="text-center" style="min-width:80px;" title="0 = ilimitado">Qtd. máx</th>
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

          </section>

          <!-- ════════════════════════════════════════════════════════════
               ABA: LOG DE ATIVIDADES
               ════════════════════════════════════════════════════════════ -->
          <!-- Aba "Log de Atividades" migrada para a página dedicada ./log.php (Parte 1 da refatoração do painel). -->


<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

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

  <!-- Modal "novo/editar app suspeito" migrado para ./auditoria.php (Parte 6). -->

<?php
// Scripts específicos desta página (Dashboard, que ainda hospeda todas as abas
// via SPA). O rodapé já carrega bootstrap + chart.js (base) e painel.js (núcleo).
$scriptsAba = [
    './js/aba-usuarios.js?v=10',
    './js/aba-atividades.js?v=8',
    './js/aba-credenciais.js?v=2',
    './js/aba-auditoria.js?v=3',
    './js/aba-mega.js?v=6',
    './js/aba-graficos.js?v=7',
];
require __DIR__ . '/_layout/rodape.php';
