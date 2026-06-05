<?php
// Página: Canal (Atividades) — migrada do index.php (Parte 5 da refatoração do
// painel). Usa os partials de _layout/. NOTA: o modalNovaAtividade e o script
// aba-atividades.js continuam TAMBÉM no index.php porque o atalho "+ Adicionar
// Canal" do Dashboard depende deles (resolver na Parte 9/10).
$tituloPagina    = 'Canais · Painel ADM';
$subtituloPagina = 'Atividades · canais e atribuições';
$abaAtiva        = 'abaAtividades';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaAtividades" aria-label="Atividades">
            <article class="cartao-grafite p-3">

              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Canais</h2>
                  <span class="badge badge-suave">BANCO</span>
                </div>

                <div class="d-flex gap-2 align-items-center">
                  <div class="input-group campo-busca">
                    <span class="input-group-text bg-transparent text-white border-secondary">🔎</span>
                    <input id="entradaBuscaAtividades" class="form-control bg-transparent text-white border-secondary"
                      placeholder="Buscar por título, status, usuário...">
                  </div>

                  <button class="btn btn-light botao-mini" type="button" data-bs-toggle="modal" data-bs-target="#modalNovaAtividade">
                    + Adicionar Canal
                  </button>
                </div>
              </div>

              <div class="table-responsive tabela-limite" style="max-height: 680px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width: 320px;">Canal</th>
                      <th class="text-center" style="min-width: 150px;">Dificuldade</th>
                      <th class="text-center" style="min-width: 160px;">Estimativa</th>
                      <th style="min-width: 320px;">Usuários</th>
                      <th class="text-center" style="min-width: 170px;">Status</th>
                      <th class="text-end" style="min-width: 210px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyAtividades">
                    <tr>
                      <td colspan="6" class="texto-fraco">Carregando…</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div class="texto-fraco small mt-2">
                Dica: uma atividade pode ser atribuída para 1 ou mais usuários.
              </div>
            </article>
          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- Modal: Novo Canal (fora do container — z-index) -->
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

<?php
$scriptsAba = ['./js/aba-atividades.js?v=8'];
require __DIR__ . '/_layout/rodape.php';
