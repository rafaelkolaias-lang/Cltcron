<?php
// Página: Log de Atividades (migrada do index.php — Parte 1 da refatoração do
// painel). Usa os partials compartilhados de _layout/. A paginação é feita pelo
// próprio js/aba-log-atividades.js + endpoint commands/log_atividades/listar.php.
$tituloPagina    = 'Log de Atividades · Painel ADM';
$subtituloPagina = 'Log · registro de todas as ações do servidor';
$abaAtiva        = 'abaLogAtividades';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaLogAtividades" aria-label="Log de Atividades">

            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Log de Atividades</h2>
                  <span class="badge badge-suave" id="logBadgeTotal">—</span>
                </div>
                <span class="texto-fraco small">Retidos por 60 dias</span>
              </div>

              <hr class="border-light opacity-10 my-3">

              <!-- Filtros -->
              <div class="row g-2 align-items-end mb-3">
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Data inicio</label>
                  <input type="date" id="logDataInicio" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Data fim</label>
                  <input type="date" id="logDataFim" class="form-control bg-transparent text-white border-secondary">
                </div>
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Entidade</label>
                  <select id="logFiltroEntidade" class="form-select bg-transparent text-white border-secondary">
                    <option value="">Todas</option>
                  </select>
                </div>
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Acao</label>
                  <select id="logFiltroAcao" class="form-select bg-transparent text-white border-secondary">
                    <option value="">Todas</option>
                  </select>
                </div>
                <div class="col-6 col-md-2">
                  <label class="form-label texto-fraco small mb-1">Executor</label>
                  <select id="logFiltroExecutor" class="form-select bg-transparent text-white border-secondary">
                    <option value="">Todos</option>
                  </select>
                </div>
                <div class="col-6 col-md-2 d-flex gap-2 align-items-end">
                  <div class="input-group campo-busca flex-grow-1">
                    <input id="logFiltroBusca" class="form-control bg-transparent text-white border-secondary" placeholder="Buscar...">
                  </div>
                  <button type="button" class="btn btn-light" id="logBtnBuscar">Buscar</button>
                </div>
              </div>

              <!-- Tabela -->
              <div class="table-responsive tabela-limite" style="max-height: 640px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:150px;">Data/Hora</th>
                      <th style="min-width:100px;">Executor</th>
                      <th style="min-width:110px;">Entidade</th>
                      <th style="min-width:90px;">Acao</th>
                      <th style="min-width:280px;">Descricao</th>
                      <th style="min-width:110px;">IP</th>
                      <th class="text-end" style="min-width:80px;">Detalhe</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyLogAtividades">
                    <tr><td colspan="7" class="texto-fraco text-center py-3">Carregando...</td></tr>
                  </tbody>
                </table>
              </div>
              <nav class="mt-2 d-flex justify-content-end" id="paginacaoLog" aria-label="Paginacao dos logs"></nav>
            </article>

          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>
<?php
$scriptsAba = ['./js/aba-log-atividades.js?v=1'];
require __DIR__ . '/_layout/rodape.php';
