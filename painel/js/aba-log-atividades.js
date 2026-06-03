/**
 * aba-log-atividades.js
 *
 * Log geral de atividades do servidor — mostra todas as acoes
 * (criacao, edicao, exclusao) com filtros, paginacao e detalhe.
 * Retencao de 60 dias (cleanup automatico no backend).
 */
(function () {
  'use strict';

  // ---- cache DOM ----
  const tbody           = document.getElementById('tbodyLogAtividades');
  const badgeTotal      = document.getElementById('logBadgeTotal');
  const selectEntidade  = document.getElementById('logFiltroEntidade');
  const selectAcao      = document.getElementById('logFiltroAcao');
  const selectExecutor  = document.getElementById('logFiltroExecutor');
  const inputBusca      = document.getElementById('logFiltroBusca');
  const inputDataInicio = document.getElementById('logDataInicio');
  const inputDataFim    = document.getElementById('logDataFim');
  const btnBuscar       = document.getElementById('logBtnBuscar');
  const navPaginacao    = document.getElementById('paginacaoLog');

  if (!tbody) return; // aba nao existe na pagina

  let paginaAtual = 1;
  let filtrosPopulados = false;

  // ---- helpers ----
  function esc(str) {
    if (str == null) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function badgeAcao(acao) {
    const cores = {
      criou:           'bg-success',
      editou:          'bg-warning text-dark',
      excluiu:         'bg-danger',
      alterou_status:  'bg-info text-dark',
      soft_delete:     'bg-secondary',
      salvou:          'bg-primary',
      revogou:         'bg-secondary',
      reprocessou:     'bg-info text-dark',
      vinculou:        'bg-primary',
      erro_interno:    'bg-danger',
      rejeicao:        'bg-warning text-dark',
    };
    const cls = cores[acao] || 'bg-secondary';
    return `<span class="badge ${cls}">${esc(acao)}</span>`;
  }

  function badgeEntidade(ent) {
    const icones = {
      usuario:     '👤',
      atividade:   '📋',
      subtarefa:   '📝',
      pagamento:   '💰',
      credencial:  '🔑',
      mega:        '☁️',
      auditoria:   '🛡️',
      mega_campo:  '📎',
      mega_config: '⚙️',
      mega_pasta:  '📁',
      mega_upload: '📤',
      painel:      '🖥️',
      desktop:     '💻',
      mega_modelo: '📐',
      canal_usuario: '🔗',
      config:      '⚙️',
    };
    const ico = icones[ent] || '📄';
    return `${ico} <span class="text-white-50">${esc(ent)}</span>`;
  }

  function formatarDataHora(str) {
    if (!str) return '—';
    const d = new Date(str.replace(' ', 'T') + 'Z');
    if (isNaN(d.getTime())) return esc(str);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getUTCDate())}/${pad(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
  }

  // ---- renderizar tabela ----
  function renderizar(dados) {
    const { registros, total, pagina, total_paginas, filtros } = dados;

    badgeTotal.textContent = `${total} registro${total !== 1 ? 's' : ''}`;

    // Popular filtros (apenas uma vez ou se vazios)
    if (!filtrosPopulados && filtros) {
      popularSelect(selectEntidade, filtros.entidades, 'Todas');
      popularSelect(selectAcao, filtros.acoes, 'Todas');
      popularSelectExecutores(selectExecutor, filtros.executores);
      filtrosPopulados = true;
    }

    if (!registros || registros.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="texto-fraco text-center py-3">Nenhum log encontrado.</td></tr>';
      navPaginacao.innerHTML = '';
      return;
    }

    let html = '';
    for (const r of registros) {
      const temDetalhe = r.tem_dados_antes === '1' || r.tem_dados_antes === 1
                      || r.tem_dados_depois === '1' || r.tem_dados_depois === 1;
      html += `<tr>
        <td class="small">${formatarDataHora(r.data_hora)}</td>
        <td class="small">${esc(r.nome_executor || r.user_id_executor || '—')}</td>
        <td class="small">${badgeEntidade(r.entidade)}</td>
        <td class="small">${badgeAcao(r.acao)}</td>
        <td class="small" style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${esc(r.descricao)}">${esc(r.descricao)}</td>
        <td class="small text-white-50">${esc(r.ip || '—')}</td>
        <td class="text-end">${temDetalhe
          ? `<button class="btn btn-outline-light btn-sm" data-log-detalhe="${r.id_log}" title="Ver detalhes">Detalhe</button>`
          : '<span class="texto-fraco small">—</span>'
        }</td>
      </tr>`;
    }
    tbody.innerHTML = html;

    // Paginacao
    renderizarPaginacao(pagina, total_paginas);
  }

  function popularSelect(sel, valores, labelTodos) {
    if (!sel || !valores) return;
    const atual = sel.value;
    sel.innerHTML = `<option value="">${labelTodos}</option>`;
    for (const v of valores) {
      const opt = document.createElement('option');
      opt.value = v;
      opt.textContent = v;
      sel.appendChild(opt);
    }
    if (atual) sel.value = atual;
  }

  function popularSelectExecutores(sel, executores) {
    const atual = sel.value;
    sel.innerHTML = '<option value="">Todos</option>';
    for (const ex of executores) {
      const opt = document.createElement('option');
      opt.value = typeof ex === 'object' ? ex.user_id : ex;
      opt.textContent = typeof ex === 'object' ? ex.nome : ex;
      sel.appendChild(opt);
    }
    if (atual) sel.value = atual;
  }

  function renderizarPaginacao(pagina, total) {
    if (total <= 1) { navPaginacao.innerHTML = ''; return; }

    let html = '<ul class="pagination pagination-sm mb-0">';

    // Anterior
    html += `<li class="page-item ${pagina <= 1 ? 'disabled' : ''}">
      <a class="page-link bg-transparent text-white border-secondary" href="#" data-log-pagina="${pagina - 1}">&laquo;</a></li>`;

    // Numeros (mostra max 7 paginas ao redor da atual)
    const inicio = Math.max(1, pagina - 3);
    const fim = Math.min(total, pagina + 3);
    for (let i = inicio; i <= fim; i++) {
      html += `<li class="page-item ${i === pagina ? 'active' : ''}">
        <a class="page-link bg-transparent text-white border-secondary" href="#" data-log-pagina="${i}">${i}</a></li>`;
    }

    // Proximo
    html += `<li class="page-item ${pagina >= total ? 'disabled' : ''}">
      <a class="page-link bg-transparent text-white border-secondary" href="#" data-log-pagina="${pagina + 1}">&raquo;</a></li>`;

    html += '</ul>';
    navPaginacao.innerHTML = html;
  }

  // ---- fetch ----
  function carregarLogs(pagina) {
    paginaAtual = pagina || 1;

    const params = new URLSearchParams();
    params.set('pagina', String(paginaAtual));
    params.set('por_pagina', '50');

    if (selectEntidade.value) params.set('entidade', selectEntidade.value);
    if (selectAcao.value)     params.set('acao', selectAcao.value);
    if (selectExecutor.value) params.set('executor', selectExecutor.value);
    if (inputBusca.value.trim()) params.set('busca', inputBusca.value.trim());
    if (inputDataInicio.value)   params.set('data_inicio', inputDataInicio.value);
    if (inputDataFim.value)      params.set('data_fim', inputDataFim.value);

    tbody.innerHTML = '<tr><td colspan="7" class="texto-fraco text-center py-3">Carregando...</td></tr>';

    fetch('./commands/log_atividades/listar.php?' + params.toString())
      .then(r => r.json())
      .then(json => {
        if (!json.ok) throw new Error(json.mensagem);
        renderizar(json.dados);
      })
      .catch(err => {
        tbody.innerHTML = `<tr><td colspan="7" class="text-danger text-center py-3">Erro: ${esc(err.message)}</td></tr>`;
      });
  }

  // ---- modal de detalhe ----
  function abrirDetalhe(idLog) {
    fetch(`./commands/log_atividades/detalhe.php?id_log=${idLog}`)
      .then(r => r.json())
      .then(json => {
        if (!json.ok) { alert(json.mensagem); return; }
        const r = json.dados;
        mostrarModalDetalhe(r);
      })
      .catch(err => alert('Erro ao buscar detalhe: ' + err.message));
  }

  function mostrarModalDetalhe(r) {
    // Remove modal anterior se existir
    const anteriorEl = document.getElementById('modalLogDetalhe');
    if (anteriorEl) anteriorEl.remove();

    const antesHtml  = r.dados_antes  ? formatarJSON(r.dados_antes) : '<span class="texto-fraco">—</span>';
    const depoisHtml = r.dados_depois ? formatarJSON(r.dados_depois) : '<span class="texto-fraco">—</span>';

    const modalHtml = `
    <div class="modal fade" id="modalLogDetalhe" tabindex="-1" aria-hidden="true">
      <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content bg-dark text-white border-secondary">
          <div class="modal-header border-secondary">
            <h5 class="modal-title">Detalhe do Log #${esc(r.id_log)}</h5>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
          </div>
          <div class="modal-body">
            <div class="row g-2 mb-3">
              <div class="col-6">
                <div class="texto-fraco small">Data/Hora</div>
                <div class="fw-semibold">${formatarDataHora(r.data_hora)}</div>
              </div>
              <div class="col-6">
                <div class="texto-fraco small">Executor</div>
                <div class="fw-semibold">${esc(r.nome_executor || r.user_id_executor || '—')}</div>
              </div>
              <div class="col-4">
                <div class="texto-fraco small">Entidade</div>
                <div>${badgeEntidade(r.entidade)}</div>
              </div>
              <div class="col-4">
                <div class="texto-fraco small">Acao</div>
                <div>${badgeAcao(r.acao)}</div>
              </div>
              <div class="col-4">
                <div class="texto-fraco small">IP</div>
                <div class="fw-semibold">${esc(r.ip || '—')}</div>
              </div>
            </div>
            <div class="mb-3">
              <div class="texto-fraco small">Descricao</div>
              <div>${esc(r.descricao)}</div>
            </div>
            ${r.id_entidade ? `<div class="mb-3"><div class="texto-fraco small">ID da entidade</div><div class="fw-semibold">${esc(r.id_entidade)}</div></div>` : ''}
            <hr class="border-light opacity-10">
            <div class="row g-3">
              <div class="col-12 col-md-6">
                <div class="texto-fraco small mb-1">Dados ANTES</div>
                <div class="p-2 rounded" style="background:rgba(255,0,0,0.05);border:1px solid rgba(255,255,255,0.08);max-height:300px;overflow:auto;">
                  ${antesHtml}
                </div>
              </div>
              <div class="col-12 col-md-6">
                <div class="texto-fraco small mb-1">Dados DEPOIS</div>
                <div class="p-2 rounded" style="background:rgba(0,255,0,0.05);border:1px solid rgba(255,255,255,0.08);max-height:300px;overflow:auto;">
                  ${depoisHtml}
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer border-secondary">
            <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Fechar</button>
          </div>
        </div>
      </div>
    </div>`;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const el = document.getElementById('modalLogDetalhe');
    const modal = new bootstrap.Modal(el);
    el.addEventListener('hidden.bs.modal', () => { el.remove(); });
    modal.show();
  }

  function formatarJSON(obj) {
    if (!obj || typeof obj !== 'object') return `<span class="texto-fraco">${esc(String(obj))}</span>`;
    let html = '<table class="table table-dark table-sm table-borderless mb-0 small">';
    for (const [chave, valor] of Object.entries(obj)) {
      html += `<tr><td class="texto-fraco" style="width:40%">${esc(chave)}</td><td>${esc(valor != null ? String(valor) : '—')}</td></tr>`;
    }
    html += '</table>';
    return html;
  }

  // ---- eventos ----
  btnBuscar.addEventListener('click', () => carregarLogs(1));

  // Enter na busca
  inputBusca.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { e.preventDefault(); carregarLogs(1); }
  });

  // Paginacao
  navPaginacao.addEventListener('click', (e) => {
    const link = e.target.closest('[data-log-pagina]');
    if (!link) return;
    e.preventDefault();
    const pg = parseInt(link.dataset.logPagina, 10);
    if (pg >= 1) carregarLogs(pg);
  });

  // Detalhe
  tbody.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-log-detalhe]');
    if (!btn) return;
    abrirDetalhe(btn.dataset.logDetalhe);
  });

  // ---- datas padrao (60 dias atras ate hoje) ----
  function preencherDatasPadrao() {
    const hoje = new Date();
    const inicio = new Date();
    inicio.setDate(inicio.getDate() - 60);
    const pad = (n) => String(n).padStart(2, '0');
    const fmtIso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    if (!inputDataInicio.value) inputDataInicio.value = fmtIso(inicio);
    if (!inputDataFim.value)    inputDataFim.value    = fmtIso(hoje);
  }

  // ---- exposicao global (para painel.js) ----
  window.logAtividadesCarregar = function () {
    filtrosPopulados = false;
    preencherDatasPadrao();
    carregarLogs(1);
  };

  // Em pagina dedicada (log.php) nao existe o SPA do index (#abaDashboard).
  // Nesse caso carrega sozinho ao abrir. No index.php o carregamento e sob
  // demanda: painel.js chama logAtividadesCarregar ao abrir a aba.
  if (!document.getElementById('abaDashboard')) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', window.logAtividadesCarregar);
    } else {
      window.logAtividadesCarregar();
    }
  }
})();
