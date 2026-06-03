<?php
// Página: Relatório de Tempo Trabalhado (migrada do index.php — Parte 2 da
// refatoração do painel). Usa os partials de _layout/. O relatório é agregado
// por período (filtro de datas + membro), agrupável por usuário ou por dia,
// com export CSV — não é lista paginada por linhas.
$tituloPagina    = 'Relatório de Tempo Trabalhado · Painel ADM';
$subtituloPagina = 'Relatório · tempo trabalhado declarado';
$abaAtiva        = 'abaRelatorio';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaRelatorio" aria-label="Relatório de tempo trabalhado">

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

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>
<?php
$scriptsAba = ['./js/aba-relatorio.js?v=8'];
require __DIR__ . '/_layout/rodape.php';
