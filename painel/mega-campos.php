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

            <!-- Bloco 1: Campos exigidos por usuário + canal -->
            <article class="cartao-grafite p-3 mb-3">
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
                Marque o <strong>Tipo</strong> certo (Thumb / Vídeo / …) — é o que liga o "verde compartilhado" e o download no app.
              </div>

              <!-- Usar modelos: abre um popup com checkboxes pra adicionar vários de uma vez -->
              <div class="d-flex flex-wrap align-items-center gap-2 mb-2 p-2 rounded" style="background:rgba(255,255,255,0.04);">
                <button class="btn btn-sm btn-light" type="button" id="megaBotaoUsarModelo" disabled
                        title="Selecione vários modelos de uma vez e adicione todos ao usuário+canal">Usar modelo existente</button>
                <span class="texto-fraco small ms-1">abre uma lista pra marcar vários modelos e adicionar todos de uma vez ao usuário+canal selecionado.</span>
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:60px;">Ordem</th>
                      <th style="min-width:200px;">Label do campo</th>
                      <th style="min-width:110px;" title="Classifica o conteúdo: Vídeo, Projeto, Thumb, Texto ou Outro">Tipo</th>
                      <th style="min-width:160px;" title="Vazio = aceita qualquer extensão">Extensões aceitas</th>
                      <th class="text-center" style="min-width:80px;" title="0 = ilimitado">Qtd. máx</th>
                      <th class="text-center" style="min-width:100px;">Obrigatório</th>
                      <th class="text-center" style="min-width:80px;">Ativo</th>
                      <th class="text-end" style="min-width:140px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyMegaCampos">
                    <tr><td colspan="8" class="texto-fraco">Selecione usuário e canal acima.</td></tr>
                  </tbody>
                </table>
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
                Modelos são atalhos globais pra preencher campos rápido (use em "Aplicar modelo" acima).
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
          <p class="texto-fraco small mb-2" id="modalUsarModelosContexto">Marque os modelos pra adicionar como campos.</p>
          <div id="modalUsarModelosLista"></div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light btn-sm" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light btn-sm" id="modalUsarModelosSalvar">Salvar selecionados</button>
        </div>
      </div>
    </div>
  </div>

<?php
$scriptsAba = ['./js/aba-mega.js?v=9'];
require __DIR__ . '/_layout/rodape.php';
