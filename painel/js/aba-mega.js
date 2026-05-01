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
      tbody.innerHTML = '<tr><td colspan="7" class="texto-fraco">Selecione usuário e canal acima.</td></tr>';
      const b = document.getElementById('megaBadgeCampos');
      if (b) b.textContent = '—';
      const btn = document.getElementById('megaBotaoNovoCampo');
      if (btn) btn.disabled = true;
      atualizarBotoesModelos();
      return;
    }

    tbody.innerHTML = '<tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>';

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
      tbody.innerHTML = `<tr><td colspan="7" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
  }

  function linhaCampoEditavel(campo) {
    // Defaults p/ "novo campo": extensões vazias = qualquer; quantidade 1.
    const c = campo || { id_campo: 0, label_campo: '', extensoes_permitidas: '', quantidade_maxima: 1, obrigatorio: true, ordem: 0, ativo: true };
    // qty=0 é válido (= ilimitado). Não usar `|| 1` (truthy coercion zeraria 0).
    const qtdAtual = (c.quantidade_maxima === undefined || c.quantidade_maxima === null) ? 1 : c.quantidade_maxima;
    return `
      <tr data-id-campo="${c.id_campo || 0}" data-modo="edicao">
        <td><input type="number" class="form-control form-control-sm bg-transparent text-white border-secondary mega-campo-ordem" value="${c.ordem || 0}" min="0" style="width:70px;"></td>
        <td><input type="text" class="form-control form-control-sm bg-transparent text-white border-secondary mega-campo-label" value="${esc(c.label_campo)}" placeholder="ex: Vídeo final" maxlength="120"></td>
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
    return `
      <tr data-id-campo="${c.id_campo}" data-modo="leitura" ${c.ativo ? '' : 'style="opacity:0.55;"'}>
        <td>${c.ordem}</td>
        <td><strong>${esc(c.label_campo)}</strong></td>
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
        <tr><td colspan="7" class="texto-fraco">
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
    atualizarSelectModelosCampos();
  }

  function atualizarSelectModelosCampos() {
    const sel = document.getElementById('megaSelectModelo');
    if (!sel) return;
    sel.disabled = false;
    if (!estado.modelosCampos.length) {
      sel.innerHTML = '<option value="">Nenhum modelo cadastrado</option>';
    } else {
      sel.innerHTML = '<option value="">Selecione um modelo…</option>' +
        estado.modelosCampos.map((m) => `<option value="${m.id_modelo}">${esc(m.nome_modelo)}</option>`).join('');
    }
    atualizarBotoesModelos();
  }

  function atualizarBotoesModelos() {
    const btnUsar = document.getElementById('megaBotaoUsarModelo');
    const btnSalvar = document.getElementById('megaBotaoSalvarComoModelo');
    if (btnUsar) {
      btnUsar.disabled = !(estado.filtroUserId && estado.filtroIdAtividade && estado.modelosCampos.length);
    }
    if (btnSalvar) {
      // Habilita só quando há linha em edição visível.
      const tbody = document.getElementById('tbodyMegaCampos');
      const temLinhaEdicao = !!tbody?.querySelector('tr[data-modo="edicao"]');
      btnSalvar.disabled = !temLinhaEdicao;
    }
  }

  function aplicarModeloCampoSelecionado() {
    if (!estado.filtroUserId || !estado.filtroIdAtividade) {
      alerta('erro', 'MEGA', 'Selecione usuário e canal antes de aplicar um modelo.');
      return;
    }
    const sel = document.getElementById('megaSelectModelo');
    const idModelo = parseInt(sel?.value, 10) || 0;
    const modelo = estado.modelosCampos.find((m) => m.id_modelo === idModelo);
    if (!modelo) {
      alerta('erro', 'MEGA', 'Selecione um modelo válido.');
      return;
    }
    const tbody = document.getElementById('tbodyMegaCampos');
    if (!tbody) return;
    // Não duplica se já existir uma linha "novo campo".
    if (tbody.querySelector('tr[data-id-campo="0"]')) {
      alerta('erro', 'MEGA', 'Já existe uma linha em edição. Salve ou cancele antes de aplicar outro modelo.');
      return;
    }
    // id_campo=0 força INSERT no usuário/canal atuais quando o admin clicar Salvar.
    const novo = {
      id_campo: 0,
      label_campo: modelo.label_campo,
      extensoes_permitidas: modelo.extensoes_permitidas || '',
      quantidade_maxima: modelo.quantidade_maxima,
      obrigatorio: !!modelo.obrigatorio,
      ordem: modelo.ordem || 0,
      ativo: true, // ao aplicar, sempre cria como ativo (mesmo se modelo inativo)
    };
    tbody.insertAdjacentHTML('afterbegin', linhaCampoEditavel(novo));
    bindCamposActions();
    atualizarBotoesModelos();
  }

  async function salvarLinhaComoModelo() {
    const tbody = document.getElementById('tbodyMegaCampos');
    const tr = tbody?.querySelector('tr[data-modo="edicao"]');
    if (!tr) {
      alerta('erro', 'MEGA', 'Nenhuma linha em edição.');
      return;
    }
    const label = tr.querySelector('.mega-campo-label')?.value?.trim() || '';
    if (!label) {
      alerta('erro', 'MEGA', 'Preencha o label do campo antes de salvar como modelo.');
      return;
    }
    const sugestao = label;
    const nome = (window.prompt('Nome do modelo:', sugestao) || '').trim();
    if (!nome) return;

    const payload = {
      nome_modelo: nome,
      label_campo: label,
      extensoes_permitidas: tr.querySelector('.mega-campo-ext')?.value?.trim() || '',
      quantidade_maxima: Math.max(0, parseInt(tr.querySelector('.mega-campo-qtd')?.value, 10) || 0),
      obrigatorio: !!tr.querySelector('.mega-campo-obrig')?.checked,
      ordem: parseInt(tr.querySelector('.mega-campo-ordem')?.value, 10) || 0,
      ativo: true,
    };
    try {
      await requisitar(API + 'campos_modelos_salvar.php', 'POST', payload);
      alerta('sucesso', 'MEGA', 'Modelo salvo.');
      carregarModelosCampos();
    } catch (e) {
      alerta('erro', 'MEGA', e.message);
    }
  }

  async function gerenciarModelos() {
    // Lista textual + prompt pra desativar — UX simples sem modal pesado.
    try {
      const dados = await requisitar(API + 'campos_modelos_listar.php?incluir_inativos=1');
      const lista = Array.isArray(dados) ? dados : [];
      if (!lista.length) {
        alerta('info', 'MEGA', 'Nenhum modelo cadastrado.');
        return;
      }
      const linhas = lista.map((m) => {
        const status = m.ativo ? '✓' : '✗';
        const ext = m.extensoes_permitidas || 'qualquer';
        const qtd = m.quantidade_maxima === 0 ? 'ilim.' : m.quantidade_maxima;
        const obr = m.obrigatorio ? 'obrig' : 'opc';
        return `[${m.id_modelo}] ${status} ${m.nome_modelo} → label="${m.label_campo}" ext=${ext} qtd=${qtd} ${obr}`;
      }).join('\n');
      const idStr = window.prompt(
        'Modelos cadastrados (✓ ativo / ✗ inativo):\n\n' + linhas +
        '\n\nDigite o ID do modelo para desativar (cancela em branco):',
        ''
      );
      const idModelo = parseInt(idStr, 10);
      if (!idModelo) return;
      if (!window.confirm(`Desativar modelo #${idModelo}?`)) return;
      await requisitar(API + 'campos_modelos_excluir.php', 'POST', { id_modelo: idModelo });
      alerta('sucesso', 'MEGA', 'Modelo desativado.');
      carregarModelosCampos();
    } catch (e) {
      alerta('erro', 'MEGA', e.message);
    }
  }

  // ===========================================================
  // BLOCO 3 — Pastas lógicas (read-only)
  // ===========================================================
  async function carregarPastas() {
    const tbody = document.getElementById('tbodyMegaPastas');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>';

    let url = API + 'pasta_logica_listar.php';
    if (estado.filtroCanalPastas > 0) {
      url += '?id_atividade=' + estado.filtroCanalPastas;
    }

    try {
      const dados = await requisitar(url);
      estado.pastas = Array.isArray(dados) ? dados : [];
      const b = document.getElementById('megaBadgePastas');
      if (b) b.textContent = String(estado.pastas.length);

      if (!estado.pastas.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="texto-fraco">Nenhuma pasta lógica cadastrada.</td></tr>';
        return;
      }

      tbody.innerHTML = estado.pastas.map((p) => `
        <tr>
          <td>${esc(p.titulo_atividade || '—')}</td>
          <td><strong>${esc(p.nome_pasta)}</strong></td>
          <td>${esc(p.numero_video)}</td>
          <td>${esc(p.criado_por || '—')}</td>
          <td class="texto-fraco small">${formatarData(p.criado_em)}</td>
        </tr>`).join('');
    } catch (e) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
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

    document.getElementById('megaBotaoUsarModelo')?.addEventListener('click', aplicarModeloCampoSelecionado);
    document.getElementById('megaBotaoSalvarComoModelo')?.addEventListener('click', salvarLinhaComoModelo);
    document.getElementById('megaBotaoGerenciarModelos')?.addEventListener('click', gerenciarModelos);
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
})();
