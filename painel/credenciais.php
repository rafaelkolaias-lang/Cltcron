<?php
// Página: Credenciais e APIs (migrada do index.php — Parte 4 da refatoração do
// painel). Usa os partials de _layout/. NOTA: o aba-credenciais.js e os modais
// modalGerenciarModelos/modalSubstituirValor continuam TAMBÉM no index.php
// porque a aba "Gestão do Usuário" (ainda no index, até a Parte 8) depende
// deles — duplicação intencional enquanto a migração não termina.
$tituloPagina    = 'Credenciais e APIs · Painel ADM';
$subtituloPagina = 'Credenciais e APIs · segredos por usuário';
$abaAtiva        = 'abaCredenciais';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaCredenciais" aria-label="Credenciais e APIs">
            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Credenciais e APIs</h2>
                  <span class="badge badge-suave">CRIPTOGRAFADO</span>
                </div>
                <div class="d-flex gap-2 align-items-center flex-wrap">
                  <select id="credenciaisFiltroUsuario" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:260px;">
                    <option value="">Selecione um usuário…</option>
                  </select>
                  <select id="credenciaisFiltroServico" class="form-select form-select-sm bg-transparent text-white border-secondary" style="min-width:180px;">
                    <option value="">Todos os serviços</option>
                  </select>
                  <button class="btn btn-outline-light btn-sm" type="button" data-bs-toggle="modal" data-bs-target="#modalGerenciarModelos">⚙ Modelos</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Os valores são guardados criptografados no servidor. O painel nunca exibe o valor completo.
                Cada modelo existe globalmente; cada usuário preenche o seu.
              </div>

              <!-- APIs globais ativas (herdam para novos usuários) -->
              <div id="boxApisGlobais" class="cartao-grafite p-2 mb-3 d-none" style="background:rgba(255,255,255,0.03);">
                <div class="d-flex align-items-center gap-2 mb-2">
                  <span class="badge bg-warning text-dark">GLOBAL</span>
                  <strong class="small">APIs aplicadas a todos os usuários</strong>
                  <span class="texto-fraco small">— novos cadastros herdam automaticamente.</span>
                </div>
                <div id="listaApisGlobais" class="d-flex flex-wrap gap-2"></div>
              </div>

              <div class="table-responsive" style="max-height:620px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:160px;">Serviço</th>
                      <th style="min-width:100px;">Categoria</th>
                      <th class="text-center" style="min-width:110px;">Estado</th>
                      <th style="min-width:180px;">Máscara</th>
                      <th style="min-width:140px;">Atualizado em</th>
                      <th class="text-end" style="min-width:220px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyCredenciais">
                    <tr><td colspan="6" class="texto-fraco">Selecione um usuário acima.</td></tr>
                  </tbody>
                </table>
              </div>
            </article>
          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- Modal: Gerenciar modelos de credenciais (fora do container — z-index) -->
  <div class="modal fade" id="modalGerenciarModelos" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title">Modelos globais de credenciais</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="texto-fraco small mb-2">
            Criar um modelo aqui faz ele aparecer automaticamente para TODOS os usuários (com valor vazio).
          </div>
          <div class="row g-2 align-items-end mb-3">
            <div class="col-12 col-md-3">
              <label class="form-label texto-fraco">Identificador</label>
              <input id="modeloIdentificador" class="form-control bg-transparent text-white border-secondary" placeholder="ex: chatgpt">
            </div>
            <div class="col-12 col-md-3">
              <label class="form-label texto-fraco">Nome exibição</label>
              <input id="modeloNomeExibicao" class="form-control bg-transparent text-white border-secondary" placeholder="ex: ChatGPT">
            </div>
            <div class="col-6 col-md-2">
              <label class="form-label texto-fraco">Categoria</label>
              <select id="modeloCategoria" class="form-select bg-transparent text-white border-secondary">
                <option value="api">api</option>
                <option value="llm">llm</option>
                <option value="tts">tts</option>
                <option value="stt">stt</option>
                <option value="outro">outro</option>
              </select>
            </div>
            <div class="col-6 col-md-2">
              <label class="form-label texto-fraco">Ordem</label>
              <input type="number" id="modeloOrdem" class="form-control bg-transparent text-white border-secondary" value="0">
            </div>
            <div class="col-12 col-md-2 d-flex gap-2">
              <button type="button" class="btn btn-light flex-fill" id="botaoSalvarModelo">Salvar</button>
              <button type="button" class="btn btn-outline-light" id="botaoLimparModelo" title="Limpar formulário">×</button>
            </div>
            <div class="col-12">
              <label class="form-label texto-fraco">Descrição (opcional)</label>
              <input id="modeloDescricao" class="form-control bg-transparent text-white border-secondary" placeholder="detalhe breve">
              <input type="hidden" id="modeloIdEdicao" value="0">
            </div>
          </div>
          <div class="table-responsive" style="max-height:340px;">
            <table class="table table-dark table-borderless align-middle mb-0 tabela-suave">
              <thead class="sticky-top" style="background:var(--cor-fundo);">
                <tr class="texto-fraco small">
                  <th>Identificador</th>
                  <th>Nome</th>
                  <th>Categoria</th>
                  <th class="text-center">Ordem</th>
                  <th class="text-end">Ações</th>
                </tr>
              </thead>
              <tbody id="tbodyModelos">
                <tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Modal: Substituir valor de credencial (fora do container — z-index) -->
  <div class="modal fade" id="modalSubstituirValor" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title">Substituir valor</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="texto-fraco small mb-2">
            Usuário: <span class="fw-semibold" id="textoModalSubUsuario">—</span>
            · Serviço: <span class="fw-semibold" id="textoModalSubServico">—</span>
          </div>
          <label class="form-label texto-fraco">Novo valor (será criptografado antes de salvar)</label>
          <textarea id="entradaNovoValor" rows="3" class="form-control bg-transparent text-white border-secondary" placeholder="cole a API key / token aqui"></textarea>
          <div class="texto-fraco small mt-2">
            O valor não será exibido de volta depois de salvo — só a máscara parcial.
          </div>

          <div class="form-check form-switch mt-3">
            <input class="form-check-input" type="checkbox" role="switch" id="checkAplicarTodos">
            <label class="form-check-label" for="checkAplicarTodos">
              Adicionar essa credencial a <strong>todos os usuários</strong>
            </label>
            <div class="texto-fraco small">
              Sobrescreve o valor atual de todos os usuários ativos para este serviço.
              Útil para APIs globais (ex.: Assembly) usadas por toda a equipe.
            </div>
          </div>

          <input type="hidden" id="subUserId" value="">
          <input type="hidden" id="subIdModelo" value="0">
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light" id="botaoSalvarNovoValor">Salvar</button>
        </div>
      </div>
    </div>
  </div>

<?php
$scriptsAba = ['./js/aba-credenciais.js?v=2'];
require __DIR__ . '/_layout/rodape.php';
