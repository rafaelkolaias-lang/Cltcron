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

  // Paginação. Substitui o corte silencioso de 500 que vinha do endpoint.
  let _paginaAtual = 1;
  const _perPage = 50;
  let _totalPaginas = 1;
  let _totalRegistros = 0;

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
      _cacheAtividades = (rA.dados || [])
        .filter(a => String(a.status || "").toLowerCase() !== "cancelada");
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
  async function carregarTarefas(pagina) {
    if (_carregando) return;
    _carregando = true;

    if (typeof pagina === "number" && pagina >= 1) {
      _paginaAtual = pagina;
    } else if (pagina === undefined) {
      _paginaAtual = 1;
    }

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
    params.set("page", String(_paginaAtual));
    params.set("per_page", String(_perPage));

    try {
      const r = await fetch(`${URL_LISTAR}?${params}`);
      const j = await r.json();
      if (!j.ok) throw new Error(j.mensagem || "Erro na API");
      _dados = j.dados || [];
      const pag = j.paginacao || {};
      _totalPaginas = Number(pag.total_pages ?? 1);
      _totalRegistros = Number(pag.total ?? _dados.length);
      _paginaAtual = Number(pag.page ?? _paginaAtual);
    } catch (err) {
      _dados = [];
      _totalPaginas = 1;
      _totalRegistros = 0;
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-danger text-center py-3">Erro: ${esc(err.message)}</td></tr>`;
      _carregando = false;
      _renderPaginacao();
      return;
    }

    _renderizar();
    _renderPaginacao();
    _carregando = false;
  }

  // Fallback local do HTML de paginação. No index.php quem expõe
  // window.__paginacaoTarefasHtml é o aba-usuarios.js; em página dedicada
  // (gerenciar-tarefas.php) ele não é carregado, então geramos aqui os mesmos
  // botões data-pag que o handler de clique espera.
  function _paginacaoHtmlLocal(pageAtual, totalPages) {
    if (!totalPages || totalPages <= 1) return "";
    const segura = (n) => Math.min(Math.max(1, n), totalPages);
    const partes = ['<ul class="pagination pagination-sm mb-0" role="navigation">'];
    partes.push(`<li class="page-item ${pageAtual <= 1 ? "disabled" : ""}"><button class="page-link bg-transparent text-light border-secondary" data-pag="${segura(pageAtual - 1)}" ${pageAtual <= 1 ? "disabled" : ""} aria-label="Anterior">«</button></li>`);
    const ini = Math.max(1, pageAtual - 3), fim = Math.min(totalPages, pageAtual + 3);
    if (ini > 1) partes.push('<li class="page-item disabled"><span class="page-link bg-transparent text-light border-secondary">…</span></li>');
    for (let n = ini; n <= fim; n++) {
      const ativa = n === pageAtual;
      partes.push(`<li class="page-item ${ativa ? "active" : ""}"><button class="page-link ${ativa ? "" : "bg-transparent text-light"} border-secondary" data-pag="${n}" ${ativa ? 'aria-current="page"' : ""}>${n}</button></li>`);
    }
    if (fim < totalPages) partes.push('<li class="page-item disabled"><span class="page-link bg-transparent text-light border-secondary">…</span></li>');
    partes.push(`<li class="page-item ${pageAtual >= totalPages ? "disabled" : ""}"><button class="page-link bg-transparent text-light border-secondary" data-pag="${segura(pageAtual + 1)}" ${pageAtual >= totalPages ? "disabled" : ""} aria-label="Próxima">»</button></li>`);
    partes.push("</ul>");
    return partes.join("");
  }

  function _renderPaginacao() {
    const nav = el("paginacaoGerenciarTarefas");
    if (!nav) return;
    if (!_totalPaginas || _totalPaginas <= 1) {
      nav.innerHTML = "";
      return;
    }
    const html = typeof window.__paginacaoTarefasHtml === "function"
      ? window.__paginacaoTarefasHtml(_paginaAtual, _totalPaginas, "gt")
      : _paginacaoHtmlLocal(_paginaAtual, _totalPaginas);
    nav.innerHTML = html;
    nav.querySelectorAll("button[data-pag]").forEach((b) => {
      b.addEventListener("click", () => {
        const p = Number(b.getAttribute("data-pag") || 1);
        if (p >= 1 && p !== _paginaAtual) carregarTarefas(p);
      });
    });
  }

  // ─── renderizar tabela ────────────────────────────────────────────────────
  function _renderizar() {
    const tbody = el("tbodyGerenciarTarefas");
    const total = el("gtTotalRegistros");
    if (!tbody) return;

    if (total) {
      // Mostra total global (não só da página atual) quando o backend
      // devolve metadado de paginação.
      const totalGlobal = Number(_totalRegistros || _dados.length);
      if (_totalPaginas > 1) {
        total.textContent = `${totalGlobal} registro(s) · pág. ${_paginaAtual}/${_totalPaginas}`;
      } else {
        total.textContent = `${totalGlobal} registro(s)`;
      }
    }

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
      const canalLimpo = String(t.canal_entrega || "")
        .replace(/^#\d+\s*-\s*/, "")
        .replace(/\s*\([^)]*\)\s*$/, "")
        .trim();
      const canal = canalLimpo ? esc(canalLimpo) : '<span class="texto-fraco">—</span>';
      // Badge [CANCELADO] quando o canal está cancelado — visual apenas; subtarefa
      // continua editável e segue contando nos cálculos (preserva histórico de pagamento).
      const canalCancelado = String(t.status_atividade || "").toLowerCase() === "cancelada";
      const canalBadge = canalCancelado
        ? ' <span class="badge bg-secondary" title="Canal cancelado pelo admin — subtarefa preservada">[CANCELADO]</span>'
        : '';
      const linhaStyle = canalCancelado ? ' style="opacity:0.55;"' : '';
      const obs = String(t.observacao || "").trim();
      const obsHtml = obs
        ? `<span title="${esc(obs)}" style="display:inline-block;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom;">${esc(obs)}</span>`
        : '<span class="texto-fraco">—</span>';
      const btnEditar = bloqueada
        ? `<button class="btn btn-sm btn-outline-secondary" disabled title="Bloqueada por pagamento">Editar</button>`
        : `<button class="btn btn-sm btn-outline-light botao-mini" onclick="gtAbrirEdicao(${t.id_subtarefa})">Editar</button>`;

      return `
        <tr${linhaStyle}>
          <td class="small">${esc(dataIsoBr(t.referencia_data))}</td>
          <td class="small">${esc(t.nome_exibicao || t.user_id)}</td>
          <td class="small">${canal}${canalBadge}</td>
          <td class="small">${esc(t.titulo)}${travaBadge}</td>
          <td class="small">${tempo}</td>
          <td class="small">${obsHtml}</td>
          <td class="text-center">${statusBadge}</td>
          <td class="text-end">${btnEditar}</td>
        </tr>`;
    }).join("");
  }

  // ─── modal de edição ──────────────────────────────────────────────────────
  window.gtAbrirEdicao = function (id, tarefaExterna) {
    const tarefa = tarefaExterna || _dados.find(t => t.id_subtarefa === id);
    if (!tarefa) return;
    _idEditando = id;

    const inputTitulo = el("gtEditTitulo");
    if (inputTitulo) inputTitulo.value = tarefa.titulo || "";
    (el("gtEditCanal")     || {}).value = tarefa.canal_entrega || "";
    (el("gtEditObservacao") || {}).value = tarefa.observacao || "";
    (el("gtEditTempo")     || {}).value = tarefa.segundos_gastos > 0
      ? segundosParaHm(tarefa.segundos_gastos)
      : "";
    const sel = el("gtEditConcluida");
    if (sel) sel.value = tarefa.concluida ? "1" : "0";

    // Tarefas MEGA não podem ser renomeadas pelo painel — o nome do
    // título está acoplado à pasta no MEGA e à `mega_pasta_logica`.
    // Mudar só o título aqui dessincronizaria banco e MEGA. Bloqueamos
    // visualmente; o backend também recusa. Os outros campos seguem
    // editáveis.
    const aviso = el("gtEditAvisoMega");
    if (tarefa.mega_pasta_vinculada) {
      if (inputTitulo) {
        inputTitulo.readOnly = true;
        inputTitulo.title = "Renomeação bloqueada — tarefa vinculada a uma pasta no MEGA.";
        inputTitulo.classList.add("text-muted");
      }
      if (aviso) {
        aviso.textContent = "Tarefa vinculada a uma pasta no MEGA: o título está bloqueado para evitar dessincronização. Demais campos seguem editáveis.";
        aviso.classList.remove("d-none");
      }
    } else {
      if (inputTitulo) {
        inputTitulo.readOnly = false;
        inputTitulo.removeAttribute("title");
        inputTitulo.classList.remove("text-muted");
      }
      if (aviso) {
        aviso.textContent = "";
        aviso.classList.add("d-none");
      }
    }

    // Vídeo publicado: pasta fechada. Só a HORA declarada e a DESCRIÇÃO podem
    // mudar — canal e status de conclusão ficam travados (o título já fica
    // travado por ser tarefa MEGA). O backend (editar.php) também recusa, e
    // não há exclusão de tarefa pelo painel.
    const canalEl = el("gtEditCanal");
    const conclEl = el("gtEditConcluida");
    if (tarefa.video_publicado) {
      if (canalEl) { canalEl.disabled = true; canalEl.title = "Vídeo publicado — bloqueado."; }
      if (conclEl) { conclEl.disabled = true; conclEl.title = "Vídeo publicado — bloqueado."; }
      if (aviso) {
        aviso.textContent = "Vídeo publicado: só dá pra alterar a hora declarada e a descrição. Título, canal e status ficam bloqueados, e a tarefa não pode ser excluída.";
        aviso.classList.remove("d-none");
      }
    } else {
      if (canalEl) { canalEl.disabled = false; canalEl.removeAttribute("title"); }
      if (conclEl) { conclEl.disabled = false; conclEl.removeAttribute("title"); }
    }

    const info = el("gtEditInfo");
    if (info) {
      info.textContent = `${tarefa.nome_exibicao || tarefa.user_id} · ${dataIsoBr(tarefa.referencia_data)} · ${tarefa.atividade_titulo || "—"}`;
    }

    // Painel de horas acumuladas: trabalhadas / declaradas / disponíveis (todas as datas)
    const horasBox = el("gtEditHorasInfo");
    if (horasBox && tarefa.segundos_trabalhados_total !== undefined) {
      const trab = tarefa.segundos_trabalhados_total || 0;
      const decl = tarefa.segundos_declarados_total || 0;
      const disp = Math.max(0, trab - decl + tarefa.segundos_gastos); // disponível = trab - outros declarados
      const elTrab = el("gtHorasTrabalhado");
      const elDecl = el("gtHorasDeclarado");
      const elDisp = el("gtHorasDisponivel");
      if (elTrab) elTrab.textContent = segundosParaHm(trab);
      if (elDecl) elDecl.textContent = segundosParaHm(decl);
      if (elDisp) elDisp.textContent = segundosParaHm(disp);
      horasBox.classList.remove("d-none");
    } else if (horasBox) {
      horasBox.classList.add("d-none");
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
      if (typeof window.__onTarefaEditada === "function") window.__onTarefaEditada();
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

  // Página dedicada (gerenciar-tarefas.php): sem o SPA do index (#abaDashboard),
  // carrega a lista ao abrir. No index é sob demanda (painel.js chama
  // recarregarAbaGerenciarTarefas ao trocar de aba). Registrado após o listener
  // de _inicializar para rodar depois dele.
  if (!document.getElementById("abaDashboard")) {
    document.addEventListener("DOMContentLoaded", function () {
      if (document.getElementById("tbodyGerenciarTarefas")) carregarTarefas();
    });
  }
})();
