<?php
// Página: Usuários + Gestão do Usuário (migrada do index.php — Parte 8 da
// refatoração do painel). É a tela mais acoplada: a Gestão usa credenciais
// (aba-credenciais.js + modais), auditoria (aba-auditoria.js — flags/alertas) e
// edição de tarefas (aba-gerenciar-tarefas.js + modalEditarTarefa).
//
// Deep-link: usuarios.php?user=<id> abre direto a Gestão daquele usuário
// (usado pelos gráficos do Dashboard e pela Auditoria, que agora navegam pra cá).
//
// A aba Usuários (#abaUsuarios) começa visível; a Gestão (#abaGestaoUsuario)
// começa oculta (d-none) e é exibida via PainelNucleo_trocarAba. Como o boot do
// painel.js é pulado em páginas dedicadas, o aba-usuarios.js inicializa a tabela
// sozinho aqui (ver auto-init no fim do arquivo).
$tituloPagina    = 'Usuários · Painel ADM';
$subtituloPagina = 'Usuários · gestão e pagamentos';
$abaAtiva        = 'abaUsuarios';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaUsuarios" aria-label="Usuários">
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
                      <button type="button" class="btn btn-outline-danger" id="botaoRemoverUsuario" disabled>Excluir definitivamente</button>
                      <div class="texto-fraco small" id="textoRemoverUsuarioMotivo">Só dá pra excluir contas sem nenhuma tarefa declarada, pagamento ou arquivo enviado.</div>
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
                      <button type="button" class="btn btn-light botao-mini active" data-resumo-periodo="pendente">PENDENTE PAGAMENTO</button>
                      <button type="button" class="btn btn-outline-light botao-mini" data-resumo-periodo="tudo">TUDO</button>
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

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- ===== Modais (fora do container — z-index) ===== -->

  <!-- Modal: Adicionar usuário -->
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

  <!-- Modal: Editar Tarefa Declarada (usado pela Gestão via gtAbrirEdicao) -->
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
            <!-- Aviso de bloqueio quando a tarefa é MEGA (preenchido por aba-gerenciar-tarefas.js). -->
            <div id="gtEditAvisoMega" class="form-text small text-warning d-none mt-1"></div>
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

<?php
// A Gestão depende de: credenciais (grade + modais), auditoria (flags/alertas) e
// edição de tarefas (gtAbrirEdicao + modalEditarTarefa). Por isso carregamos os
// 4 scripts aqui.
$scriptsAba = [
    './js/aba-auditoria.js?v=3',
    './js/aba-credenciais.js?v=2',
    './js/aba-gerenciar-tarefas.js?v=11',
    './js/aba-usuarios.js?v=10',
];
require __DIR__ . '/_layout/rodape.php';
