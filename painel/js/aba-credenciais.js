/* aba-credenciais.js — Credenciais e APIs
 *
 * Fluxo:
 *  - Aba autônoma (#abaCredenciais): seletor de usuário + seletor de serviço + grade.
 *  - Embutido em Gestão do Usuário (#tbodyGestaoCredenciais): carregado automaticamente
 *    quando abaGestaoUsuario fica visível e possui data-user-id.
 *  - Modal "Gerenciar modelos" (#modalGerenciarModelos): CRUD dos modelos globais.
 *  - Modal "Substituir valor" (#modalSubstituirValor): grava valor cifrado.
 */
(function () {
  'use strict';

  const API = './commands/credenciais/';

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
      throw new Error(msg);
    }
    return json.dados;
  }

  // ---------- Estado ----------
  const estado = {
    modelos: [],
    usuarios: [],
    userSelecionadoAba: '',
    filtroServico: '',
  };

  // ---------- Modelos globais (CRUD) ----------
  async function carregarModelos() {
    try {
      estado.modelos = await requisitar(API + 'listar_modelos.php');
    } catch (e) {
      estado.modelos = [];
      console.error('[credenciais] listar_modelos', e);
    }
    renderizarModelosTabela();
    popularFiltroServico();
    renderizarApisGlobais();
  }

  // ---------- APIs globais (lista + remover) ----------
  function renderizarApisGlobais() {
    const box = document.getElementById('boxApisGlobais');
    const lista = document.getElementById('listaApisGlobais');
    if (!box || !lista) return;
    const globais = estado.modelos.filter(m => Number(m.aplicar_novos_usuarios) === 1);
    if (!globais.length) {
      box.classList.add('d-none');
      lista.innerHTML = '';
      return;
    }
    box.classList.remove('d-none');
    lista.innerHTML = globais.map(m => `
      <div class="d-inline-flex align-items-center gap-2 px-2 py-1 rounded"
           style="background:rgba(255,255,255,0.06);"
           data-id-modelo="${m.id_modelo}" data-nome="${esc(m.nome_exibicao)}">
        <span class="texto-mono small">${esc(m.identificador)}</span>
        <span class="small">${esc(m.nome_exibicao)}</span>
        <button class="btn btn-sm btn-outline-warning"
                data-acao="remover-global"
                title="Desativar globalmente: revoga em todos os usuários e novos cadastros não herdam mais.">
          Remover global
        </button>
      </div>
    `).join('');
  }

  async function removerApiGlobal(idModelo, nome) {
    const ok = confirm(
      `Remover "${nome}" das APIs globais?\n\n` +
      `• A credencial será REVOGADA em todos os usuários (clientes perdem acesso).\n` +
      `• Novos cadastros NÃO herdarão mais essa credencial.\n` +
      `• O modelo continua existindo — credenciais individuais podem ser atribuídas depois.\n\n` +
      `Continuar?`
    );
    if (!ok) return;
    try {
      const resp = await requisitar(API + 'remover_global.php', 'POST', { id_modelo: idModelo });
      alert(`OK — ${resp.credenciais_revogadas} credencial(is) revogada(s).`);
      await carregarModelos();
      if (estado.userSelecionadoAba) carregarCredenciaisAba();
      const userG = obterUserIdGestao();
      if (userG) carregarCredenciaisGestao(userG);
    } catch (e) {
      alert('Erro ao remover global: ' + e.message);
    }
  }

  const MODELOS_PROTEGIDOS = ['chatgpt', 'gemini', 'minimax', 'elevenlabs', 'assembly'];

  function renderizarModelosTabela() {
    const tb = document.getElementById('tbodyModelos');
    if (!tb) return;
    if (!estado.modelos.length) {
      tb.innerHTML = '<tr><td colspan="5" class="texto-fraco">Nenhum modelo cadastrado.</td></tr>';
      return;
    }
    tb.innerHTML = estado.modelos.map(m => {
      const protegido = MODELOS_PROTEGIDOS.includes((m.identificador || '').toLowerCase());
      const botaoExcluir = protegido
        ? `<button class="btn btn-sm btn-outline-secondary" disabled title="Modelo padrão do sistema — não pode ser excluído">Excluir</button>`
        : `<button class="btn btn-sm btn-outline-danger" data-acao="excluir-modelo">Excluir</button>`;
      return `
      <tr data-id="${m.id_modelo}">
        <td class="texto-mono">${esc(m.identificador)}${protegido ? ' <span class="badge badge-suave ms-1" title="Modelo padrão protegido">padrão</span>' : ''}</td>
        <td>${esc(m.nome_exibicao)}</td>
        <td>${esc(m.categoria)}</td>
        <td class="text-center">${esc(m.ordem_exibicao)}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-outline-light me-1" data-acao="editar-modelo">Editar</button>
          ${botaoExcluir}
        </td>
      </tr>`;
    }).join('');
  }

  function popularFiltroServico() {
    const sel = document.getElementById('credenciaisFiltroServico');
    if (!sel) return;
    const atual = sel.value;
    sel.innerHTML = '<option value="">Todos os serviços</option>'
      + estado.modelos.map(m => `<option value="${esc(m.identificador)}">${esc(m.nome_exibicao)}</option>`).join('');
    sel.value = atual;
  }

  async function salvarModelo() {
    const idEdicao = parseInt(document.getElementById('modeloIdEdicao').value || '0', 10);
    const corpo = {
      id_modelo: idEdicao,
      identificador: document.getElementById('modeloIdentificador').value.trim(),
      nome_exibicao: document.getElementById('modeloNomeExibicao').value.trim(),
      categoria: document.getElementById('modeloCategoria').value,
      descricao: document.getElementById('modeloDescricao').value.trim(),
      ordem_exibicao: parseInt(document.getElementById('modeloOrdem').value || '0', 10),
    };
    if (!corpo.identificador || !corpo.nome_exibicao) {
      alert('Preencha identificador e nome.');
      return;
    }
    try {
      await requisitar(API + 'salvar_modelo.php', 'POST', corpo);
      limparFormModelo();
      await carregarModelos();
      // Se tem usuário selecionado, recarrega grades
      if (estado.userSelecionadoAba) carregarCredenciaisAba();
      const userG = obterUserIdGestao();
      if (userG) carregarCredenciaisGestao(userG);
    } catch (e) {
      alert('Erro ao salvar modelo: ' + e.message);
    }
  }

  function limparFormModelo() {
    document.getElementById('modeloIdEdicao').value = '0';
    document.getElementById('modeloIdentificador').value = '';
    document.getElementById('modeloNomeExibicao').value = '';
    document.getElementById('modeloCategoria').value = 'api';
    document.getElementById('modeloOrdem').value = '0';
    document.getElementById('modeloDescricao').value = '';
  }

  function preencherFormModelo(m) {
    document.getElementById('modeloIdEdicao').value = String(m.id_modelo);
    document.getElementById('modeloIdentificador').value = m.identificador || '';
    document.getElementById('modeloNomeExibicao').value = m.nome_exibicao || '';
    document.getElementById('modeloCategoria').value = m.categoria || 'api';
    document.getElementById('modeloOrdem').value = String(m.ordem_exibicao || 0);
    document.getElementById('modeloDescricao').value = m.descricao || '';
  }

  async function excluirModelo(id) {
    if (!confirm('Excluir este modelo? Isso removerá também as credenciais dos usuários para este serviço.')) return;
    try {
      await requisitar(API + 'excluir_modelo.php', 'POST', { id_modelo: id });
      await carregarModelos();
      if (estado.userSelecionadoAba) carregarCredenciaisAba();
      const userG = obterUserIdGestao();
      if (userG) carregarCredenciaisGestao(userG);
    } catch (e) {
      alert('Erro ao excluir: ' + e.message);
    }
  }

  // ---------- Usuários (seletor da aba) ----------
  async function carregarUsuariosParaSeletor() {
    try {
      const r = await fetch('./commands/usuarios/listar.php', { credentials: 'same-origin' });
      const j = await r.json();
      estado.usuarios = (j && j.ok && Array.isArray(j.dados)) ? j.dados : [];
    } catch (_) {
      estado.usuarios = [];
    }
    const sel = document.getElementById('credenciaisFiltroUsuario');
    if (!sel) return;
    sel.innerHTML = '<option value="">Selecione um usuário…</option>'
      + estado.usuarios
          .filter(u => (u.status_conta || '').toLowerCase() === 'ativa')
          .map(u => `<option value="${esc(u.user_id)}">${esc(u.user_id)} — ${esc(u.nome_exibicao || '')}</option>`)
          .join('');
  }

  // ---------- Grade (aba autônoma) ----------
  async function carregarCredenciaisAba() {
    const tb = document.getElementById('tbodyCredenciais');
    if (!tb) return;
    if (!estado.userSelecionadoAba) {
      tb.innerHTML = '<tr><td colspan="6" class="texto-fraco">Selecione um usuário acima.</td></tr>';
      return;
    }
    tb.innerHTML = '<tr><td colspan="6" class="texto-fraco">Carregando…</td></tr>';
    try {
      const dados = await requisitar(API + 'listar_por_usuario.php?user_id=' + encodeURIComponent(estado.userSelecionadoAba));
      renderizarGrade(tb, dados, estado.userSelecionadoAba, true);
    } catch (e) {
      tb.innerHTML = `<tr><td colspan="6" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
  }

  // ---------- Grade (Gestão do Usuário) ----------
  function obterUserIdGestao() {
    const aba = document.getElementById('abaGestaoUsuario');
    if (!aba || aba.classList.contains('d-none')) return '';
    return aba.getAttribute('data-user-id') || '';
  }

  async function carregarCredenciaisGestao(userId) {
    const tb = document.getElementById('tbodyGestaoCredenciais');
    if (!tb) return;
    tb.innerHTML = '<tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>';
    try {
      const dados = await requisitar(API + 'listar_por_usuario.php?user_id=' + encodeURIComponent(userId));
      renderizarGrade(tb, dados, userId, false);
    } catch (e) {
      tb.innerHTML = `<tr><td colspan="5" class="text-danger">Erro: ${esc(e.message)}</td></tr>`;
    }
  }

  // ---------- Renderização compartilhada ----------
  function renderizarGrade(tb, dados, userId, incluirCategoria) {
    const filtro = estado.filtroServico;
    const lista = (dados || []).filter(d => !filtro || d.identificador === filtro);
    if (!lista.length) {
      const cols = incluirCategoria ? 6 : 5;
      tb.innerHTML = `<tr><td colspan="${cols}" class="texto-fraco">Nenhum serviço cadastrado.</td></tr>`;
      return;
    }
    tb.innerHTML = lista.map(d => {
      const est = d.estado || 'vazia';
      const cor = est === 'preenchida' ? 'text-success'
                : est === 'revogada' ? 'text-warning' : 'text-secondary';
      const rotulo = est === 'preenchida' ? 'Preenchida'
                   : est === 'revogada' ? 'Revogada' : 'Vazia';
      const mascara = d.mascara_parcial ? `<span class="texto-mono">${esc(d.mascara_parcial)}</span>` : '<span class="texto-fraco">—</span>';
      const atualizado = formatarData(d.credencial_atualizado_em);
      const catCol = incluirCategoria ? `<td>${esc(d.categoria || '')}</td>` : '';
      return `
        <tr data-id-modelo="${d.id_modelo}" data-identificador="${esc(d.identificador)}" data-nome="${esc(d.nome_exibicao)}">
          <td>
            <div class="fw-semibold">${esc(d.nome_exibicao)}</div>
            <div class="texto-fraco small texto-mono">${esc(d.identificador)}</div>
          </td>
          ${catCol}
          <td class="text-center ${cor} fw-semibold">${rotulo}</td>
          <td>${mascara}</td>
          <td>${atualizado}</td>
          <td class="text-end">
            <button class="btn btn-sm btn-light me-1" data-acao="substituir" data-user="${esc(userId)}">Substituir</button>
            ${est !== 'vazia' ? `<button class="btn btn-sm btn-outline-warning me-1" data-acao="revogar" data-user="${esc(userId)}">Revogar</button>` : ''}
            ${est !== 'vazia' ? `<button class="btn btn-sm btn-outline-danger" data-acao="apagar" data-user="${esc(userId)}">Apagar</button>` : ''}
          </td>
        </tr>`;
    }).join('');
  }

  // ---------- Modal substituir valor ----------
  function abrirModalSubstituir(userId, idModelo, nomeServico) {
    document.getElementById('subUserId').value = userId;
    document.getElementById('subIdModelo').value = String(idModelo);
    document.getElementById('textoModalSubUsuario').textContent = userId;
    document.getElementById('textoModalSubServico').textContent = nomeServico;
    document.getElementById('entradaNovoValor').value = '';
    // Sempre desmarcado ao abrir
    const chk = document.getElementById('checkAplicarTodos');
    if (chk) chk.checked = false;
    const m = new bootstrap.Modal(document.getElementById('modalSubstituirValor'));
    m.show();
  }

  async function salvarNovoValor() {
    const user_id = document.getElementById('subUserId').value;
    const id_modelo = parseInt(document.getElementById('subIdModelo').value || '0', 10);
    const valor = document.getElementById('entradaNovoValor').value;
    const aplicar_todos = !!document.getElementById('checkAplicarTodos')?.checked;

    if (id_modelo <= 0) { alert('Dados inválidos.'); return; }
    if (!aplicar_todos && !user_id) { alert('Usuário inválido.'); return; }
    if (!valor.trim()) { alert('Informe o valor.'); return; }

    // Confirmação extra em modo global
    if (aplicar_todos) {
      const ok = confirm(
        'Isso vai SOBRESCREVER o valor desta credencial em TODOS os usuários ativos.\n\n' +
        'Usuários que já tinham outra chave perderão a atual.\n\n' +
        'Continuar?'
      );
      if (!ok) return;
    }

    try {
      const resp = await requisitar(API + 'salvar_valor.php', 'POST', {
        user_id, id_modelo, valor, aplicar_todos,
      });
      document.getElementById('entradaNovoValor').value = '';
      bootstrap.Modal.getInstance(document.getElementById('modalSubstituirValor')).hide();

      if (aplicar_todos && resp && resp.usuarios_afetados != null) {
        alert(`Credencial aplicada a ${resp.usuarios_afetados} usuário(s).`);
      }

      // Recarrega grades independentemente (no modo global todos mudaram)
      if (estado.userSelecionadoAba) carregarCredenciaisAba();
      const userG = obterUserIdGestao();
      if (userG) carregarCredenciaisGestao(userG);

      // Aplicar global liga aplicar_novos_usuarios — recarrega lista de globais
      if (aplicar_todos) carregarModelos();
    } catch (e) {
      alert('Erro ao salvar valor: ' + e.message);
    }
  }

  async function acaoRevogar(userId, idModelo, apagar) {
    const msg = apagar
      ? 'Apagar definitivamente esta credencial do usuário?'
      : 'Revogar esta credencial? O valor fica no banco mas marcado como revogado.';
    if (!confirm(msg)) return;
    try {
      await requisitar(API + 'revogar_valor.php', 'POST', { user_id: userId, id_modelo: idModelo, apagar: !!apagar });
      if (estado.userSelecionadoAba === userId) carregarCredenciaisAba();
      if (obterUserIdGestao() === userId) carregarCredenciaisGestao(userId);
    } catch (e) {
      alert('Erro: ' + e.message);
    }
  }

  // ---------- Wiring ----------
  function extrairDadosLinha(tr) {
    return {
      idModelo: parseInt(tr.getAttribute('data-id-modelo') || '0', 10),
      identificador: tr.getAttribute('data-identificador') || '',
      nome: tr.getAttribute('data-nome') || '',
    };
  }

  function delegarAcoesGrade(container) {
    if (!container) return;
    container.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-acao]');
      if (!btn) return;
      const tr = btn.closest('tr');
      if (!tr) return;
      const { idModelo, nome } = extrairDadosLinha(tr);
      const userId = btn.getAttribute('data-user') || '';
      const acao = btn.getAttribute('data-acao');
      if (acao === 'substituir') abrirModalSubstituir(userId, idModelo, nome);
      else if (acao === 'revogar') acaoRevogar(userId, idModelo, false);
      else if (acao === 'apagar')  acaoRevogar(userId, idModelo, true);
    });
  }

  function delegarAcoesModelos() {
    const tb = document.getElementById('tbodyModelos');
    if (!tb) return;
    tb.addEventListener('click', (ev) => {
      const btn = ev.target.closest('button[data-acao]');
      if (!btn) return;
      const tr = btn.closest('tr');
      const id = parseInt(tr.getAttribute('data-id') || '0', 10);
      const modelo = estado.modelos.find(m => m.id_modelo === id);
      if (btn.getAttribute('data-acao') === 'editar-modelo' && modelo) preencherFormModelo(modelo);
      else if (btn.getAttribute('data-acao') === 'excluir-modelo') excluirModelo(id);
    });
  }

  function ligarEventos() {
    const selU = document.getElementById('credenciaisFiltroUsuario');
    if (selU) selU.addEventListener('change', () => {
      estado.userSelecionadoAba = selU.value;
      carregarCredenciaisAba();
    });
    const selS = document.getElementById('credenciaisFiltroServico');
    if (selS) selS.addEventListener('change', () => {
      estado.filtroServico = selS.value;
      carregarCredenciaisAba();
      const userG = obterUserIdGestao();
      if (userG) carregarCredenciaisGestao(userG);
    });

    const btnSalvarModelo = document.getElementById('botaoSalvarModelo');
    if (btnSalvarModelo) btnSalvarModelo.addEventListener('click', salvarModelo);
    const btnLimparModelo = document.getElementById('botaoLimparModelo');
    if (btnLimparModelo) btnLimparModelo.addEventListener('click', limparFormModelo);
    const btnSalvarValor = document.getElementById('botaoSalvarNovoValor');
    if (btnSalvarValor) btnSalvarValor.addEventListener('click', salvarNovoValor);

    delegarAcoesGrade(document.getElementById('tbodyCredenciais'));
    delegarAcoesGrade(document.getElementById('tbodyGestaoCredenciais'));
    delegarAcoesModelos();

    // Botões "Remover global" na seção de APIs globais
    const boxGlob = document.getElementById('listaApisGlobais');
    if (boxGlob) {
      boxGlob.addEventListener('click', (ev) => {
        const btn = ev.target.closest('button[data-acao="remover-global"]');
        if (!btn) return;
        const wrapper = btn.closest('[data-id-modelo]');
        if (!wrapper) return;
        const idModelo = parseInt(wrapper.getAttribute('data-id-modelo') || '0', 10);
        const nome = wrapper.getAttribute('data-nome') || '';
        if (idModelo > 0) removerApiGlobal(idModelo, nome);
      });
    }

    // Reagir à abertura da Gestão do Usuário
    const abaGestao = document.getElementById('abaGestaoUsuario');
    if (abaGestao) {
      const mo = new MutationObserver(() => {
        const userId = obterUserIdGestao();
        if (userId) carregarCredenciaisGestao(userId);
      });
      mo.observe(abaGestao, { attributes: true, attributeFilter: ['class', 'data-user-id'] });
    }

    // Reagir à troca para a aba Credenciais
    const abaC = document.getElementById('abaCredenciais');
    if (abaC) {
      const mo2 = new MutationObserver(() => {
        if (!abaC.classList.contains('d-none') && !estado.modelos.length) {
          carregarModelos();
          carregarUsuariosParaSeletor();
        }
      });
      mo2.observe(abaC, { attributes: true, attributeFilter: ['class'] });
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    ligarEventos();
    // Pré-carrega modelos para que o seletor de serviço e Gestão do Usuário funcionem de cara
    carregarModelos();
    carregarUsuariosParaSeletor();
  });
})();
