<?php
// Página: MEGA · Pastas lógicas — lista dos vídeos/pastas criados pelos usuários.
// Separada da configuração de Campos de upload (mega-campos.php) para a página
// não ficar sobrecarregada. Compartilha o aba-mega.js: cada bloco se protege
// pelos próprios elementos, então o que não existe nesta página não roda.
$tituloPagina    = 'MEGA · Pastas lógicas';
$subtituloPagina = 'MEGA · pastas lógicas (vídeos)';
$abaAtiva        = 'abaMega';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaMega" aria-label="MEGA · Pastas lógicas">

            <!-- Pastas lógicas existentes -->
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
                A configuração de campos de upload ficou em <a href="./mega-campos.php" class="text-info">Campos de upload</a>.
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

          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>
<?php
$scriptsAba = ['./js/aba-mega.js?v=8'];
require __DIR__ . '/_layout/rodape.php';
