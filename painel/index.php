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

          <!-- Aba "Usuários" + "Gestão do Usuário" migradas para ./usuarios.php (Parte 8).
               O modalAdicionarUsuario e o script aba-usuarios.js PERMANECEM neste index.php
               porque o atalho "+ Adicionar Usuário" do Dashboard depende deles. -->

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

          <!-- "Gestão do Usuário" migrada para ./usuarios.php (Parte 8). -->

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
          <!-- Aba "MEGA" migrada para ./mega.php (Parte 7). Sem acoplamento — seção e script
               (aba-mega.js) foram inteiros para a nova página. -->

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

  <!-- Modais de credenciais (modalGerenciarModelos/modalSubstituirValor) migrados para
       ./credenciais.php e ./usuarios.php (Parte 8 — a Gestao saiu do index). -->

  <!-- Modal "novo/editar app suspeito" migrado para ./auditoria.php (Parte 6). -->

<?php
// Scripts específicos desta página (Dashboard, que ainda hospeda todas as abas
// via SPA). O rodapé já carrega bootstrap + chart.js (base) e painel.js (núcleo).
$scriptsAba = [
    './js/aba-usuarios.js?v=10',
    './js/aba-atividades.js?v=8',
    './js/aba-auditoria.js?v=3',
    './js/aba-graficos.js?v=7',
];
require __DIR__ . '/_layout/rodape.php';
