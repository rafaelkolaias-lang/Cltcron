/* aba-auditoria.js — Auditoria de apps suspeitos + usuários com flag
 *
 * Fluxo:
 *   - Aba #abaAuditoria contém dois blocos:
 *       1) Tabela de usuários com flag (tbody #tbodyAuditoriaUsuarios)
 *       2) CRUD de apps suspeitos (tbody #tbodyAuditoriaApps)
 *   - Modal #modalAppSuspeito é usado tanto para criar quanto editar.
 *   - window.PainelAbaAuditoria.renderizarAbaAuditoria() — chamada por painel.js
 *     quando a aba fica visível.
 */
(function () {
  'use strict';

  const API = './commands/auditoria/';

  // ---------- Helpers ----------
  function esc(s) {
    if (s === null || s === undefined) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function formatarData(s) {
    if (!s) return '—';
    const d = new Date(String(s).replace(' ', 'T'));
    if (isNaN(d.getTime())) return esc(s);
    return d.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' });
  }

  async function requisitar(url, metodo, corpo) {
    const opts = { method: metodo || 'GET', credentials: 'same-origin', headers: {} };
    if (corpo !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(corpo);
    }
    const r = await fetch(url, opts);
    let json = null;
    try { json = await r.json(); } catch (_) {}
    if (!r.ok || !json || json.ok !== true) {
      const msg = (json && json.mensagem) ? json.mensagem : ('HTTP ' + r.status);
      const det = (json && json.dados && json.dados.erro) ? ' — ' + json.dados.erro : '';
      throw new Error(msg + det);
    }
    return json.dados;
  }

  function alerta(tipo, titulo, msg) {
    if (typeof window.mostrarAlerta === 'function') {
      window.mostrarAlerta(tipo, titulo, msg);
      return;
    }
    // fallback mínimo
    console[tipo === 'erro' ? 'error' : 'log']('[auditoria]', titulo, msg);
  }

  // ---------- Estado ----------
  const estado = {
    apps: [],
    usuariosFlag: [],
    geradoEm: '',
    appsAtivos: 0,
    incluirInativos: false,
    carregando: false,
  };

  // Cache compartilhado entre módulos — outras abas consultam via
  // window.PainelAbaAuditoria.obterFlagsMap() para exibir bandeiras sem
  // refazer o fetch.
  const CACHE_TTL_MS = 60 * 1000; // 1 min
  let _flagsCache = { carregadoEm: 0, mapa: {} };

  async function garantirFlagsMap(forcar) {
    const agora = Date.now();
    if (!forcar && _flagsCache.carregadoEm && (agora - _flagsCache.carregadoEm) < CACHE_TTL_MS) {
      return _flagsCache.mapa;
    }
    try {
      const dados = await requisitar(API + 'flags_usuarios.php');
      const lista = Array.isArray(dados?.usuarios) ? dados.usuarios : [];
      const mapa = {};
      lista.forEach(u => {
        if (!u.user_id) return;
        mapa[u.user_id] = {
          tem_flag_7dias: !!u.tem_flag_7dias,
          apps_detectados: Array.isArray(u.apps_detectados) ? u.apps_detectados : [],
        };
      });
      _flagsCache = { carregadoEm: agora, mapa };
      _atualizarIconeAbaAuditoria();
    } catch (e) {
      // falha silenciosa — o painel funciona mesmo sem bandeira
      console.warn('[auditoria] falha ao carregar flags para cache:', e?.message || e);
    }
    return _flagsCache.mapa;
  }

  function invalidarCacheFlags() {
    _flagsCache = { carregadoEm: 0, mapa: {} };
  }

  function obterFlagUsuarioSync(user_id) {
    return _flagsCache.mapa[user_id] || null;
  }

  // Mostra o ícone 🚨 no link "Auditoria" da navbar SOMENTE quando existir
  // ao menos um usuário com bandeira ativa (uso nos últimos 7 dias).
  function _atualizarIconeAbaAuditoria() {
    const icone = document.getElementById('linkAbaAuditoriaIcone');
    if (!icone) return;
    const temAlgum = Object.values(_flagsCache.mapa || {}).some(
      (u) => u && u.tem_flag_7dias === true
    );
    icone.classList.toggle('d-none', !temAlgum);
  }

  // ===========================================================
  // BLOCO 1 — Usuários com flag
  // ===========================================================
  async function carregarUsuariosFlag() {
    try {
      const dados = await requisitar(API + 'flags_usuarios.php');
      estado.usuariosFlag = Array.isArray(dados?.usuarios) ? dados.usuarios : [];
      estado.geradoEm = dados?.gerado_em || '';
      estado.appsAtivos = Number(dados?.apps_suspeitos_ativos || 0);

      // Atualiza cache compartilhado para outros módulos
      const mapa = {};
      estado.usuariosFlag.forEach(u => {
        if (!u.user_id) return;
        mapa[u.user_id] = {
          tem_flag_7dias: !!u.tem_flag_7dias,
          apps_detectados: Array.isArray(u.apps_detectados) ? u.apps_detectados : [],
        };
      });
      _flagsCache = { carregadoEm: Date.now(), mapa };
      _atualizarIconeAbaAuditoria();
      // Dispara evento para quem quiser escutar
      try { window.dispatchEvent(new CustomEvent('painel:flags-auditoria-atualizadas')); } catch (_) {}
    } catch (e) {
      estado.usuariosFlag = [];
      alerta('erro', 'Auditoria', 'Falha ao carregar flags: ' + (e?.message || e));
    }
    renderizarUsuariosFlag();
  }

  function renderizarUsuariosFlag() {
    const tb = document.getElementById('tbodyAuditoriaUsuarios');
    const badge = document.getElementById('auditoriaBadgeContadorUsuarios');
    const txtGerado = document.getElementById('auditoriaGeradoEm');
    if (!tb) return;

    if (txtGerado) txtGerado.textContent = estado.geradoEm ? formatarData(estado.geradoEm) : '—';
    if (badge) badge.textContent = `${estado.usuariosFlag.length} usuário${estado.usuariosFlag.length === 1 ? '' : 's'}`;

    if (!estado.usuariosFlag.length) {
      tb.innerHTML = '<tr><td colspan="7" class="texto-fraco">Nenhum usuário com registro de app suspeito.</td></tr>';
      return;
    }

    // Ordena: flagados nos últimos 7d primeiro, depois por total de horas desc
    const lista = [...estado.usuariosFlag].sort((a, b) => {
      if (a.tem_flag_7dias !== b.tem_flag_7dias) return a.tem_flag_7dias ? -1 : 1;
      const ta = (a.apps_detectados || []).reduce((s, x) => s + Number(x.segundos_totais || 0), 0);
      const tb_ = (b.apps_detectados || []).reduce((s, x) => s + Number(x.segundos_totais || 0), 0);
      return tb_ - ta;
    });

    tb.innerHTML = lista.map(u => {
      const apps = Array.isArray(u.apps_detectados) ? u.apps_detectados : [];
      const totalSeg = apps.reduce((s, x) => s + Number(x.segundos_totais || 0), 0);
      const totalSess = apps.reduce((s, x) => s + Number(x.sessoes || 0), 0);
      const totalHoras = formatarHHMM(totalSeg);
      const ultimoUso = apps.reduce((acc, x) => {
        const t = x.ultimo_uso ? new Date(String(x.ultimo_uso).replace(' ', 'T')).getTime() : 0;
        return t > acc ? t : acc;
      }, 0);
      const ultimoUsoTxt = ultimoUso ? new Date(ultimoUso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';

      const bandeira = u.tem_flag_7dias ? '<span title="Uso nos últimos 7 dias" style="font-size:1.1rem">🚩</span>' : '';

      const listaApps = apps.map(a => {
        const marca7 = a.usado_ultimos_7d ? ' <span title="Últimos 7 dias" class="badge bg-danger-subtle text-danger-emphasis">7d</span>' : '';
        return `
          <div class="small" style="line-height:1.35">
            <strong>${esc(a.nome_app_real)}</strong>${marca7}
            <span class="texto-fraco">· ${a.sessoes} sess · ${esc(a.horas_abertas)}</span>
          </div>`;
      }).join('');

      return `
        <tr data-user-id="${esc(u.user_id)}">
          <td class="text-center">${bandeira}</td>
          <td><strong>${esc(u.nome_exibicao || u.user_id)}</strong><div class="texto-fraco small">${esc(u.user_id)}</div></td>
          <td>${listaApps || '<span class="texto-fraco">—</span>'}</td>
          <td class="text-end"><strong>${esc(totalHoras)}</strong></td>
          <td class="text-end">${totalSess}</td>
          <td class="text-end small">${esc(ultimoUsoTxt)}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-light" type="button" data-acao="abrir-gestao" data-user-id="${esc(u.user_id)}">Abrir gestão</button>
          </td>
        </tr>`;
    }).join('');
  }

  function formatarHHMM(seg) {
    seg = Math.max(0, Number(seg) || 0);
    const h = Math.floor(seg / 3600);
    const m = Math.floor((seg % 3600) / 60);
    return `${h}h${String(m).padStart(2, '0')}m`;
  }

  // ===========================================================
  // BLOCO 2 — CRUD de apps suspeitos
  // ===========================================================
  async function carregarApps() {
    try {
      const url = API + 'listar_apps_suspeitos.php' + (estado.incluirInativos ? '?incluir_inativos=1' : '');
      const dados = await requisitar(url);
      estado.apps = Array.isArray(dados) ? dados : [];
    } catch (e) {
      estado.apps = [];
      alerta('erro', 'Auditoria', 'Falha ao listar apps: ' + (e?.message || e));
    }
    renderizarApps();
  }

  function renderizarApps() {
    const tb = document.getElementById('tbodyAuditoriaApps');
    const badge = document.getElementById('auditoriaBadgeContadorApps');
    if (!tb) return;

    if (badge) {
      const ativos = estado.apps.filter(a => a.ativo === 1).length;
      badge.textContent = `${ativos} ativo${ativos === 1 ? '' : 's'}${estado.incluirInativos ? ` / ${estado.apps.length} total` : ''}`;
    }

    if (!estado.apps.length) {
      tb.innerHTML = '<tr><td colspan="6" class="texto-fraco">Nenhum app cadastrado.</td></tr>';
      return;
    }

    tb.innerHTML = estado.apps.map(a => {
      const inativoClasse = a.ativo === 1 ? '' : 'style="opacity:.5"';
      const statusBadge = a.ativo === 1
        ? '<span class="badge bg-success-subtle text-success-emphasis">Ativo</span>'
        : '<span class="badge bg-secondary-subtle text-secondary-emphasis">Inativo</span>';
      const botaoToggle = a.ativo === 1
        ? `<button class="btn btn-sm btn-outline-danger" type="button" data-acao="desativar" data-id="${a.id}" title="Desativar">Desativar</button>`
        : `<button class="btn btn-sm btn-outline-success" type="button" data-acao="reativar" data-id="${a.id}" title="Reativar">Reativar</button>`;
      return `
        <tr data-id="${a.id}" ${inativoClasse}>
          <td><code>${esc(a.nome_app)}</code></td>
          <td class="small">${esc(a.motivo || '')}</td>
          <td class="text-center">${statusBadge}</td>
          <td class="small">${esc(a.criado_por || '—')}</td>
          <td class="small">${formatarData(a.atualizado_em)}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-light me-1" type="button" data-acao="editar" data-id="${a.id}">Editar</button>
            ${botaoToggle}
          </td>
        </tr>`;
    }).join('');
  }

  // ---------- Modal: abrir / salvar ----------
  function abrirModalNovo() {
    document.getElementById('appSuspeitoId').value = '';
    document.getElementById('appSuspeitoNome').value = '';
    document.getElementById('appSuspeitoMotivo').value = '';
    document.getElementById('appSuspeitoAtivo').checked = true;
    document.getElementById('modalAppSuspeitoTitulo').textContent = 'Novo app suspeito';
    const modalEl = document.getElementById('modalAppSuspeito');
    window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
    setTimeout(() => document.getElementById('appSuspeitoNome').focus(), 150);
  }

  function abrirModalEditar(id) {
    const app = estado.apps.find(a => Number(a.id) === Number(id));
    if (!app) return;
    document.getElementById('appSuspeitoId').value = String(app.id);
    document.getElementById('appSuspeitoNome').value = app.nome_app || '';
    document.getElementById('appSuspeitoMotivo').value = app.motivo || '';
    document.getElementById('appSuspeitoAtivo').checked = Number(app.ativo) === 1;
    document.getElementById('modalAppSuspeitoTitulo').textContent = 'Editar app suspeito';
    const modalEl = document.getElementById('modalAppSuspeito');
    window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  async function salvarAppDoModal() {
    const id = Number(document.getElementById('appSuspeitoId').value || 0);
    const nome_app = (document.getElementById('appSuspeitoNome').value || '').trim();
    const motivo = (document.getElementById('appSuspeitoMotivo').value || '').trim();
    const ativo = document.getElementById('appSuspeitoAtivo').checked ? 1 : 0;

    if (!nome_app || nome_app.length < 2) {
      alerta('aviso', 'Validação', 'Nome do app inválido (mínimo 2 caracteres).');
      return;
    }

    const corpo = { nome_app, motivo, ativo };
    if (id > 0) corpo.id = id;

    try {
      await requisitar(API + 'salvar_app_suspeito.php', 'POST', corpo);
      const modalEl = document.getElementById('modalAppSuspeito');
      window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
      alerta('sucesso', 'Auditoria', id > 0 ? 'App atualizado.' : 'App cadastrado.');
      await carregarApps();
      // Recarrega também as flags — o app novo pode ativar alerta pra alguém
      await carregarUsuariosFlag();
    } catch (e) {
      alerta('erro', 'Auditoria', e?.message || String(e));
    }
  }

  async function desativarApp(id) {
    if (!confirm('Desativar este app? Ele deixará de levantar alertas, mas o histórico continua registrado.')) return;
    try {
      await requisitar(API + 'excluir_app_suspeito.php', 'POST', { id: Number(id) });
      alerta('sucesso', 'Auditoria', 'App desativado.');
      await carregarApps();
      await carregarUsuariosFlag();
    } catch (e) {
      alerta('erro', 'Auditoria', e?.message || String(e));
    }
  }

  async function reativarApp(id) {
    // Reativar = salvar com ativo=1
    const app = estado.apps.find(a => Number(a.id) === Number(id));
    if (!app) return;
    try {
      await requisitar(API + 'salvar_app_suspeito.php', 'POST', {
        id: Number(id),
        nome_app: app.nome_app,
        motivo: app.motivo || '',
        ativo: 1,
      });
      alerta('sucesso', 'Auditoria', 'App reativado.');
      await carregarApps();
      await carregarUsuariosFlag();
    } catch (e) {
      alerta('erro', 'Auditoria', e?.message || String(e));
    }
  }

  // ===========================================================
  // Eventos
  // ===========================================================
  // Link "Ver aba Auditoria →" dentro da Gestão do Usuário
  function ligarLinkGestaoParaAuditoria() {
    const link = document.getElementById('linkIrAuditoriaGestao');
    if (!link || link.dataset.ligado === '1') return;
    link.dataset.ligado = '1';
    link.addEventListener('click', (ev) => {
      ev.preventDefault();
      if (typeof window.PainelNucleo_trocarAba === 'function') {
        window.PainelNucleo_trocarAba('abaAuditoria');
      }
    });
  }

  function ligarEventos() {
    ligarLinkGestaoParaAuditoria();

    // Recarregar (bloco usuários)
    document.getElementById('auditoriaBotaoRecarregar')?.addEventListener('click', async () => {
      await renderizarAbaAuditoria();
    });

    // Novo app
    document.getElementById('auditoriaBotaoNovoApp')?.addEventListener('click', abrirModalNovo);

    // Incluir inativos
    document.getElementById('auditoriaIncluirInativos')?.addEventListener('change', async (e) => {
      estado.incluirInativos = !!e.target.checked;
      await carregarApps();
    });

    // Salvar no modal
    document.getElementById('botaoSalvarAppSuspeito')?.addEventListener('click', salvarAppDoModal);

    // Delegação: ações nas linhas de apps
    document.getElementById('tbodyAuditoriaApps')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-acao]');
      if (!btn) return;
      const id = Number(btn.getAttribute('data-id') || 0);
      const acao = btn.getAttribute('data-acao');
      if (acao === 'editar') abrirModalEditar(id);
      else if (acao === 'desativar') desativarApp(id);
      else if (acao === 'reativar') reativarApp(id);
    });

    // Delegação: "abrir gestão" na linha de usuário
    document.getElementById('tbodyAuditoriaUsuarios')?.addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-acao="abrir-gestao"]');
      if (!btn) return;
      const user_id = btn.getAttribute('data-user-id') || '';
      if (!user_id) return;
      const fn = window.PainelAbaUsuarios?.abrirModalGestaoUsuario;
      if (typeof fn === 'function') {
        fn(user_id);
      } else {
        alerta('aviso', 'Navegação', 'Função de gestão não encontrada.');
      }
    });
  }

  // ===========================================================
  // Entry point
  // ===========================================================
  let inicializado = false;

  async function renderizarAbaAuditoria() {
    if (estado.carregando) return;
    estado.carregando = true;
    try {
      if (!inicializado) {
        ligarEventos();
        inicializado = true;
      }
      await Promise.all([carregarApps(), carregarUsuariosFlag()]);
    } finally {
      estado.carregando = false;
    }
  }

  // ===========================================================
  // Renderização de alertas na Gestão do Usuário
  // ===========================================================
  async function renderizarAlertasNaGestao(uid) {
    const host = document.getElementById('blocoAlertasAuditoria');
    const corpo = document.getElementById('alertasAuditoriaCorpo');
    if (!host || !corpo) return;

    if (!uid) {
      host.classList.add('d-none');
      return;
    }

    corpo.innerHTML = '<div class="texto-fraco small">Carregando…</div>';

    try {
      const [flagsResp, statsResp] = await Promise.all([
        requisitar(API + 'flags_usuarios.php?user_id=' + encodeURIComponent(uid)),
        requisitar(API + 'input_stats.php?user_id=' + encodeURIComponent(uid) + '&dias=15').catch(() => null),
      ]);

      const usuario = Array.isArray(flagsResp?.usuarios) ? flagsResp.usuarios.find(u => u.user_id === uid) : null;
      const apps = usuario && Array.isArray(usuario.apps_detectados) ? usuario.apps_detectados : [];
      const statsTotais = statsResp?.totais || { humano: 0, sintetico: 0, percentual_sintetico: 0 };
      const statsDias = Array.isArray(statsResp?.dias) ? statsResp.dias : [];

      const temApps = apps.length > 0;
      const temInputSintetico = Number(statsTotais.sintetico || 0) > 0;

      if (!temApps && !temInputSintetico) {
        host.classList.add('d-none');
        return;
      }

      host.classList.remove('d-none');

      // ── Bloco de métrica superior ───────────────────────────
      const iconeBandeira = (usuario && usuario.tem_flag_7dias)
        ? '<span style="font-size:1.2rem" title="Uso nos últimos 7 dias">🚩</span>'
        : '<span style="font-size:1.2rem; opacity:.5" title="Sem uso nos últimos 7 dias">📋</span>';

      const textoBandeira = (usuario && usuario.tem_flag_7dias)
        ? '<span class="badge bg-danger-subtle text-danger-emphasis">Ativo nos últimos 7 dias</span>'
        : '<span class="badge bg-secondary-subtle text-secondary-emphasis">Apenas histórico</span>';

      // Totais dos apps suspeitos
      const totalSeg = apps.reduce((s, x) => s + Number(x.segundos_totais || 0), 0);
      const totalSess = apps.reduce((s, x) => s + Number(x.sessoes || 0), 0);
      const primeiroUso = apps.reduce((acc, x) => {
        const t = x.primeiro_uso ? new Date(String(x.primeiro_uso).replace(' ', 'T')).getTime() : Infinity;
        return t < acc ? t : acc;
      }, Infinity);
      const ultimoUso = apps.reduce((acc, x) => {
        const t = x.ultimo_uso ? new Date(String(x.ultimo_uso).replace(' ', 'T')).getTime() : 0;
        return t > acc ? t : acc;
      }, 0);

      // ── Card de input automatizado (métrica Fase 2) ────────
      const cardInputSintetico = temInputSintetico
        ? `
          <article class="cartao-grafite p-3 mb-3" style="border-left:3px solid var(--bs-danger,#dc3545); background:rgba(220,53,69,.08)">
            <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
              <div>
                <div class="texto-fraco small">⚠️ Input automatizado detectado (hooks low-level)</div>
                <div class="h5 mb-0"><strong>${formatarHHMM(statsTotais.sintetico)}</strong>
                  <span class="texto-fraco small ms-2">de ${formatarHHMM(Number(statsTotais.humano) + Number(statsTotais.sintetico))} totais</span>
                </div>
                <div class="small" style="color:#ff8a95">
                  ${Number(statsTotais.percentual_sintetico).toFixed(1)}% do input desse usuário foi gerado por software
                </div>
              </div>
              <div id="chartInputStats_${esc(uid)}" style="width:min(520px, 60vw); height:140px"></div>
            </div>
            <div class="texto-fraco small mt-1">
              Eventos marcados com <code>LLMHF_INJECTED</code> pelo Windows — cliques/teclas gerados por software, não por hardware físico.
              Últimos 15 dias. A detecção não depende do nome do processo.
            </div>
          </article>`
        : '';

      // ── Tabela de processos (Fase 1) ───────────────────────
      const rows = apps.map(a => {
        const marca7 = a.usado_ultimos_7d
          ? '<span class="badge bg-danger-subtle text-danger-emphasis ms-1">7d</span>'
          : '';
        return `
          <tr>
            <td><code>${esc(a.nome_app_real)}</code>${marca7}</td>
            <td class="small texto-fraco">${esc(a.motivo || '')}</td>
            <td class="text-end">${a.sessoes}</td>
            <td class="text-end"><strong>${esc(a.horas_abertas)}</strong></td>
            <td class="small">${formatarData(a.primeiro_uso)}</td>
            <td class="small">${formatarData(a.ultimo_uso)}</td>
          </tr>`;
      }).join('');

      const blocoApps = temApps ? `
        <div class="mb-2">
          <div class="d-flex justify-content-between align-items-start flex-wrap gap-2 mb-2">
            <div class="d-flex align-items-center gap-2">
              ${iconeBandeira}
              ${textoBandeira}
            </div>
            <div class="d-flex gap-3 small texto-fraco">
              <div>Primeiro uso: <strong class="text-white">${formatarData(isFinite(primeiroUso) ? new Date(primeiroUso).toISOString().replace('T', ' ').slice(0, 19) : '')}</strong></div>
              <div>Último uso: <strong class="text-white">${formatarData(ultimoUso ? new Date(ultimoUso).toISOString().replace('T', ' ').slice(0, 19) : '')}</strong></div>
              <div>Total aberto: <strong class="text-white">${formatarHHMM(totalSeg)}</strong> em ${totalSess} sessões</div>
            </div>
          </div>
          <div class="table-responsive">
            <table class="table table-dark table-borderless align-middle tabela-suave mb-0">
              <thead>
                <tr class="texto-fraco small">
                  <th style="min-width:220px;">Processo detectado</th>
                  <th style="min-width:180px;">Motivo</th>
                  <th class="text-end" style="min-width:80px;">Sessões</th>
                  <th class="text-end" style="min-width:100px;">Horas abertas</th>
                  <th style="min-width:140px;">Primeiro uso</th>
                  <th style="min-width:140px;">Último uso</th>
                </tr>
              </thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      ` : '';

      corpo.innerHTML = cardInputSintetico + blocoApps;

      // Renderiza gráfico se houver input sintético detectado
      if (temInputSintetico) {
        setTimeout(() => _renderGraficoInputStats(`chartInputStats_${uid}`, statsDias), 50);
      }
    } catch (e) {
      corpo.innerHTML = `<div class="text-danger small">Erro ao carregar alertas: ${esc(e?.message || String(e))}</div>`;
    }
  }

  // ── Gráfico compacto de input humano vs sintético por dia ──
  function _renderGraficoInputStats(containerId, dias) {
    const el = document.getElementById(containerId);
    if (!el || !window.echarts) return;
    const chart = window.echarts.getInstanceByDom(el) || window.echarts.init(el, null, { renderer: 'canvas' });
    const rotulos = dias.map(d => {
      const dt = new Date(String(d.referencia_data) + 'T00:00:00');
      return isNaN(dt.getTime()) ? String(d.referencia_data) : dt.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    });
    const humano = dias.map(d => Math.round(Number(d.humano || 0) / 3600 * 100) / 100);
    const sintet = dias.map(d => Math.round(Number(d.sintetico || 0) / 3600 * 100) / 100);

    chart.setOption({
      grid: { left: 32, right: 8, top: 8, bottom: 24 },
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(15,20,35,.95)',
        borderColor: 'rgba(255,255,255,.1)',
        textStyle: { color: '#e2e8f0', fontSize: 11 },
        formatter: (params) => {
          const dia = params[0]?.axisValueLabel || '';
          const linhas = params.map(p => `${p.marker} ${p.seriesName}: <strong>${p.value}h</strong>`).join('<br>');
          return `<div class="small"><strong>${dia}</strong><br>${linhas}</div>`;
        },
      },
      xAxis: {
        type: 'category', data: rotulos,
        axisLabel: { color: 'rgba(255,255,255,.5)', fontSize: 9 },
        axisLine: { lineStyle: { color: 'rgba(255,255,255,.15)' } },
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: 'rgba(255,255,255,.4)', fontSize: 9, formatter: (v) => v + 'h' },
        splitLine: { lineStyle: { color: 'rgba(255,255,255,.05)' } },
      },
      series: [
        { name: 'Humano', type: 'bar', stack: 'total', data: humano, itemStyle: { color: '#33c5a1' }, barWidth: '55%' },
        { name: 'Sintético', type: 'bar', stack: 'total', data: sintet, itemStyle: { color: '#e62117' }, barWidth: '55%' },
      ],
    }, true);
  }

  // Expõe API pública
  window.PainelAbaAuditoria = {
    renderizarAbaAuditoria,
    recarregarTudo: renderizarAbaAuditoria,
    garantirFlagsMap,
    invalidarCacheFlags,
    obterFlagUsuarioSync,
    renderizarAlertasNaGestao,
  };

  // Ao carregar o DOM, pré-carrega o cache (em background) para que as
  // bandeiras apareçam já na primeira renderização do Dashboard e da aba
  // Usuários, sem esperar o admin abrir a aba de Auditoria.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      ligarLinkGestaoParaAuditoria();
      garantirFlagsMap().catch(() => { /* silencioso */ });
    });
  } else {
    ligarLinkGestaoParaAuditoria();
    garantirFlagsMap().catch(() => { /* silencioso */ });
  }
})();
