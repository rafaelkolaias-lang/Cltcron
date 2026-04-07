/* painel/js/aba-gerenciar-tarefas.js */
(function () {
  "use strict";

  const URL_LISTAR = "./commands/atividades_subtarefas/listar.php";
  const URL_EDITAR = "./commands/atividades_subtarefas/editar.php";
  const URL_USUARIOS = "./commands/usuarios/listar_ativos.php";
  const URL_ATIVIDADES = "./commands/atividades/listar.php";

  // ─── estado ───────────────────────────────────────────────────────────────
  let _dados = [];
  let _carregando = false;
  let _idEditando = 0;
  let _cacheUsuarios = [];
  let _cacheAtividades = [];

  // ─── helpers ──────────────────────────────────────────────────────────────
  function el(id) { return document.getElementById(id); }

  function esc(v) {
    return String(v ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function dataIsoBr(iso) {
    const m = String(iso ?? "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : (iso ?? "—");
  }

  function segundosParaHm(s) {
    const total = Math.max(0, Math.round(Number(s) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const seg = total % 60;
    if (h > 0) return `${h}h ${String(m).padStart(2,"0")}m`;
    if (m > 0) return `${m}m ${String(seg).padStart(2,"0")}s`;
    return `${seg}s`;
  }

  function hmParaSegundos(str) {
    // aceita: "1h30m", "90m", "5400", "1:30:00", "01:30"
    str = String(str || "").trim().toLowerCase();
    if (/^\d+$/.test(str)) return parseInt(str, 10);
    // hh:mm:ss ou hh:mm
    const hhmmss = str.match(/^(\d+):(\d{2})(?::(\d{2}))?$/);
    if (hhmmss) {
      return parseInt(hhmmss[1],10)*3600 + parseInt(hhmmss[2],10)*60 + parseInt(hhmmss[3]||"0",10);
    }
    // XhYm ou Xh ou Ym
    let total = 0;
    const mH = str.match(/(\d+)\s*h/); if (mH) total += parseInt(mH[1],10)*3600;
    const mM = str.match(/(\d+)\s*m/); if (mM) total += parseInt(mM[1],10)*60;
    const mS = str.match(/(\d+)\s*s/); if (mS) total += parseInt(mS[1],10);
    return total;
  }

  function dataHojeIso() {
    const d = new Date();
    return [d.getFullYear(), String(d.getMonth()+1).padStart(2,"0"), String(d.getDate()).padStart(2,"0")].join("-");
  }

  // ─── carregar combos ──────────────────────────────────────────────────────
  async function _carregarCombos() {
    try {
      const [rU, rA] = await Promise.all([
        fetch(URL_USUARIOS).then(r => r.json()),
        fetch(URL_ATIVIDADES).then(r => r.json()),
      ]);
      _cacheUsuarios   = (rU.dados  || []);
      _cacheAtividades = (rA.dados  || []);
      _preencherSelectFiltroUsuario();
      _preencherSelectFiltroAtividade();
    } catch (_) {}
  }

  function _preencherSelectFiltroUsuario() {
    const sel = el("gtFiltroUsuario");
    if (!sel) return;
    sel.innerHTML = '<option value="">Todos os membros</option>';
    _cacheUsuarios.forEach(u => {
      const opt = document.createElement("option");
      opt.value = esc(u.user_id);
      opt.textContent = u.nome_exibicao || u.user_id;
      sel.appendChild(opt);
    });
  }

  function _preencherSelectFiltroAtividade() {
    const sel = el("gtFiltroAtividade");
    if (!sel) return;
    sel.innerHTML = '<option value="">Todas as atividades</option>';
    _cacheAtividades.forEach(a => {
      const opt = document.createElement("option");
      opt.value = a.id_atividade;
      opt.textContent = esc(a.titulo);
      sel.appendChild(opt);
    });
  }

  // ─── carregar dados ───────────────────────────────────────────────────────
  async function carregarTarefas() {
    if (_carregando) return;
    _carregando = true;

    const tbody = el("tbodyGerenciarTarefas");
    if (tbody) tbody.innerHTML = '<tr><td colspan="8" class="texto-fraco text-center py-3">Carregando…</td></tr>';

    const params = new URLSearchParams();
    const di = (el("gtDataInicio") || {}).value || "";
    const df = (el("gtDataFim")    || {}).value || "";
    const uid = (el("gtFiltroUsuario")   || {}).value || "";
    const aid = (el("gtFiltroAtividade") || {}).value || "";
    const canal = (el("gtFiltroCanal")   || {}).value || "";

    if (di)   params.set("data_inicio",   di);
    if (df)   params.set("data_fim",      df);
    if (uid)  params.set("user_id",       uid);
    if (aid)  params.set("id_atividade",  aid);
    if (canal) params.set("canal",        canal);

    try {
      const r = await fetch(`${URL_LISTAR}?${params}`);
      const j = await r.json();
      if (!j.ok) throw new Error(j.mensagem || "Erro na API");
      _dados = j.dados || [];
    } catch (err) {
      _dados = [];
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-danger text-center py-3">Erro: ${esc(err.message)}</td></tr>`;
      _carregando = false;
      return;
    }

    _renderizar();
    _carregando = false;
  }

  // ─── renderizar tabela ────────────────────────────────────────────────────
  function _renderizar() {
    const tbody = el("tbodyGerenciarTarefas");
    const total = el("gtTotalRegistros");
    if (!tbody) return;

    if (total) total.textContent = `${_dados.length} registro(s)`;

    if (!_dados.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="texto-fraco text-center py-3">Nenhuma declaração encontrada.</td></tr>';
      return;
    }

    tbody.innerHTML = _dados.map(t => {
      const bloqueada = t.bloqueada_pagamento;
      const statusBadge = t.concluida
        ? '<span class="badge badge-suave text-success">Concluída</span>'
        : '<span class="badge badge-suave text-warning">Aberta</span>';
      const travaBadge = bloqueada
        ? '<span class="badge badge-suave text-danger ms-1" title="Bloqueada por pagamento">🔒</span>'
        : '';
      const tempo = t.segundos_gastos > 0 ? segundosParaHm(t.segundos_gastos) : '<span class="texto-fraco">—</span>';
      const canal = t.canal_entrega ? esc(t.canal_entrega) : '<span class="texto-fraco">—</span>';
      const btnEditar = bloqueada
        ? `<button class="btn btn-sm btn-outline-secondary" disabled title="Bloqueada por pagamento">Editar</button>`
        : `<button class="btn btn-sm btn-outline-light botao-mini" onclick="gtAbrirEdicao(${t.id_subtarefa})">Editar</button>`;

      return `
        <tr>
          <td class="small">${esc(dataIsoBr(t.referencia_data))}</td>
          <td class="small">${esc(t.nome_exibicao || t.user_id)}</td>
          <td class="small texto-fraco">${esc(t.atividade_titulo || "—")}</td>
          <td class="small">${esc(t.titulo)}${travaBadge}</td>
          <td class="small">${tempo}</td>
          <td class="small">${canal}</td>
          <td class="text-center">${statusBadge}</td>
          <td class="text-end">${btnEditar}</td>
        </tr>`;
    }).join("");
  }

  // ─── modal de edição ──────────────────────────────────────────────────────
  window.gtAbrirEdicao = function (id) {
    const tarefa = _dados.find(t => t.id_subtarefa === id);
    if (!tarefa) return;
    _idEditando = id;

    (el("gtEditTitulo")    || {}).value = tarefa.titulo || "";
    (el("gtEditCanal")     || {}).value = tarefa.canal_entrega || "";
    (el("gtEditObservacao") || {}).value = tarefa.observacao || "";
    (el("gtEditTempo")     || {}).value = tarefa.segundos_gastos > 0
      ? segundosParaHm(tarefa.segundos_gastos)
      : "";
    const sel = el("gtEditConcluida");
    if (sel) sel.value = tarefa.concluida ? "1" : "0";

    const info = el("gtEditInfo");
    if (info) {
      info.textContent = `${tarefa.nome_exibicao || tarefa.user_id} · ${dataIsoBr(tarefa.referencia_data)} · ${tarefa.atividade_titulo || "—"}`;
    }

    const btn = el("gtBtnSalvar");
    if (btn) btn.disabled = false;

    const errDiv = el("gtEditErro");
    if (errDiv) { errDiv.textContent = ""; errDiv.classList.add("d-none"); }

    const modal = bootstrap.Modal.getOrCreateInstance(el("modalEditarTarefa"));
    modal.show();
  };

  async function _salvarEdicao() {
    const btn = el("gtBtnSalvar");
    const errDiv = el("gtEditErro");

    const titulo = (el("gtEditTitulo") || {}).value?.trim() || "";
    const canal  = (el("gtEditCanal")  || {}).value?.trim() || "";
    const obs    = (el("gtEditObservacao") || {}).value?.trim() || "";
    const tempoStr = (el("gtEditTempo") || {}).value?.trim() || "";
    const concluida = (el("gtEditConcluida") || {}).value === "1";

    if (titulo.length < 2) {
      if (errDiv) { errDiv.textContent = "Título muito curto."; errDiv.classList.remove("d-none"); }
      return;
    }

    if (btn) btn.disabled = true;
    if (errDiv) errDiv.classList.add("d-none");

    const payload = {
      id_subtarefa: _idEditando,
      titulo,
      canal_entrega: canal,
      observacao: obs,
      concluida,
    };
    if (tempoStr !== "") payload.segundos_gastos = hmParaSegundos(tempoStr);

    try {
      const r = await fetch(URL_EDITAR, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const j = await r.json();
      if (!j.ok) throw new Error(j.mensagem || "Erro ao salvar");

      bootstrap.Modal.getOrCreateInstance(el("modalEditarTarefa")).hide();
      await carregarTarefas();
    } catch (err) {
      if (errDiv) { errDiv.textContent = err.message; errDiv.classList.remove("d-none"); }
      if (btn) btn.disabled = false;
    }
  }

  // ─── inicialização ────────────────────────────────────────────────────────
  function _inicializar() {
    // datas padrão: últimos 30 dias
    const hoje = dataHojeIso();
    const inicio30 = (() => {
      const d = new Date(hoje + "T12:00:00");
      d.setDate(d.getDate() - 29);
      return [d.getFullYear(), String(d.getMonth()+1).padStart(2,"0"), String(d.getDate()).padStart(2,"0")].join("-");
    })();
    const di = el("gtDataInicio");
    const df = el("gtDataFim");
    if (di && !di.value) di.value = inicio30;
    if (df && !df.value) df.value = hoje;

    el("gtBtnBuscar")   ?.addEventListener("click", carregarTarefas);
    el("gtBtnSalvar")   ?.addEventListener("click", _salvarEdicao);

    _carregarCombos();
  }

  // expõe para o painel.js acionar ao trocar aba
  window.inicializarAbaGerenciarTarefas = function () {
    _inicializar();
    carregarTarefas();
  };

  window.recarregarAbaGerenciarTarefas = carregarTarefas;

  document.addEventListener("DOMContentLoaded", _inicializar);
})();
