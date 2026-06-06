<?php
// Página: MEGA · Campos de upload — campos exigidos por usuário+canal + gestão
// de modelos (templates) inline + configuração de pasta raiz por canal (no fim).
// Separada das Pastas lógicas (mega.php). Compartilha o aba-mega.js (cada bloco
// se protege pelos próprios elementos; o que não existe na página não roda).
$tituloPagina    = 'MEGA · Campos de upload';
$subtituloPagina = 'MEGA · campos de upload por canal e usuário';
$abaAtiva        = 'abaMega';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaMega" aria-label="MEGA · Campos de upload">

            <div class="mb-2">
              <a href="./mega.php" class="btn btn-sm btn-outline-info" title="Ver pastas lógicas (vídeos)">← Pastas lógicas</a>
            </div>

            <!-- Bloco 1: Campos por usuário — todos os canais do usuário, agrupados -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Campos de upload por usuário + canal</h2>
                  <span class="badge badge-suave" id="megaBadgeCampos">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center flex-wrap">
                  <select id="megaFiltroUser" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:220px;">
                    <option value="">Selecione um usuário…</option>
                  </select>
                  <button class="btn btn-sm btn-light" type="button" id="megaBotaoUsarModelo" disabled
                          title="Marque modelos e canais e adicione tudo de uma vez">Usar modelo existente</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Selecione o usuário → aparecem <strong>todos os canais dele</strong>, cada um com seus campos. Use <strong>+ Novo campo</strong> no canal, ou <strong>Usar modelo existente</strong> pra adicionar modelos a vários canais de uma vez.
                Marque o <strong>Tipo</strong> certo (Thumb / Vídeo / …) — é o que liga o "verde compartilhado" e o download no app.
              </div>

              <div id="megaCamposPorCanal">
                <div class="texto-fraco">Selecione um usuário acima para ver os canais dele.</div>
              </div>
            </article>

            <!-- Bloco 2: Modelos de campo reutilizáveis (CRUD inline) -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Modelos de campo (reutilizáveis)</h2>
                  <span class="badge badge-suave" id="megaBadgeModelos">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <button class="btn btn-sm btn-light" type="button" id="megaBotaoNovoModelo">+ Novo modelo</button>
                  <button class="btn btn-sm btn-outline-light" type="button" id="megaBotaoRecarregarModelos" title="Recarregar">&#x21BB;</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Modelos são atalhos globais pra preencher campos rápido (use em "Usar modelo existente" acima).
                Editar ou excluir um modelo <strong>não mexe</strong> nos campos que os usuários já têm — só altera esta lista de modelos.
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

            <!-- Bloco 3: Configuração por canal (no fim — define pasta raiz + ativa upload) -->
            <article class="cartao-grafite p-3">
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

          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- Modal: Usar modelos existentes (multi-seleção → adiciona todos de uma vez) -->
  <div class="modal fade" id="modalUsarModelos" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-scrollable">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title h6 mb-0">Usar modelos existentes</h5>
          <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body">
          <p class="texto-fraco small mb-2" id="modalUsarModelosContexto">Marque os modelos e os canais.</p>
          <div class="small mb-1"><strong>Modelos</strong> <span class="texto-fraco">(viram campos):</span></div>
          <div id="modalUsarModelosLista"></div>
          <hr class="border-secondary my-2">
          <div class="small mb-1"><strong>Canais do usuário</strong> <span class="texto-fraco">(onde criar):</span></div>
          <div id="modalUsarModelosCanais"></div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light btn-sm" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light btn-sm" id="modalUsarModelosSalvar">Salvar selecionados</button>
        </div>
      </div>
    </div>
  </div>

<?php
$scriptsAba = ['./js/aba-mega.js?v=11'];
require __DIR__ . '/_layout/rodape.php';
