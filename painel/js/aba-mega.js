/* aba-mega.js — Configuração de upload obrigatório no MEGA por canal e usuário.
 *
 * Três blocos independentes na #abaMega:
 *   1) Canal config: pasta raiz no MEGA + flag upload_ativo por atividade.
 *   2) Campos exigidos: por (user_id, id_atividade), CRUD inline.
 *   3) Pastas lógicas: lista read-only, com filtro opcional por canal.
 *
 * Edição via linha inline (sem modal) — mantém o código curto e a UX direta.
 */
(function () {
  'use strict';

  const API = './commands/mega/';

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
    console[tipo === 'erro' ? 'error' : 'log']('[mega]', titulo, msg);
  }

  // ---------- Estado ----------
  const estado = {
    canais: [],
    usuarios: [],
    // Vem de /commands/atividades/listar.php — inclui usuarios[] por atividade.
    // Usado pra filtrar o select de canais do bloco "Campos por user+canal":
    // só mostra canais que o usuário selecionado tem atribuídos.
    atividadesComUsuarios: [],
    campos: [],
    pastas: [],
    modelosCampos: [], // templates globais (mega_campos_modelos)
    filtroUserId: '',
    filtroIdAtividade: 0,
    filtroCanalPastas: 0,
    filtroStatusPastas: '',
    filtroUpadoPor: '',
    buscaPastas: '',
    // Ordenação de colunas da tabela de pastas: { campo, direcao: 'asc'|'desc'|null }
    sortPastas: { campo: null, direcao: null },
  };

  // ===========================================================
  // BLOCO 1 — Configuração por canal
  // ===========================================================
  async function carregarCanais() {
    const tbody = document.getElementById('tbodyMegaCanais');
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>';

    try {
      const dados = await requisitar(API + 'canal_config_listar.php');
      estado.canais = Array.isArray(dados) ? dados : [];
      const badge = document.getElementById('megaBadgeCanais');
      if (badge) badge.textContent = String(estado.canais.length);
      renderizarCanais();
      // Filtro do bloco "Pastas lógicas" usa todos os canais; o do bloco
      // "Campos por user+canal" depende do user selecionado (separado).
      atualizarSelectCanaisPastas();
      atualizarSelectCanaisPorUsuario();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
  }

  // Lista de atividades com usuarios atribuídos (vem de atividades/listar.php).
  // Usada pra filtrar o select de canais por usuário no bloco "Campos".
  async function carregarAtividadesComUsuarios() {
    try {
      const dados = await requisitar('./commands/atividades/listar.php');
      estado.atividadesComUsuarios = (Array.isArray(dados) ? dados : [])
        .filter((a) => String(a.status || '').toLowerCase() !== 'cancelada');
      atualizarSelectCanaisPorUsuario();
    } catch (e) {
      console.warn('[mega] falha ao carregar atividades+usuarios:', e?.message || e);
    }
  }

  function renderizarCanais() {
    const tbody = document.getElementById('tbodyMegaCanais');
    if (!tbody) return;

    if (!estado.canais.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="texto-fraco">Nenhum canal cadastrado.</td></tr>';
      return;
    }

    tbody.innerHTML = estado.canais.map((c) => {
      const idA = c.id_atividade;
      const ativo = c.upload_ativo ? 'checked' : '';
      const inativoHint = String(c.status_atividade || '').toLowerCase() !== 'aberta'
        ? `<span class="badge bg-secondary ms-1" title="Status: ${esc(c.status_atividade)}">${esc(c.status_atividade)}</span>` : '';
      return `
        <tr data-id-atividade="${idA}">
          <td><strong>${esc(c.titulo_atividade)}</strong>${inativoHint}</td>
          <td>
            <input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-pasta-input"
                   placeholder="ex: Canal Astronomia"
                   value="${esc(c.nome_pasta_mega)}" maxlength="255">
          </td>
          <td class="text-center">
            <div class="form-check form-switch d-inline-block">
              <input class="form-check-input mega-ativo-input" type="checkbox" ${ativo}>
            </div>
          </td>
          <td class="texto-fraco small">${formatarData(c.atualizado_em)}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-light mega-salvar-canal" type="button">Salvar</button>
          </td>
        </tr>`;
    }).join('');

    tbody.querySelectorAll('.mega-salvar-canal').forEach((btn) => {
      btn.addEventListener('click', async (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const idA = parseInt(tr.getAttribute('data-id-atividade'), 10);
        const nome = (tr.querySelector('.mega-pasta-input')?.value || '').trim();
        const ativo = !!tr.querySelector('.mega-ativo-input')?.checked;
        try {
          await requisitar(API + 'canal_config_salvar.php', 'POST', {
            id_atividade: idA, nome_pasta_mega: nome, upload_ativo: ativo,
          });
          alerta('sucesso', 'MEGA', 'Configuração salva.');
          carregarCanais();
        } catch (e) {
          alerta('erro', 'MEGA', e.message);
        }
      });
    });
  }

  // ===========================================================
  // BLOCO 2 — Campos por user + canal
  // ===========================================================
  async function carregarUsuarios() {
    try {
      const dados = await requisitar('./commands/usuarios/listar.php');
      const usuarios = Array.isArray(dados) ? dados : (Array.isArray(dados?.usuarios) ? dados.usuarios : []);
      estado.usuarios = usuarios.filter((u) =>
        String(u.status_conta || '').toLowerCase() === 'ativa' &&
        Number(u.ocultar_dashboard || 0) !== 1
      );
      atualizarSelectUsuarios();
    } catch (e) {
      console.warn('[mega] falha ao carregar usuarios:', e?.message || e);
    }
  }

  function atualizarSelectUsuarios() {
    const sel = document.getElementById('megaFiltroUser');
    if (!sel) return;
    const atual = sel.value;
    sel.innerHTML = '<option value="">Selecione um usuário…</option>' +
      estado.usuarios.map((u) => {
        const uid = u.user_id || '';
        const nome = u.nome_exibicao || uid;
        return `<option value="${esc(uid)}">${esc(nome)}</option>`;
      }).join('');
    if (atual && estado.usuarios.some((u) => String(u.user_id || '') === atual)) {
      sel.value = atual;
    } else if (atual) {
      estado.filtroUserId = '';
    }
  }

  // Bloco "Pastas lógicas cadastradas": filtro opcional, todos os canais.
  function atualizarSelectCanaisPastas() {
    const sel = document.getElementById('megaFiltroCanalPastas');
    if (!sel) return;
    const atual = sel.value;
    sel.innerHTML = '<option value="">Todos os canais</option>' +
      estado.canais.map((c) => `<option value="${c.id_atividade}">${esc(c.titulo_atividade)}</option>`).join('');
    if (atual) sel.value = atual;
  }

  // Bloco "Campos por user+canal": só mostra canais que o usuário selecionado
  // efetivamente tem atribuídos (via atividades_usuarios). Sem usuário, fica
  // desabilitado com placeholder. Usuário sem canais → mostra mensagem.
  function atualizarSelectCanaisPorUsuario() {
    const sel = document.getElementById('megaFiltroCanal');
    if (!sel) return;
    const userId = String(estado.filtroUserId || '').trim();
    const valorAtual = sel.value;

    if (!userId) {
      sel.innerHTML = '<option value="">Selecione um usuário primeiro…</option>';
      sel.disabled = true;
      estado.filtroIdAtividade = 0;
      return;
    }

    const canaisDoUsuario = estado.atividadesComUsuarios.filter((a) =>
      String(a.status || '').toLowerCase() !== 'cancelada' &&
      Array.isArray(a.usuarios) && a.usuarios.some((u) => String(u.user_id || '') === userId)
    );

    if (!canaisDoUsuario.length) {
      sel.innerHTML = '<option value="">Nenhum canal atribuído a este usuário</option>';
      sel.disabled = true;
      estado.filtroIdAtividade = 0;
      return;
    }

    sel.disabled = false;
    sel.innerHTML = '<option value="">Selecione um canal…</option>' +
      canaisDoUsuario.map((c) => `<option value="${c.id_atividade}">${esc(c.titulo)}</option>`).join('');

    // Preserva seleção anterior se ainda for válida pro novo user.
    if (valorAtual && canaisDoUsuario.some((c) => String(c.id_atividade) === valorAtual)) {
      sel.value = valorAtual;
    } else {
      estado.filtroIdAtividade = 0;
    }
  }

  async function carregarCampos() {
    const tbody = document.getElementById('tbodyMegaCampos');
    if (!tbody) return;

    if (!estado.filtroUserId || !estado.filtroIdAtividade) {
      tbody.innerHTML = '<tr><td colspan="8" class="texto-fraco">Selecione usuário e canal acima.</td></tr>';
      const b = document.getElementById('megaBadgeCampos');
      if (b) b.textContent = '—';
      const btn = document.getElementById('megaBotaoNovoCampo');
      if (btn) btn.disabled = true;
      atualizarBotoesModelos();
      return;
    }

    tbody.innerHTML = '<tr><td colspan="8" class="texto-fraco">Carregando…</td></tr>';

    try {
      const url = `${API}campos_listar.php?user_id=${encodeURIComponent(estado.filtroUserId)}&id_atividade=${estado.filtroIdAtividade}&incluir_inativos=1`;
      const dados = await requisitar(url);
      estado.campos = Array.isArray(dados) ? dados : [];
      const b = document.getElementById('megaBadgeCampos');
      if (b) b.textContent = String(estado.campos.filter(c => c.ativo).length);
      const btn = document.getElementById('megaBotaoNovoCampo');
      if (btn) btn.disabled = false;
      renderizarCampos();
      atualizarBotoesModelos();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="8" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
  }

  // Tipos de campo de upload (espelha MEGA_TIPOS_CAMPO no backend _comum.php).
  // Usado pro "verde compartilhado" (tipo='thumb') e pra listar arquivos da pasta
  // pro download direto no desktop.
  const MEGA_TIPOS = [
    { v: 'video',   t: 'Vídeo' },
    { v: 'projeto', t: 'Projeto' },
    { v: 'thumb',   t: 'Thumb' },
    { v: 'texto',   t: 'Texto' },
    { v: 'outro',   t: 'Outro' },
  ];
  function rotuloTipoCampo(v) {
    const m = MEGA_TIPOS.find((x) => x.v === v);
    return m ? m.t : 'Outro';
  }
  function opcoesTipoCampo(sel) {
    const atual = MEGA_TIPOS.some((x) => x.v === sel) ? sel : 'outro';
    return MEGA_TIPOS.map((x) => `<option value="${x.v}"${x.v === atual ? ' selected' : ''}>${x.t}</option>`).join('');
  }

  function linhaCampoEditavel(campo) {
    // Defaults p/ "novo campo": extensões vazias = qualquer; quantidade 1.
    const c = campo || { id_campo: 0, label_campo: '', tipo: 'outro', extensoes_permitidas: '', quantidade_maxima: 1, obrigatorio: true, ordem: 0, ativo: true };
    // qty=0 é válido (= ilimitado). Não usar `|| 1` (truthy coercion zeraria 0).
    const qtdAtual = (c.quantidade_maxima === undefined || c.quantidade_maxima === null) ? 1 : c.quantidade_maxima;
    return `
      <tr data-id-campo="${c.id_campo || 0}" data-modo="edicao">
        <td><input type="number" class="form-control form-control-sm bg-transparent text-white border-secondary mega-campo-ordem" value="${c.ordem || 0}" min="0" style="width:70px;"></td>
        <td><input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-campo-label" value="${esc(c.label_campo)}" placeholder="ex: Vídeo final" maxlength="120"></td>
        <td>
          <select class="form-select form-select-sm bg-transparent text-white border-secondary mega-campo-tipo" style="min-width:110px;">${opcoesTipoCampo(c.tipo || 'outro')}</select>
        </td>
        <td>
          <input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-campo-ext" value="${esc(c.extensoes_permitidas || '')}" placeholder="vazio = qualquer arquivo" maxlength="255">
        </td>
        <td class="text-center">
          <input type="number" class="form-control form-control-sm bg-transparent text-white border-secondary mega-campo-qtd" value="${qtdAtual}" min="0" max="100" title="0 = ilimitado" style="width:70px;display:inline-block;">
        </td>
        <td class="text-center"><input type="checkbox" class="form-check-input mega-campo-obrig" ${c.obrigatorio ? 'checked' : ''}></td>
        <td class="text-center"><input type="checkbox" class="form-check-input mega-campo-ativo" ${c.ativo ? 'checked' : ''}></td>
        <td class="text-end">
          <button class="btn btn-sm btn-light mega-campo-confirmar" type="button">Salvar</button>
          <button class="btn btn-sm btn-outline-light mega-campo-cancelar" type="button">Cancelar</button>
        </td>
      </tr>`;
  }

  function linhaCampoLeitura(c) {
    const ext = c.extensoes_permitidas ? esc(c.extensoes_permitidas) : '<span class="texto-fraco">qualquer</span>';
    const qtd = (parseInt(c.quantidade_maxima, 10) || 0) === 0
      ? '<span class="texto-fraco">ilim.</span>'
      : c.quantidade_maxima;
    const obrig = c.obrigatorio ? '<span class="badge bg-warning text-dark">SIM</span>' : '<span class="badge bg-secondary">não</span>';
    const ativo = c.ativo ? '<span class="badge bg-success">ativo</span>' : '<span class="badge bg-secondary">inativo</span>';
    const tipoBadge = (c.tipo && c.tipo !== 'outro')
      ? `<span class="badge bg-info text-dark">${esc(rotuloTipoCampo(c.tipo))}</span>`
      : '<span class="texto-fraco">—</span>';
    return `
      <tr data-id-campo="${c.id_campo}" data-modo="leitura" ${c.ativo ? '' : 'style="opacity:0.55;"'}>
        <td>${c.ordem}</td>
        <td><strong>${esc(c.label_campo)}</strong></td>
        <td>${tipoBadge}</td>
        <td>${ext}</td>
        <td class="text-center">${qtd}</td>
        <td class="text-center">${obrig}</td>
        <td class="text-center">${ativo}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-light mega-campo-editar" type="button">Editar</button>
          <button class="btn btn-sm btn-outline-danger mega-campo-excluir" type="button" title="Desativar">×</button>
        </td>
      </tr>`;
  }

  function renderizarCampos() {
    const tbody = document.getElementById('tbodyMegaCampos');
    if (!tbody) return;

    if (!estado.campos.length) {
      tbody.innerHTML = `
        <tr><td colspan="8" class="texto-fraco">
          Nenhum campo cadastrado para esse usuário neste canal. Clique em <strong>+ Novo campo</strong>.
        </td></tr>`;
      bindCamposActions();
      return;
    }

    tbody.innerHTML = estado.campos.map(linhaCampoLeitura).join('');
    bindCamposActions();
  }

  function bindCamposActions() {
    const tbody = document.getElementById('tbodyMegaCampos');
    if (!tbody) return;

    tbody.querySelectorAll('.mega-campo-editar').forEach((btn) => {
      btn.addEventListener('click', (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const id = parseInt(tr.getAttribute('data-id-campo'), 10);
        const c = estado.campos.find((x) => x.id_campo === id);
        if (!c) return;
        tr.outerHTML = linhaCampoEditavel(c);
        bindCamposActions();
      });
    });

    tbody.querySelectorAll('.mega-campo-excluir').forEach((btn) => {
      btn.addEventListener('click', async (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const id = parseInt(tr.getAttribute('data-id-campo'), 10);
        if (!id || !confirm('Desativar este campo? (Soft-delete)')) return;
        try {
          await requisitar(API + 'campos_excluir.php', 'POST', { id_campo: id });
          carregarCampos();
        } catch (e) {
          alerta('erro', 'MEGA', e.message);
        }
      });
    });

    tbody.querySelectorAll('.mega-campo-cancelar').forEach((btn) => {
      btn.addEventListener('click', () => carregarCampos());
    });

    tbody.querySelectorAll('.mega-campo-confirmar').forEach((btn) => {
      btn.addEventListener('click', async (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const id = parseInt(tr.getAttribute('data-id-campo'), 10) || 0;
        const payload = {
          id_campo: id,
          user_id: estado.filtroUserId,
          id_atividade: estado.filtroIdAtividade,
          label_campo: tr.querySelector('.mega-campo-label')?.value?.trim() || '',
          tipo: tr.querySelector('.mega-campo-tipo')?.value || 'outro',
          extensoes_permitidas: tr.querySelector('.mega-campo-ext')?.value?.trim() || '',
          // 0 = ilimitado (válido). Math.max evita negativos; sem `|| 1` pra não zerar 0.
          quantidade_maxima: Math.max(0, parseInt(tr.querySelector('.mega-campo-qtd')?.value, 10) || 0),
          obrigatorio: !!tr.querySelector('.mega-campo-obrig')?.checked,
          ordem: parseInt(tr.querySelector('.mega-campo-ordem')?.value, 10) || 0,
          ativo: !!tr.querySelector('.mega-campo-ativo')?.checked,
        };
        if (!payload.label_campo) {
          alerta('erro', 'MEGA', 'Label do campo é obrigatório.');
          return;
        }
        try {
          await requisitar(API + 'campos_salvar.php', 'POST', payload);
          carregarCampos();
        } catch (e) {
          alerta('erro', 'MEGA', e.message);
        }
      });
    });
  }

  // ===========================================================
  // BLOCO 2.5 — Modelos reutilizáveis de campos (templates globais)
  // ===========================================================
  // Atalho de preenchimento: admin salva valores comuns como modelo e aplica
  // numa linha editável de outro user/canal. Aplicar NÃO grava — só insere a
  // linha pré-preenchida; o admin ainda precisa clicar em "Salvar" pra
  // persistir o campo daquele user+canal.
  async function carregarModelosCampos() {
    try {
      const dados = await requisitar(API + 'campos_modelos_listar.php');
      estado.modelosCampos = Array.isArray(dados) ? dados : [];
    } catch (e) {
      estado.modelosCampos = [];
      console.warn('[mega] falha ao carregar modelos de campo:', e?.message || e);
    }
    renderizarTabelaModelos();
    atualizarBotoesModelos();
  }

  function atualizarBotoesModelos() {
    const btnUsar = document.getElementById('megaBotaoUsarModelo');
    if (btnUsar) {
      btnUsar.disabled = !(estado.filtroUserId && estado.filtroIdAtividade && estado.modelosCampos.length);
    }
  }

  // Popup "Usar modelo existente": lista os modelos com checkbox; ao salvar,
  // adiciona TODOS os marcados de uma vez como campos do usuário+canal atual.
  function abrirModalUsarModelos() {
    if (!estado.filtroUserId || !estado.filtroIdAtividade) {
      alerta('erro', 'MEGA', 'Selecione um usuário e um canal antes de usar modelos.');
      return;
    }
    const lista = document.getElementById('modalUsarModelosLista');
    const modalEl = document.getElementById('modalUsarModelos');
    if (!lista || !modalEl) return;

    if (!estado.modelosCampos.length) {
      lista.innerHTML = '<div class="texto-fraco small">Nenhum modelo cadastrado. Crie modelos na tabela "Modelos de campo" abaixo.</div>';
    } else {
      // Marca os labels que o usuário JÁ tem nesse canal (pra não duplicar).
      const jaTemLabels = new Set(
        estado.campos.filter((c) => c.ativo)
          .map((c) => String(c.label_campo || '').trim().toLowerCase())
      );
      lista.innerHTML = estado.modelosCampos.map((m) => {
        const jaTem = jaTemLabels.has(String(m.label_campo || '').trim().toLowerCase());
        const tipoTxt = (m.tipo && m.tipo !== 'outro') ? rotuloTipoCampo(m.tipo) : '—';
        const ext = m.extensoes_permitidas || 'qualquer';
        return `
          <div class="form-check d-flex align-items-start gap-2 py-1">
            <input class="form-check-input mega-modelo-check" type="checkbox" value="${m.id_modelo}" id="mum_${m.id_modelo}" ${jaTem ? '' : 'checked'}>
            <label class="form-check-label small" for="mum_${m.id_modelo}">
              <strong>${esc(m.nome_modelo)}</strong>
              <span class="texto-fraco">— "${esc(m.label_campo)}" · ${esc(tipoTxt)} · ${esc(ext)}</span>
              ${jaTem ? '<span class="badge bg-secondary ms-1">já existe</span>' : ''}
            </label>
          </div>`;
      }).join('');
    }
    const ctx = document.getElementById('modalUsarModelosContexto');
    if (ctx) {
      const u = estado.usuarios.find((x) => String(x.user_id) === String(estado.filtroUserId));
      const c = estado.atividadesComUsuarios.find((x) => Number(x.id_atividade) === Number(estado.filtroIdAtividade));
      ctx.textContent = `Marque os modelos pra adicionar como campos de ${u?.nome_exibicao || estado.filtroUserId} no canal ${c?.titulo || ('#' + estado.filtroIdAtividade)}:`;
    }
    if (window.bootstrap?.Modal) {
      window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
    }
  }

  async function salvarModelosSelecionados() {
    if (!estado.filtroUserId || !estado.filtroIdAtividade) {
      alerta('erro', 'MEGA', 'Selecione um usuário e um canal.');
      return;
    }
    const lista = document.getElementById('modalUsarModelosLista');
    if (!lista) return;
    const ids = Array.from(lista.querySelectorAll('.mega-modelo-check:checked')).map((c) => parseInt(c.value, 10));
    if (!ids.length) {
      alerta('erro', 'MEGA', 'Selecione ao menos um modelo.');
      return;
    }
    const btn = document.getElementById('modalUsarModelosSalvar');
    if (btn) { btn.disabled = true; btn.textContent = 'Salvando…'; }
    let ok = 0;
    let falhou = 0;
    for (const id of ids) {
      const m = estado.modelosCampos.find((x) => x.id_modelo === id);
      if (!m) continue;
      try {
        await requisitar(API + 'campos_salvar.php', 'POST', {
          id_campo: 0,
          user_id: estado.filtroUserId,
          id_atividade: estado.filtroIdAtividade,
          label_campo: m.label_campo,
          tipo: m.tipo || 'outro',
          extensoes_permitidas: m.extensoes_permitidas || '',
          quantidade_maxima: m.quantidade_maxima,
          obrigatorio: !!m.obrigatorio,
          ordem: m.ordem || 0,
          ativo: true,
        });
        ok++;
      } catch (e) {
        falhou++;
        console.warn('[mega] falha ao aplicar modelo', id, e?.message || e);
      }
    }
    if (btn) { btn.disabled = false; btn.textContent = 'Salvar selecionados'; }
    const modalEl = document.getElementById('modalUsarModelos');
    if (window.bootstrap?.Modal && modalEl) window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    alerta(falhou ? 'erro' : 'sucesso', 'MEGA', `${ok} campo(s) adicionado(s)${falhou ? `, ${falhou} falhou(aram)` : ''}.`);
    carregarCampos();
  }

  // ----- Tabela CRUD de modelos (inline) — substitui os popups antigos -----
  // Editar/Excluir/Novo direto na tabela. Excluir é soft-delete do template
  // (campos_modelos_excluir.php → ativo=0): NÃO remove o campo dos usuários que
  // já o têm — só tira o modelo da lista de modelos.
  function linhaModeloLeitura(m) {
    const ext = m.extensoes_permitidas ? esc(m.extensoes_permitidas) : '<span class="texto-fraco">qualquer</span>';
    const qtd = (parseInt(m.quantidade_maxima, 10) || 0) === 0 ? '<span class="texto-fraco">ilim.</span>' : m.quantidade_maxima;
    const obrig = m.obrigatorio ? '<span class="badge bg-warning text-dark">SIM</span>' : '<span class="badge bg-secondary">não</span>';
    const tipoBadge = (m.tipo && m.tipo !== 'outro')
      ? `<span class="badge bg-info text-dark">${esc(rotuloTipoCampo(m.tipo))}</span>`
      : '<span class="texto-fraco">—</span>';
    return `
      <tr data-id-modelo="${m.id_modelo}" data-modo="leitura">
        <td>${m.ordem || 0}</td>
        <td><strong>${esc(m.nome_modelo)}</strong></td>
        <td>${esc(m.label_campo)}</td>
        <td>${tipoBadge}</td>
        <td>${ext}</td>
        <td class="text-center">${qtd}</td>
        <td class="text-center">${obrig}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-light mega-modelo-editar" type="button">Editar</button>
          <button class="btn btn-sm btn-outline-danger mega-modelo-excluir" type="button" title="Excluir modelo">×</button>
        </td>
      </tr>`;
  }

  function linhaModeloEditavel(modelo) {
    const m = modelo || { id_modelo: 0, nome_modelo: '', label_campo: '', tipo: 'outro', extensoes_permitidas: '', quantidade_maxima: 1, obrigatorio: true, ordem: 0 };
    const qtdAtual = (m.quantidade_maxima === undefined || m.quantidade_maxima === null) ? 1 : m.quantidade_maxima;
    return `
      <tr data-id-modelo="${m.id_modelo || 0}" data-modo="edicao">
        <td><input type="number" class="form-control form-control-sm bg-transparent text-white border-secondary mega-modelo-ordem" value="${m.ordem || 0}" min="0" style="width:70px;"></td>
        <td><input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-modelo-nome" value="${esc(m.nome_modelo)}" placeholder="ex: Thumb padrão" maxlength="120"></td>
        <td><input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-modelo-label" value="${esc(m.label_campo)}" placeholder="ex: Thumbnail" maxlength="120"></td>
        <td><select class="form-select form-select-sm bg-transparent text-white border-secondary mega-modelo-tipo" style="min-width:110px;">${opcoesTipoCampo(m.tipo || 'outro')}</select></td>
        <td><input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-modelo-ext" value="${esc(m.extensoes_permitidas || '')}" placeholder="vazio = qualquer" maxlength="255"></td>
        <td class="text-center"><input type="number" class="form-control form-control-sm bg-transparent text-white border-secondary mega-modelo-qtd" value="${qtdAtual}" min="0" max="100" title="0 = ilimitado" style="width:70px;display:inline-block;"></td>
        <td class="text-center"><input type="checkbox" class="form-check-input mega-modelo-obrig" ${m.obrigatorio ? 'checked' : ''}></td>
        <td class="text-end">
          <button class="btn btn-sm btn-light mega-modelo-confirmar" type="button">Salvar</button>
          <button class="btn btn-sm btn-outline-light mega-modelo-cancelar" type="button">Cancelar</button>
        </td>
      </tr>`;
  }

  function renderizarTabelaModelos() {
    const tbody = document.getElementById('tbodyMegaModelos');
    if (!tbody) return;
    const badge = document.getElementById('megaBadgeModelos');
    if (badge) badge.textContent = String(estado.modelosCampos.length);
    if (!estado.modelosCampos.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="texto-fraco">Nenhum modelo cadastrado. Clique em <strong>+ Novo modelo</strong>.</td></tr>';
      bindModelosActions();
      return;
    }
    tbody.innerHTML = estado.modelosCampos.map(linhaModeloLeitura).join('');
    bindModelosActions();
  }

  function novoModelo() {
    const tbody = document.getElementById('tbodyMegaModelos');
    if (!tbody) return;
    if (tbody.querySelector('tr[data-id-modelo="0"]')) return; // já há uma linha nova
    tbody.insertAdjacentHTML('afterbegin', linhaModeloEditavel(null));
    bindModelosActions();
  }

  function bindModelosActions() {
    const tbody = document.getElementById('tbodyMegaModelos');
    if (!tbody) return;

    tbody.querySelectorAll('.mega-modelo-editar').forEach((btn) => {
      btn.addEventListener('click', (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const id = parseInt(tr.getAttribute('data-id-modelo'), 10);
        const m = estado.modelosCampos.find((x) => x.id_modelo === id);
        if (!m) return;
        tr.outerHTML = linhaModeloEditavel(m);
        bindModelosActions();
      });
    });

    tbody.querySelectorAll('.mega-modelo-excluir').forEach((btn) => {
      btn.addEventListener('click', async (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const id = parseInt(tr.getAttribute('data-id-modelo'), 10);
        if (!id) return;
        const m = estado.modelosCampos.find((x) => x.id_modelo === id);
        const nome = m ? m.nome_modelo : ('#' + id);
        if (!confirm(`Excluir o modelo "${nome}"?\n\nIsso remove só o modelo da lista. Os usuários que já têm esse campo continuam com ele.`)) return;
        try {
          await requisitar(API + 'campos_modelos_excluir.php', 'POST', { id_modelo: id });
          alerta('sucesso', 'MEGA', 'Modelo excluído.');
          carregarModelosCampos();
        } catch (e) {
          alerta('erro', 'MEGA', e.message);
        }
      });
    });

    tbody.querySelectorAll('.mega-modelo-cancelar').forEach((btn) => {
      btn.addEventListener('click', () => renderizarTabelaModelos());
    });

    tbody.querySelectorAll('.mega-modelo-confirmar').forEach((btn) => {
      btn.addEventListener('click', async (ev) => {
        const tr = ev.currentTarget.closest('tr');
        const id = parseInt(tr.getAttribute('data-id-modelo'), 10) || 0;
        const payload = {
          id_modelo: id,
          nome_modelo: tr.querySelector('.mega-modelo-nome')?.value?.trim() || '',
          label_campo: tr.querySelector('.mega-modelo-label')?.value?.trim() || '',
          tipo: tr.querySelector('.mega-modelo-tipo')?.value || 'outro',
          extensoes_permitidas: tr.querySelector('.mega-modelo-ext')?.value?.trim() || '',
          quantidade_maxima: Math.max(0, parseInt(tr.querySelector('.mega-modelo-qtd')?.value, 10) || 0),
          obrigatorio: !!tr.querySelector('.mega-modelo-obrig')?.checked,
          ordem: parseInt(tr.querySelector('.mega-modelo-ordem')?.value, 10) || 0,
          ativo: true,
        };
        if (!payload.nome_modelo || !payload.label_campo) {
          alerta('erro', 'MEGA', 'Preencha o nome do modelo e o label do campo.');
          return;
        }
        try {
          await requisitar(API + 'campos_modelos_salvar.php', 'POST', payload);
          alerta('sucesso', 'MEGA', 'Modelo salvo.');
          carregarModelosCampos();
        } catch (e) {
          alerta('erro', 'MEGA', e.message); // 409 = nome de modelo duplicado
        }
      });
    });
  }

  // ===========================================================
  // BLOCO 3 — Pastas lógicas (com link MEGA + status publicação)
  // ===========================================================
  async function carregarPastas() {
    const tbody = document.getElementById('tbodyMegaPastas');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>';

    let url = API + 'pasta_logica_listar.php';
    if (estado.filtroCanalPastas > 0) {
      url += '?id_atividade=' + estado.filtroCanalPastas;
    }

    try {
      const dados = await requisitar(url);
      estado.pastas = Array.isArray(dados) ? dados : [];
      popularSelectUsuariosPastas();
      renderizarPastas();
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
  }

  function popularSelectUsuariosPastas() {
    const selUpado = document.getElementById('megaFiltroUpadoPor');
    if (!selUpado) return;

    const uploaders = new Set();
    estado.pastas.forEach((p) => {
      if (p.upado_por) {
        p.upado_por.split(',').forEach((u) => { const t = u.trim(); if (t) uploaders.add(t); });
      }
    });

    const prev = estado.filtroUpadoPor;
    selUpado.innerHTML = '<option value="">Upado por</option>'
      + [...uploaders].sort().map((u) => `<option value="${esc(u)}"${u === prev ? ' selected' : ''}>${esc(u)}</option>`).join('');
  }

  function filtrarPastas() {
    const busca = estado.buscaPastas.toLowerCase().trim();
    const status = estado.filtroStatusPastas;
    const upadoPor = estado.filtroUpadoPor;
    return estado.pastas.filter((p) => {
      if (status === 'publicado' && !p.video_publicado) return false;
      if (status === 'pendente' && p.video_publicado) return false;
      if (upadoPor) {
        const uploaders = (p.upado_por || '').split(',').map((u) => u.trim());
        if (!uploaders.includes(upadoPor)) return false;
      }
      if (busca) {
        const texto = ((p.nome_pasta || '') + ' ' + (p.numero_video || '') + ' ' + (p.titulo_atividade || '') + ' ' + (p.upado_por || '')).toLowerCase();
        if (!texto.includes(busca)) return false;
      }
      return true;
    });
  }

  function ordenarPastas(lista) {
    const { campo, direcao } = estado.sortPastas;
    if (!campo || !direcao) return lista;
    const copia = lista.slice();
    copia.sort((a, b) => {
      let va = a[campo], vb = b[campo];
      // numero_video: comparação numérica
      if (campo === 'numero_video') {
        va = parseInt(va, 10) || 0;
        vb = parseInt(vb, 10) || 0;
      } else if (campo === 'video_publicado') {
        // booleano → 0/1
        va = va ? 1 : 0;
        vb = vb ? 1 : 0;
      } else if (campo === 'criado_em') {
        va = va ? new Date(String(va).replace(' ', 'T')).getTime() : 0;
        vb = vb ? new Date(String(vb).replace(' ', 'T')).getTime() : 0;
      } else {
        va = String(va || '').toLowerCase();
        vb = String(vb || '').toLowerCase();
      }
      if (va < vb) return direcao === 'asc' ? -1 : 1;
      if (va > vb) return direcao === 'asc' ? 1 : -1;
      return 0;
    });
    return copia;
  }

  function atualizarIconesSort() {
    const thead = document.querySelector('#tbodyMegaPastas')?.closest('table')?.querySelector('thead');
    if (!thead) return;
    thead.querySelectorAll('[data-mega-sort]').forEach((th) => {
      const icone = th.querySelector('.mega-sort-icon');
      if (!icone) return;
      if (th.dataset.megaSort === estado.sortPastas.campo && estado.sortPastas.direcao) {
        icone.textContent = estado.sortPastas.direcao === 'asc' ? ' \u25B2' : ' \u25BC';
      } else {
        icone.textContent = '';
      }
    });
  }

  function renderizarPastas() {
    const tbody = document.getElementById('tbodyMegaPastas');
    if (!tbody) return;

    const filtradas = ordenarPastas(filtrarPastas());
    const b = document.getElementById('megaBadgePastas');
    if (b) b.textContent = filtradas.length === estado.pastas.length
      ? String(estado.pastas.length)
      : filtradas.length + '/' + estado.pastas.length;

    if (!filtradas.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="texto-fraco">Nenhuma pasta encontrada.</td></tr>';
      return;
    }

    tbody.innerHTML = filtradas.map((p) => {
      const pub = p.video_publicado;
      const classeRow = pub ? 'mega-linha-publicado' : '';
      const nomePasta = p.link_mega
        ? `<a href="${esc(p.link_mega)}" target="_blank" rel="noopener" class="text-white text-decoration-underline" title="Abrir no MEGA">${esc(p.nome_pasta)}</a>`
        : `<span title="Link MEGA não disponível">${esc(p.nome_pasta)}</span>`;
      const badge = pub
        ? `<span class="badge bg-success">Publicado</span>`
        : `<span class="badge bg-danger">Pendente</span>`;
      const btnAcao = pub
        ? `<button class="btn btn-sm btn-outline-danger" data-acao-pasta="desmarcar" data-id="${p.id_pasta_logica}" title="Cancelar publicação">Cancelar</button>`
        : `<button class="btn btn-sm btn-outline-secondary" data-acao-pasta="marcar" data-id="${p.id_pasta_logica}" title="Marcar como publicado">Publicar</button>`;

      return `<tr class="${classeRow}">
        <td>${esc(p.titulo_atividade || '—')}</td>
        <td><strong>${nomePasta}</strong></td>
        <td>${esc(p.upado_por || '—')}</td>
        <td>${esc(p.numero_video)}</td>
        <td>${badge}</td>
        <td class="texto-fraco small">${formatarData(p.criado_em)}</td>
        <td>${btnAcao}</td>
      </tr>`;
    }).join('');

    bindPastasActions();
    atualizarIconesSort();
  }

  function bindPastasActions() {
    document.querySelectorAll('[data-acao-pasta]').forEach((btn) => {
      btn.addEventListener('click', async (ev) => {
        const id = parseInt(ev.currentTarget.dataset.id, 10);
        const acao = ev.currentTarget.dataset.acaoPasta;
        const publicado = acao === 'marcar' ? 1 : 0;
        ev.currentTarget.disabled = true;
        try {
          await requisitar(API + 'pasta_logica_marcar_publicado.php', 'POST', {
            id_pasta_logica: id,
            publicado: publicado,
          });
          // Atualiza no estado local sem recarregar tudo
          const p = estado.pastas.find((x) => x.id_pasta_logica === id);
          if (p) {
            p.video_publicado = publicado === 1;
            p.publicado_em = publicado === 1 ? new Date().toISOString() : null;
          }
          renderizarPastas();
          alerta('sucesso', 'MEGA', publicado ? 'Vídeo marcado como publicado' : 'Publicação cancelada');
        } catch (e) {
          alerta('erro', 'MEGA', e.message);
          ev.currentTarget.disabled = false;
        }
      });
    });
  }

  // ===========================================================
  // Wiring de eventos
  // ===========================================================
  function bindEventosAba() {
    document.getElementById('megaBotaoRecarregarCanais')?.addEventListener('click', () => carregarCanais());
    document.getElementById('megaBotaoRecarregarPastas')?.addEventListener('click', () => carregarPastas());

    document.getElementById('megaFiltroUser')?.addEventListener('change', (ev) => {
      estado.filtroUserId = ev.target.value;
      // Re-renderiza select de canais filtrado pelos canais do user; reseta
      // a seleção atual de canal pra evitar inconsistência.
      atualizarSelectCanaisPorUsuario();
      carregarCampos();
    });
    document.getElementById('megaFiltroCanal')?.addEventListener('change', (ev) => {
      estado.filtroIdAtividade = parseInt(ev.target.value, 10) || 0;
      carregarCampos();
    });
    document.getElementById('megaFiltroCanalPastas')?.addEventListener('change', (ev) => {
      estado.filtroCanalPastas = parseInt(ev.target.value, 10) || 0;
      carregarPastas();
    });
    document.getElementById('megaFiltroStatusPastas')?.addEventListener('change', (ev) => {
      estado.filtroStatusPastas = ev.target.value;
      renderizarPastas();
    });
    document.getElementById('megaBuscaPastas')?.addEventListener('input', (ev) => {
      estado.buscaPastas = ev.target.value;
      renderizarPastas();
    });
    document.getElementById('megaFiltroUpadoPor')?.addEventListener('change', (ev) => {
      estado.filtroUpadoPor = ev.target.value;
      renderizarPastas();
    });

    document.getElementById('megaBotaoNovoCampo')?.addEventListener('click', () => {
      if (!estado.filtroUserId || !estado.filtroIdAtividade) return;
      const tbody = document.getElementById('tbodyMegaCampos');
      if (!tbody) return;
      // Insere linha em modo edição no topo (não duplica se já existir uma).
      if (tbody.querySelector('tr[data-id-campo="0"]')) return;
      tbody.insertAdjacentHTML('afterbegin', linhaCampoEditavel(null));
      bindCamposActions();
      atualizarBotoesModelos();
    });

    document.getElementById('megaBotaoUsarModelo')?.addEventListener('click', abrirModalUsarModelos);
    document.getElementById('modalUsarModelosSalvar')?.addEventListener('click', salvarModelosSelecionados);
    document.getElementById('megaBotaoNovoModelo')?.addEventListener('click', novoModelo);
    document.getElementById('megaBotaoRecarregarModelos')?.addEventListener('click', carregarModelosCampos);

    // Ordenação clicável nos cabeçalhos da tabela de pastas lógicas
    document.querySelectorAll('[data-mega-sort]').forEach((th) => {
      th.addEventListener('click', () => {
        const campo = th.dataset.megaSort;
        if (estado.sortPastas.campo === campo) {
          // Ciclo: asc → desc → sem filtro
          if (estado.sortPastas.direcao === 'asc') {
            estado.sortPastas.direcao = 'desc';
          } else {
            estado.sortPastas.campo = null;
            estado.sortPastas.direcao = null;
          }
        } else {
          estado.sortPastas.campo = campo;
          estado.sortPastas.direcao = 'asc';
        }
        renderizarPastas();
      });
    });
  }

  let _eventosBindados = false;
  let _carregadoUmaVez = false;

  async function renderizarAbaMega() {
    if (!_eventosBindados) {
      bindEventosAba();
      _eventosBindados = true;
    }
    // Carrega usuários + canais em paralelo na primeira visita; depois só se forçado.
    if (!_carregadoUmaVez) {
      _carregadoUmaVez = true;
      await Promise.all([
        carregarCanais(),
        carregarUsuarios(),
        carregarAtividadesComUsuarios(),
        carregarModelosCampos(),
      ]);
      carregarPastas();
    } else {
      carregarCanais();
      carregarAtividadesComUsuarios();
      carregarModelosCampos();
      carregarPastas();
    }
  }

  window.PainelAbaMega = {
    renderizarAbaMega,
    recarregarCanais: carregarCanais,
    recarregarCampos: carregarCampos,
    recarregarPastas: carregarPastas,
  };

  // Página dedicada (mega.php): sem o SPA do index (#abaDashboard), renderiza a
  // aba ao abrir. No index é sob demanda (painel.js chama renderizarAbaMega ao
  // trocar para a aba MEGA).
  if (!document.getElementById("abaDashboard") && document.getElementById("abaMega")) {
    const _bootMega = () => renderizarAbaMega().catch((e) => console.error("[mega]", e));
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", _bootMega);
    else _bootMega();
  }
})();
