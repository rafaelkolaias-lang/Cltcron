<?php
// Página: MEGA (config de upload obrigatório por canal/usuário) — migrada do
// index.php (Parte 7 da refatoração do painel). Usa os partials de _layout/.
// Sem modais (edição inline). O aba-mega.js só era usado pela própria aba
// (painel.js), então foi movido inteiro para cá (sem duplicação no index).
$tituloPagina    = 'MEGA · Painel ADM';
$subtituloPagina = 'MEGA · upload obrigatório por canal e usuário';
$abaAtiva        = 'abaMega';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaMega" aria-label="MEGA">

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

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>
<?php
$scriptsAba = ['./js/aba-mega.js?v=6'];
require __DIR__ . '/_layout/rodape.php';
