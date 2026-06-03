<?php
// Página: Auditoria (apps suspeitos + usuários com flag) — migrada do index.php
// (Parte 6 da refatoração do painel). Usa os partials de _layout/. NOTA: o
// script aba-auditoria.js continua TAMBÉM no index.php porque ele expõe o cache
// de flags (PainelAbaAuditoria.obterFlagUsuarioSync/garantirFlagsMap/
// renderizarAlertasNaGestao) usado pelo Dashboard e pela Gestão do Usuário.
$tituloPagina    = 'Auditoria · Painel ADM';
$subtituloPagina = 'Auditoria · apps suspeitos e alertas por usuário';
$abaAtiva        = 'abaAuditoria';
require __DIR__ . '/_layout/topo.php';
?>

          <section id="abaAuditoria" aria-label="Auditoria">
            <!-- Bloco 1: Usuários com flag -->
            <article class="cartao-grafite p-3 mb-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">🚨 Usuários com alerta</h2>
                  <span class="badge badge-suave" id="auditoriaBadgeContadorUsuarios">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <span class="texto-fraco small">Atualizado em <span id="auditoriaGeradoEm">—</span></span>
                  <button class="btn btn-sm btn-outline-light" type="button" id="auditoriaBotaoRecarregar" title="Recarregar">&#x21BB;</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                Bandeira 🚩 fica ativa se o usuário utilizou algum app suspeito nos últimos 7 dias.
                O histórico completo (desde sempre) permanece registrado mesmo após a bandeira sumir.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:40px;"></th>
                      <th style="min-width:160px;">Usuário</th>
                      <th style="min-width:220px;">Apps suspeitos detectados</th>
                      <th class="text-end" style="min-width:120px;">Horas totais</th>
                      <th class="text-end" style="min-width:100px;">Sessões</th>
                      <th class="text-end" style="min-width:160px;">Último uso</th>
                      <th class="text-end" style="min-width:140px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyAuditoriaUsuarios">
                    <tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>

            <!-- Bloco 2: CRUD de apps suspeitos -->
            <article class="cartao-grafite p-3">
              <div class="linha-header-card">
                <div class="d-flex align-items-center gap-2">
                  <h2 class="h6 mb-0">Apps suspeitos configurados</h2>
                  <span class="badge badge-suave" id="auditoriaBadgeContadorApps">—</span>
                </div>
                <div class="d-flex gap-2 align-items-center">
                  <div class="form-check form-switch d-flex align-items-center gap-2">
                    <input class="form-check-input" type="checkbox" id="auditoriaIncluirInativos">
                    <label class="form-check-label small texto-fraco" for="auditoriaIncluirInativos">Mostrar inativos</label>
                  </div>
                  <button class="btn btn-sm btn-light" type="button" id="auditoriaBotaoNovoApp">+ Novo app</button>
                </div>
              </div>

              <div class="texto-fraco small mb-2">
                A lista abaixo define quais nomes de processo levantam alerta. O match é por <em>substring</em>
                (ex: cadastrar <code>autohotkey</code> pega <code>AutoHotkeyU64.exe</code>, <code>autohotkey64.exe</code>, etc).
                Use termos curtos e específicos.
              </div>

              <div class="table-responsive">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th style="min-width:200px;">Nome do app (substring)</th>
                      <th style="min-width:260px;">Motivo</th>
                      <th class="text-center" style="min-width:90px;">Status</th>
                      <th style="min-width:120px;">Criado por</th>
                      <th style="min-width:140px;">Atualizado em</th>
                      <th class="text-end" style="min-width:180px;">Ações</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyAuditoriaApps">
                    <tr><td colspan="6" class="texto-fraco">Carregando…</td></tr>
                  </tbody>
                </table>
              </div>
            </article>
          </section>

<?php require __DIR__ . '/_layout/fim_conteudo.php'; ?>

  <!-- Modal: novo / editar app suspeito (fora do container — z-index) -->
  <div class="modal fade" id="modalAppSuspeito" tabindex="-1" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content bg-dark text-white border-secondary">
        <div class="modal-header border-secondary">
          <h5 class="modal-title" id="modalAppSuspeitoTitulo">Novo app suspeito</h5>
          <button type="button" class="btn btn-close btn-close-white" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <input type="hidden" id="appSuspeitoId" value="">
          <div class="mb-3">
            <label class="form-label texto-fraco" for="appSuspeitoNome">Nome do app (substring)</label>
            <input type="text" id="appSuspeitoNome" class="form-control bg-transparent text-white border-secondary" placeholder="ex: autohotkey" maxlength="180">
            <div class="form-text texto-fraco small">Match por <em>substring</em> no nome do processo. Use termos curtos (sem versão/arquitetura).</div>
          </div>
          <div class="mb-3">
            <label class="form-label texto-fraco" for="appSuspeitoMotivo">Motivo (opcional)</label>
            <input type="text" id="appSuspeitoMotivo" class="form-control bg-transparent text-white border-secondary" placeholder="ex: Linguagem de automação" maxlength="255">
          </div>
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" id="appSuspeitoAtivo" checked>
            <label class="form-check-label" for="appSuspeitoAtivo">Ativo</label>
          </div>
        </div>
        <div class="modal-footer border-secondary">
          <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-light" id="botaoSalvarAppSuspeito">Salvar</button>
        </div>
      </div>
    </div>
  </div>

<?php
$scriptsAba = ['./js/aba-auditoria.js?v=3'];
require __DIR__ . '/_layout/rodape.php';
