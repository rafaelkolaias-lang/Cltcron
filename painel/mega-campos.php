<?php
// Página: MEGA · Campos de upload — organizada em 3 abas internas (pills):
//   1) Campos por usuário — fluxo principal: escolhe o usuário → canais dele em
//      cards, cada card com seus campos + "+ Novo campo" + "Aplicar modelos".
//   2) Modelos de campo — CRUD inline dos templates globais reutilizáveis.
//   3) Canais — pasta raiz no MEGA + flag upload_ativo por canal.
// Separada das Pastas lógicas (mega.php). Compartilha o aba-mega.js (cada bloco
// se protege pelos próprios elementos; o que não existe na página não roda).
$tituloPagina    = 'MEGA · Campos de upload';
$subtituloPagina = 'MEGA · campos de upload por canal e usuário';
$abaAtiva        = 'abaMega';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaMega" aria-label="MEGA · Campos de upload">

            <!-- Navegação interna: 3 áreas bem separadas + link pras Pastas -->
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
              <ul class="nav nav-pills gap-1" role="tablist">
                <li class="nav-item" role="presentation">
                  <button class="nav-link active" type="button" data-bs-toggle="pill" data-bs-target="#megaTabCampos" role="tab">
                    Campos por usuário
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" type="button" data-bs-toggle="pill" data-bs-target="#megaTabModelos" role="tab">
                    Modelos de campo <span class="badge badge-suave ms-1" id="megaBadgeModelos">—</span>
                  </button>
                </li>
                <li class="nav-item" role="presentation">
                  <button class="nav-link" type="button" data-bs-toggle="pill" data-bs-target="#megaTabCanais" role="tab">
                    Canais (pasta raiz) <span class="badge badge-suave ms-1" id="megaBadgeCanais">—</span>
                  </button>
                </li>
              </ul>
              <a href="./mega.php" class="btn btn-sm btn-outline-info" title="Ver pastas lógicas (vídeos)">Pastas lógicas →</a>
            </div>

            <div class="tab-content">

              <!-- ===== ABA 1: Campos por usuário (fluxo principal) ===== -->
              <div class="tab-pane fade show active" id="megaTabCampos" role="tabpanel">
                <article class="cartao-grafite p-3 mb-3">
                  <div class="d-flex align-items-end justify-content-between flex-wrap gap-3 mb-3">
                    <div>
                      <label for="megaFiltroUser" class="form-label small texto-fraco mb-1 text-uppercase" style="letter-spacing:.4px;">Usuário</label>
                      <select id="megaFiltroUser" class="form-select bg-transparent text-white border-secondary" style="min-width:280px;">
                        <option value="">Selecione um usuário…</option>
                      </select>
                    </div>
                    <div class="d-flex gap-2 align-items-center">
                      <span class="badge badge-suave" id="megaBadgeCampos" title="Total de campos ativos do usuário">—</span>
                      <button class="btn btn-sm btn-light" type="button" id="megaBotaoUsarModelo" disabled
                              title="Selecione um usuário primeiro">Aplicar modelos…</button>
                    </div>
                  </div>

                  <div class="texto-fraco small mb-3">
                    Aqui você define <strong>o que cada usuário precisa enviar ao MEGA</strong> (vídeo, thumb, projeto…) ao declarar
                    tarefa, canal por canal. O <strong>Tipo</strong> do campo é o que liga o "verde compartilhado" e o download no app.
                  </div>

                  <div id="megaCamposPorCanal">
                    <div class="texto-fraco">Carregando…</div>
                  </div>
                </article>
              </div>

              <!-- ===== ABA 2: Modelos de campo (templates globais) ===== -->
              <div class="tab-pane fade" id="megaTabModelos" role="tabpanel">
                <article class="cartao-grafite p-3 mb-3">
                  <div class="linha-header-card">
                    <div class="d-flex align-items-center gap-2">
                      <h2 class="h6 mb-0">Modelos de campo</h2>
                    </div>
                    <div class="d-flex gap-2 align-items-center">
                      <button class="btn btn-sm btn-light" type="button" id="megaBotaoNovoModelo">+ Novo modelo</button>
                      <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoRecarregarModelos" title="Recarregar">&#x21BB;</button>
                    </div>
                  </div>

                  <div class="texto-fraco small mb-2">
                    Modelo = <strong>campo pronto pra reaproveitar</strong>. Em vez de digitar "Vídeo final, .mp4, obrigatório" pra cada
                    usuário, você cadastra uma vez aqui e aplica em massa pelo botão <strong>Aplicar modelos…</strong> na aba
                    "Campos por usuário". Editar ou excluir um modelo <strong>não mexe</strong> nos campos que os usuários já têm.
                  </div>

                  <div class="table-responsive">
                    <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                      <thead>
                        <tr class="texto-fraco small">
                          <th style="min-width:60px;">Ordem</th>
                          <th style="min-width:160px;">Nome do modelo</th>
                          <th style="min-width:160px;">Label do campo</th>
                          <th style="min-width:110px;">Tipo</th>
                          <th style="min-width:140px;" title="Vazio = aceita qualquer extensão">Extensões</th>
                          <th class="text-center" style="min-width:80px;" title="0 = ilimitado">Qtd. máx</th>
                          <th class="text-center" style="min-width:100px;">Obrigatório</th>
                          <th class="text-end" style="min-width:140px;">Ações</th>
                        </tr>
                      </thead>
                      <tbody id="tbodyMegaModelos">
                        <tr><td colspan="8" class="texto-fraco">Carregando…</td></tr>
                      </tbody>
                    </table>
                  </div>
                </article>
              </div>

              <!-- ===== ABA 3: Canais — pasta raiz + upload ativo ===== -->
              <div class="tab-pane fade" id="megaTabCanais" role="tabpanel">
                <article class="cartao-grafite p-3">
                  <div class="linha-header-card">
                    <div class="d-flex align-items-center gap-2">
                      <h2 class="h6 mb-0">Configuração por canal</h2>
                    </div>
                    <div class="d-flex gap-2 align-items-center">
                      <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoRecarregarCanais" title="Recarregar">&#x21BB;</button>
                    </div>
                  </div>

                  <div class="texto-fraco small mb-2">
                    Defina a <strong>pasta raiz no MEGA</strong> de cada canal e ligue o <strong>Upload ativo</strong> para exigir
                    envio de arquivos. Canal com upload desligado mantém o fluxo antigo (sem exigência de upload no app).
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
              </div>

            </div>

          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- Modal: Aplicar modelos (multi-seleção modelos × canais → adiciona tudo de uma vez) -->
  <div class="modal fade" id="modalUsarModelos" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-scrollable">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <div>
            <h5 class="modal-title h6 mb-1">Aplicar modelos de campo</h5>
            <div class="texto-fraco small" id="modalUsarModelosContexto">Marque os modelos e os canais.</div>
          </div>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body">
          <div class="row g-3">
            <div class="col-md-6">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <div class="d-flex align-items-center gap-2">
                  <span class="mega-passo-num">1</span>
                  <strong class="small">O que adicionar</strong>
                </div>
                <label class="small texto-fraco d-flex align-items-center gap-1" style="cursor:pointer;">
                  <input class="form-check-input m-0" type="checkbox" id="modalUsarModelosTodosModelos"> todos
                </label>
              </div>
              <div id="modalUsarModelosLista" class="mega-lista-selecao"></div>
            </div>
            <div class="col-md-6">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <div class="d-flex align-items-center gap-2">
                  <span class="mega-passo-num">2</span>
                  <strong class="small">Em quais canais</strong>
                </div>
                <label class="small texto-fraco d-flex align-items-center gap-1" style="cursor:pointer;">
                  <input class="form-check-input m-0" type="checkbox" id="modalUsarModelosTodosCanais"> todos
                </label>
              </div>
              <div id="modalUsarModelosCanais" class="mega-lista-selecao"></div>
            </div>
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <div class="me-auto texto-fraco small" id="modalUsarModelosResumo">Marque ao menos 1 modelo e 1 canal.</div>
          <button type="button" class="btn btn-outline-light btn-sm" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light btn-sm" id="modalUsarModelosSalvar" disabled>Adicionar campos</button>
        </div>
      </div>
    </div>
  </div>

<?php
$scriptsAba = ['./js/aba-mega.js?v=13'];
require __DIR__ . '/_layout/rodape.php';
