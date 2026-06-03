<?php
// Página: Gerenciar Tarefas Declaradas (migrada do index.php — Parte 3 da
// refatoração do painel). Usa os partials de _layout/. Lista paginada de
// subtarefas declaradas (page/per_page) com filtros e modal de edição.
$tituloPagina    = 'Gerenciar Tarefas · Painel ADM';
$subtituloPagina = 'Gerenciar Tarefas · declarações';
$abaAtiva        = 'abaGerenciarTarefas';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaGerenciarTarefas" aria-label="Gerenciar Tarefas Declaradas">

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
              <!-- Paginação inferior — substitui o corte silencioso de 500 itens -->
              <nav class="mt-2 d-flex justify-content-end" id="paginacaoGerenciarTarefas" aria-label="Paginação das tarefas"></nav>
            </article>

          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- Modal: Editar Tarefa Declarada (fora do container — z-index) -->
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
$scriptsAba = ['./js/aba-gerenciar-tarefas.js?v=11'];
require __DIR__ . '/_layout/rodape.php';
