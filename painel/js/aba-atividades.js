/* painel/js/aba-atividades.js */
(function () {
  "use strict";

  // Redesign (tarefa 11 + ajuste): a tabela antiga virou LISTA de linhas ricas
  // #listaAtividades (canal.php), com filtros de status (ativo/inativo) e de
  // usuário. Toggle #chkMostrarAdm oculta/mostra a conta 'adm' nos vínculos
  // (padrão: oculta).
  const seletorLista = "#listaAtividades";
  const seletorBusca = "#entradaBuscaAtividades";
  const seletorMostrarAdm = "#chkMostrarAdm";
  const seletorFiltroStatus = "#filtroStatusAtividades";
  const seletorFiltroUsuario = "#filtroUsuarioAtividades";
  const CHAVE_PREF_MOSTRAR_ADM = "canais_mostrar_adm";
  const CHAVE_PREF_USUARIOS_OCULTOS = "canais_usuarios_ocultos";

  // Usuários ocultados individualmente pela legenda (persistido). Vazio =
  // todos visíveis (padrão). Só afeta os CHIPS exibidos — o cálculo de
  // "Sem vínculos" continua olhando os vínculos reais.
  let usuariosOcultos = new Set();
  try {
    const salvo = JSON.parse(localStorage.getItem(CHAVE_PREF_USUARIOS_OCULTOS) || "[]");
    if (Array.isArray(salvo)) usuariosOcultos = new Set(salvo.map(String));
  } catch (_) { /* padrão: todos visíveis */ }

  function salvarUsuariosOcultos() {
    try { localStorage.setItem(CHAVE_PREF_USUARIOS_OCULTOS, JSON.stringify([...usuariosOcultos])); } catch (_) {}
  }

  const seletorModal = "#modalNovaAtividade";
  const seletorTitulo = "#entradaAtividadeTitulo";
  const seletorDescricao = "#entradaAtividadeDescricao";
  const seletorDificuldade = "#entradaAtividadeDificuldade";
  const seletorEstimativa = "#entradaAtividadeEstimativa";
  const seletorStatus = "#entradaAtividadeStatus";
  const seletorBotaoSalvar = "#botaoSalvarAtividade";

  const seletorListaUsuarios = "#listaUsuariosAtividade";
  const seletorBuscaUsuarios = "#entradaBuscaUsuariosAtividade";

  const urlListarAtividades = "./commands/atividades/listar.php";
  const urlCriarAtividade = "./commands/atividades/criar.php";
  const urlEditarAtividade = "./commands/atividades/editar.php"; // se quiser debug: "./commands/atividades/editar.php?debug=1"
  const urlAlterarStatus = "./commands/atividades/alterar_status.php";
  const urlExcluirAtividade = "./commands/atividades/excluir.php";
  const urlListarUsuariosAtivos = "./commands/usuarios/listar_ativos.php";

  let cacheAtividades = [];
  let cacheUsuariosAtivos = [];

  let modoModal = "criar"; // criar | editar
  let idAtividadeEmEdicao = 0;

  // Seleção atual de usuários vinculados ao canal em edição/criação.
  // Mantém os IDs marcados mesmo quando a lista é re-renderizada pelo
  // filtro de busca — sem isso, os checkboxes fora do filtro perdem o
  // estado e o salvar acaba removendo usuários por engano.
  const idsUsuariosSelecionadosAtividade = new Set();

  function obterElemento(seletor) {
    return document.querySelector(seletor);
  }

  function obterTextoSeguro(v) {
    return (v === null || v === undefined) ? "" : String(v);
  }

  function escaparHtml(s) {
    return obterTextoSeguro(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatarHoras(v) {
    const n = Number(v || 0);
    if (!Number.isFinite(n)) return "—";
    return `${n.toLocaleString("pt-BR", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}h`;
  }

  function formatarDataHoraPtBr(dt) {
    if (!dt) return "—";
    const d = new Date(obterTextoSeguro(dt).replace(" ", "T"));
    if (Number.isNaN(d.getTime())) return "—";
    return d.toLocaleString("pt-BR");
  }

  function textoDificuldade(d) {
    switch (d) {
      case "facil": return "Fácil";
      case "media": return "Média";
      case "dificil": return "Difícil";
      case "critica": return "Crítica";
      default: return "—";
    }
  }

  // Status binário (tarefa 11): a UI só conhece Ativado/Desativado.
  // Legado no banco: aberta|em_andamento → ATIVO; concluida|cancelada → INATIVO.
  // O switch grava 'aberta' (ligar) ou 'cancelada' (desligar) via alterar_status.
  function statusEhAtivo(s) {
    return s === "aberta" || s === "em_andamento";
  }
  function statusParaBinario(s) {
    return statusEhAtivo(s) ? "aberta" : "cancelada";
  }

  function ehAdm(u) {
    return obterTextoSeguro(u?.user_id).trim().toLowerCase() === "adm";
  }
  function deveMostrarAdm() {
    return document.querySelector(seletorMostrarAdm)?.checked === true;
  }
  function usuariosVisiveis(a) {
    const lista = Array.isArray(a.usuarios) ? a.usuarios : [];
    return deveMostrarAdm() ? lista : lista.filter((u) => !ehAdm(u));
  }

  function normalizarDecimalBrl(valor) {
    let s = obterTextoSeguro(valor).trim();
    if (!s) return NaN;

    s = s.replaceAll("R$", "").replaceAll(" ", "");

    const temVirgula = s.includes(",");
    const temPonto = s.includes(".");

    if (temVirgula && temPonto) {
      // último separador manda
      if (s.lastIndexOf(",") > s.lastIndexOf(".")) {
        // 1.234,56
        s = s.replaceAll(".", "").replaceAll(",", ".");
      } else {
        // 1,234.56
        s = s.replaceAll(",", "");
      }
    } else if (temVirgula) {
      // 123,45
      s = s.replaceAll(".", "").replaceAll(",", ".");
    } else {
      // 123.45 ou 123
      // não remove ponto porque pode ser decimal
    }

    const n = Number(s);
    return Number.isFinite(n) ? n : NaN;
  }


  async function requisitarJson(url, opcoes) {
    const resp = await fetch(url, {
      cache: "no-store",
      ...opcoes,
    });

    const json = await resp.json().catch(() => null);

    if (!json || typeof json.ok !== "boolean") {
      throw new Error("Resposta inválida do servidor.");
    }
    if (!resp.ok || json.ok === false) {
      const base = json.mensagem || "Falha na requisição.";
      const d = json.dados;
      const detalhe = (d && typeof d === "object")
        ? [d.erro, d.arquivo && `@${d.arquivo}:${d.linha || "?"}`].filter(Boolean).join(" ")
        : "";
      throw new Error(detalhe ? `${base} — ${detalhe}` : base);
    }
    return json;
  }

  function renderizarUsuariosChips(usuarios) {
    const lista = Array.isArray(usuarios) ? usuarios : [];
    if (lista.length === 0) return "";

    return lista.map((u) => {
      const userId = obterTextoSeguro(u.user_id || "");
      const nome = obterTextoSeguro(u.nome_exibicao || u.user_id || "");
      // Chip colorido do Design System v2 (cor única por usuário).
      if (typeof window.chipUsuarioHtml === "function") {
        return window.chipUsuarioHtml(userId, nome);
      }
      return `<span class="chip" title="${escaparHtml(nome)}">${escaparHtml(userId)}</span>`;
    }).join(" ");
  }

  // Linha rica de canal (lista — mantém as cores/design do redesign: switch
  // binário, chips coloridos, destaque "Sem vínculos", inativo esmaecido).
  function montarLinhaCanal(a) {
    const id = Number(a.id_atividade || 0);
    const titulo = escaparHtml(a.titulo || "");
    const descricao = escaparHtml(a.descricao || "");
    const dificuldade = obterTextoSeguro(a.dificuldade || "");
    const ativo = statusEhAtivo(obterTextoSeguro(a.status || ""));
    const estimativa = formatarHoras(a.estimativa_horas);
    const criado = formatarDataHoraPtBr(a.criado_em);

    const visiveis = usuariosVisiveis(a);
    const semVinculo = visiveis.length === 0;
    // Ocultação individual pela legenda: só esconde chips; "Sem vínculos"
    // continua refletindo os vínculos reais.
    const exibidos = visiveis.filter((u) => !usuariosOcultos.has(obterTextoSeguro(u.user_id)));
    const nOcultos = visiveis.length - exibidos.length;
    let chipsHtml;
    if (semVinculo) {
      chipsHtml = '<span class="badge badge-alerta">⚠ Sem vínculos</span>';
    } else {
      chipsHtml = renderizarUsuariosChips(exibidos);
      if (nOcultos > 0) {
        chipsHtml += ` <span class="texto-fraco small" title="Usuário(s) ocultado(s) pela legenda acima">+${nOcultos} oculto${nOcultos === 1 ? "" : "s"}</span>`;
      }
    }

    const classes = ["canal-linha"];
    if (!ativo) classes.push("canal-linha--inativo");
    if (semVinculo && ativo) classes.push("canal-linha--sem-vinculo");

    return `
      <div class="${classes.join(" ")}" data-id-atividade="${id}">
        <label class="form-check form-switch m-0 d-flex align-items-center flex-shrink-0"
               title="${ativo ? "Canal ativado — clique para desativar" : "Canal desativado — clique para ativar"}">
          <input class="form-check-input m-0" type="checkbox" role="switch"
                 data-acao="switch-status" data-id="${id}" ${ativo ? "checked" : ""}>
        </label>

        <div class="canal-linha__main">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <strong>${titulo}</strong>
            <span class="badge badge-suave" title="Dificuldade">${escaparHtml(textoDificuldade(dificuldade))}</span>
            <span class="badge badge-suave texto-mono" title="Estimativa de horas">⏱ ${escaparHtml(estimativa)}</span>
            ${ativo ? "" : '<span class="badge badge-perigo">Desativado</span>'}
          </div>
          <div class="texto-fraco small text-truncate" title="${descricao}">${descricao || "Sem descrição."} <span style="opacity:.55">· criado em ${criado}</span></div>
        </div>

        <div class="canal-linha__chips">${chipsHtml}</div>

        <div class="d-flex gap-1 flex-shrink-0">
          <button class="btn btn-outline-light btn-sm" data-acao="editar" data-id="${id}" title="Editar canal">✎</button>
          <button class="btn btn-outline-danger btn-sm" data-acao="excluir" data-id="${id}" title="Excluir canal">🗑</button>
        </div>
      </div>
    `;
  }

  // Popula o filtro "Todos os usuários" com os usuários que aparecem em algum
  // canal (respeitando o toggle "Mostrar adm").
  function popularFiltroUsuarios() {
    const sel = obterElemento(seletorFiltroUsuario);
    if (!sel) return;
    const atual = sel.value;
    const vistos = new Map();
    cacheAtividades.forEach((a) => {
      (Array.isArray(a.usuarios) ? a.usuarios : []).forEach((u) => {
        if (!deveMostrarAdm() && ehAdm(u)) return;
        const uid = obterTextoSeguro(u.user_id);
        if (uid && !vistos.has(uid)) vistos.set(uid, obterTextoSeguro(u.nome_exibicao || uid));
      });
    });
    const opcoes = [...vistos.entries()]
      .sort((x, y) => x[1].localeCompare(y[1]))
      .map(([uid, nome]) => `<option value="${escaparHtml(uid)}">${escaparHtml(nome)}</option>`)
      .join("");
    sel.innerHTML = `<option value="">Todos os usuários</option>` + opcoes;
    if (atual && vistos.has(atual)) sel.value = atual;
  }

  // Legenda clicável de usuários: chip aceso = visível; clicado/apagado =
  // oculto nas linhas. Padrão: todos visíveis. Respeita o toggle "Mostrar adm".
  function renderizarLegendaUsuarios() {
    const bloco = document.getElementById("blocoLegendaUsuariosCanais");
    const legenda = document.getElementById("legendaUsuariosCanais");
    if (!bloco || !legenda) return;

    const vistos = new Map();
    cacheAtividades.forEach((a) => {
      (Array.isArray(a.usuarios) ? a.usuarios : []).forEach((u) => {
        if (!deveMostrarAdm() && ehAdm(u)) return;
        const uid = obterTextoSeguro(u.user_id);
        if (uid && !vistos.has(uid)) vistos.set(uid, obterTextoSeguro(u.nome_exibicao || uid));
      });
    });

    if (!vistos.size) { bloco.classList.add("d-none"); return; }
    bloco.classList.remove("d-none");

    legenda.innerHTML = [...vistos.entries()]
      .sort((x, y) => x[1].localeCompare(y[1]))
      .map(([uid, nome]) => {
        const oculto = usuariosOcultos.has(uid);
        const chip = (typeof window.chipUsuarioHtml === "function")
          ? window.chipUsuarioHtml(uid, nome)
          : `<span class="chip">${escaparHtml(nome)}</span>`;
        return `<button type="button" class="chip-usuario-toggle${oculto ? " chip-usuario-toggle--off" : ""}"
                        data-toggle-usuario="${escaparHtml(uid)}"
                        title="${oculto ? "Oculto — clique para mostrar" : "Visível — clique para ocultar"}">${chip}</button>`;
      }).join("");
  }

  function aplicarFiltroETabela() {
    const lista = obterElemento(seletorLista);
    if (!lista) return;

    const termo = obterTextoSeguro(obterElemento(seletorBusca)?.value).trim().toLowerCase();
    const filtroStatus = obterTextoSeguro(obterElemento(seletorFiltroStatus)?.value);
    const filtroUsuario = obterTextoSeguro(obterElemento(seletorFiltroUsuario)?.value);

    const filtradas = cacheAtividades.filter((a) => {
      const ativo = statusEhAtivo(obterTextoSeguro(a.status));
      if (filtroStatus === "ativo" && !ativo) return false;
      if (filtroStatus === "inativo" && ativo) return false;

      if (filtroUsuario) {
        const usuarios = Array.isArray(a.usuarios) ? a.usuarios : [];
        if (!usuarios.some((u) => obterTextoSeguro(u.user_id) === filtroUsuario)) return false;
      }

      if (termo === "") return true;
      const titulo = obterTextoSeguro(a.titulo).toLowerCase();
      const dif = obterTextoSeguro(a.dificuldade).toLowerCase();
      const usuarios = Array.isArray(a.usuarios) ? a.usuarios : [];
      const usuariosTexto = usuarios.map((u) => `${u.user_id} ${u.nome_exibicao}`).join(" ").toLowerCase();
      return `${titulo} ${dif} ${usuariosTexto}`.includes(termo);
    });

    // Ordena: ativos sem vínculo primeiro (precisam de atenção), depois ativos,
    // depois desativados.
    const peso = (a) => {
      const ativo = statusEhAtivo(obterTextoSeguro(a.status));
      if (!ativo) return 2;
      return usuariosVisiveis(a).length === 0 ? 0 : 1;
    };
    filtradas.sort((x, y) => peso(x) - peso(y) || obterTextoSeguro(x.titulo).localeCompare(obterTextoSeguro(y.titulo)));

    const badge = document.getElementById("badgeTotalAtividades");
    if (badge) {
      badge.textContent = filtradas.length === cacheAtividades.length
        ? String(cacheAtividades.length)
        : `${filtradas.length}/${cacheAtividades.length}`;
    }

    if (filtradas.length === 0) {
      lista.innerHTML = `<div class="mega-vazio"><div class="mega-vazio-icone">📺</div><div><strong>Nenhum canal encontrado</strong></div><div class="texto-fraco small">Ajuste a busca/filtros ou clique em <strong>+ Adicionar Canal</strong>.</div></div>`;
      return;
    }

    lista.innerHTML = filtradas.map(montarLinhaCanal).join("");
  }

  async function carregarAtividades() {
    const lista = obterElemento(seletorLista);
    if (lista) lista.innerHTML = `<div class="texto-fraco">Carregando…</div>`;

    const json = await requisitarJson(urlListarAtividades, { method: "GET" });
    cacheAtividades = Array.isArray(json.dados) ? json.dados : [];
    popularFiltroUsuarios();
    renderizarLegendaUsuarios();
    aplicarFiltroETabela();
  }

  async function carregarUsuariosAtivos() {
    const container = obterElemento(seletorListaUsuarios);
    if (container) container.innerHTML = `<div class="texto-fraco">Carregando usuários…</div>`;

    const json = await requisitarJson(urlListarUsuariosAtivos, { method: "GET" });
    cacheUsuariosAtivos = Array.isArray(json.dados) ? json.dados : [];

    renderizarListaUsuariosAtividade("");
  }

  function renderizarListaUsuariosAtividade(termo) {
    const container = obterElemento(seletorListaUsuarios);
    if (!container) return;

    const t = obterTextoSeguro(termo).trim().toLowerCase();

    const lista = cacheUsuariosAtivos.filter((u) => {
      const base = `${u.user_id} ${u.nome_exibicao} ${u.nivel}`.toLowerCase();
      return t === "" ? true : base.includes(t);
    });

    if (lista.length === 0) {
      container.innerHTML = `<div class="texto-fraco">Nenhum usuário ativo encontrado.</div>`;
      return;
    }

    container.innerHTML = lista.map((u) => {
      const idUsuario = Number(u.id_usuario || 0);
      const userId = escaparHtml(u.user_id);
      const nome = escaparHtml(u.nome_exibicao);
      const nivel = escaparHtml(u.nivel);
      const checked = idsUsuariosSelecionadosAtividade.has(idUsuario) ? " checked" : "";

      return `
        <label class="cartao-grafite p-2 d-flex align-items-center justify-content-between" style="cursor:pointer;">
          <div class="d-flex align-items-center gap-2">
            <input type="checkbox" class="form-check-input m-0" data-id-usuario="${idUsuario}"${checked}>
            <div>
              <div class="fw-semibold">${nome}</div>
              <div class="texto-fraco small">${userId} · ${nivel}</div>
            </div>
          </div>
        </label>
      `;
    }).join("");
  }

  function obterIdsUsuariosSelecionados() {
    // Fonte da verdade: o `Set` em memória. Os checkboxes renderizados na
    // tela só refletem a lista filtrada pela busca — usar `querySelectorAll`
    // aqui removeria silenciosamente os usuários que ficaram fora do filtro.
    const selecionados = [];
    idsUsuariosSelecionadosAtividade.forEach((idUsuario) => {
      const n = Number(idUsuario || 0);
      if (n > 0) selecionados.push(n);
    });
    return selecionados;
  }

  function limparFormularioModal() {
    const titulo = obterElemento(seletorTitulo);
    const desc = obterElemento(seletorDescricao);
    const dif = obterElemento(seletorDificuldade);
    const est = obterElemento(seletorEstimativa);
    const st = obterElemento(seletorStatus);
    const buscaUsuarios = obterElemento(seletorBuscaUsuarios);

    if (titulo) titulo.value = "";
    if (desc) desc.value = "";
    if (dif) dif.value = "media";
    if (est) est.value = "";
    if (st) st.value = "aberta";
    if (buscaUsuarios) buscaUsuarios.value = "";

    const container = obterElemento(seletorListaUsuarios);
    if (container) {
      container.querySelectorAll('input[type="checkbox"][data-id-usuario]').forEach((c) => { c.checked = false; });
    }
    idsUsuariosSelecionadosAtividade.clear();

    modoModal = "criar";
    idAtividadeEmEdicao = 0;
  }

  function abrirModal() {
    const modalEl = document.querySelector(seletorModal);
    if (!modalEl) return;
    const instancia = window.bootstrap?.Modal?.getOrCreateInstance(modalEl);
    instancia?.show();
  }

  function marcarUsuariosNoModal(usuariosDaAtividade) {
    const container = obterElemento(seletorListaUsuarios);
    if (!container) return;

    const lista = Array.isArray(usuariosDaAtividade) ? usuariosDaAtividade : [];

    // Reset + repopulação do `Set` autoritativo a partir dos vínculos
    // atuais do canal. Os checkboxes visíveis são apenas o espelho.
    idsUsuariosSelecionadosAtividade.clear();
    lista.forEach((u) => {
      const n = Number(u.id_usuario || 0);
      if (n > 0) idsUsuariosSelecionadosAtividade.add(n);
    });

    container.querySelectorAll('input[type="checkbox"][data-id-usuario]').forEach((c) => {
      const idUsuario = Number(c.getAttribute("data-id-usuario") || 0);
      c.checked = idsUsuariosSelecionadosAtividade.has(idUsuario);
    });
  }

  async function salvarAtividade() {
    const titulo = obterTextoSeguro(obterElemento(seletorTitulo)?.value).trim();
    const descricao = obterTextoSeguro(obterElemento(seletorDescricao)?.value).trim();
    const dificuldade = obterTextoSeguro(obterElemento(seletorDificuldade)?.value).trim();
    const status = obterTextoSeguro(obterElemento(seletorStatus)?.value).trim();

    const estimativaTexto = obterTextoSeguro(obterElemento(seletorEstimativa)?.value).trim();
    const estimativaNumero = estimativaTexto === "" ? 0 : normalizarDecimalBrl(estimativaTexto);

    if (titulo === "") throw new Error("Informe o título da atividade.");
    if (titulo.length < 3) throw new Error("Título inválido (mínimo 3 caracteres).");
    if (!["facil", "media", "dificil", "critica"].includes(dificuldade)) throw new Error("Selecione uma dificuldade válida.");
    // UI binária (tarefa 11): qualquer valor legado é normalizado.
    if (!["aberta", "em_andamento", "concluida", "cancelada"].includes(status)) throw new Error("Selecione um status válido.");
    const statusNormalizado = statusParaBinario(status);
    if (!Number.isFinite(estimativaNumero) || estimativaNumero < 0) throw new Error("Estimativa inválida. Use um número (ex: 6 ou 6,5).");

    const ids_usuarios = obterIdsUsuariosSelecionados();
    if (ids_usuarios.length < 1) throw new Error("Selecione ao menos 1 usuário.");

    if (modoModal === "criar") {
      await requisitarJson(urlCriarAtividade, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({
          titulo,
          descricao,
          dificuldade,
          estimativa_horas: estimativaNumero,
          status: statusNormalizado,
          ids_usuarios
        })
      });
    } else {
      if (idAtividadeEmEdicao <= 0) throw new Error("Não encontrei a atividade para editar.");

      await requisitarJson(urlEditarAtividade, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({
          id_atividade: idAtividadeEmEdicao,
          titulo,
          descricao,
          dificuldade,
          estimativa_horas: estimativaNumero,
          status: statusNormalizado,
          ids_usuarios
        })
      });
    }

    await carregarAtividades();

    const modalEl = document.querySelector(seletorModal);
    if (modalEl) {
      const instancia = window.bootstrap?.Modal?.getOrCreateInstance(modalEl);
      instancia?.hide();
    }

    limparFormularioModal();
  }

  async function alterarStatusAtividade(id_atividade, status) {
    await requisitarJson(urlAlterarStatus, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ id_atividade, status })
    });
    await carregarAtividades();
  }

  async function excluirAtividade(id_atividade) {
    const ok = window.confirm("Tem certeza que deseja excluir esta atividade? Essa ação não pode ser desfeita.");
    if (!ok) return;

    await requisitarJson(urlExcluirAtividade, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ id_atividade })
    });

    await carregarAtividades();
  }

  async function editarAtividade(id_atividade) {
    const atividade = cacheAtividades.find((a) => Number(a.id_atividade || 0) === Number(id_atividade));
    if (!atividade) throw new Error("Atividade não encontrada.");

    modoModal = "editar";
    idAtividadeEmEdicao = Number(id_atividade);

    // carrega usuários e depois marca
    await carregarUsuariosAtivos();

    const titulo = obterElemento(seletorTitulo);
    const desc = obterElemento(seletorDescricao);
    const dif = obterElemento(seletorDificuldade);
    const est = obterElemento(seletorEstimativa);
    const st = obterElemento(seletorStatus);

    if (titulo) titulo.value = obterTextoSeguro(atividade.titulo);
    if (desc) desc.value = obterTextoSeguro(atividade.descricao);
    if (dif) dif.value = obterTextoSeguro(atividade.dificuldade || "media");
    if (est) est.value = obterTextoSeguro(atividade.estimativa_horas || "");
    if (st) st.value = statusParaBinario(obterTextoSeguro(atividade.status || "aberta"));

    marcarUsuariosNoModal(atividade.usuarios);
    abrirModal();
  }

  function registrarEventosTabela() {
    document.addEventListener("change", async (ev) => {
      const alvo = ev.target;
      if (!(alvo instanceof HTMLElement)) return;

      // Switch Ativado/Desativado do card (tarefa 11).
      if (alvo.matches('input[data-acao="switch-status"][data-id]')) {
        const id = Number(alvo.getAttribute("data-id") || 0);
        const status = alvo.checked ? "aberta" : "cancelada";
        if (id > 0) {
          alvo.disabled = true;
          try {
            await alterarStatusAtividade(id, status);
          } catch (e) {
            console.error(e);
            alvo.checked = !alvo.checked; // reverte visual em caso de falha
            alvo.disabled = false;
            window.PainelNucleo?.utilidades?.mostrarAlerta?.("erro", "Canais", String(e?.message || e));
          }
        }
      }
    });

    document.addEventListener("click", async (ev) => {
      const alvo = ev.target;
      if (!(alvo instanceof HTMLElement)) return;

      if (alvo.matches('button[data-acao="excluir"][data-id]')) {
        const id = Number(alvo.getAttribute("data-id") || 0);
        if (id > 0) {
          try { await excluirAtividade(id); } catch (e) { console.error(e); }
        }
      }

      if (alvo.matches('button[data-acao="editar"][data-id]')) {
        const id = Number(alvo.getAttribute("data-id") || 0);
        if (id > 0) {
          try { await editarAtividade(id); } catch (e) { console.error(e); }
        }
      }
    });
  }

  function registrarEventosModal() {
    const botaoSalvar = obterElemento(seletorBotaoSalvar);
    if (botaoSalvar) {
      botaoSalvar.addEventListener("click", async () => {
        botaoSalvar.disabled = true;
        try {
          await salvarAtividade();
        } catch (e) {
          console.error(e);
          if (window.PainelNucleo?.utilidades?.mostrarAlerta) {
            window.PainelNucleo.utilidades.mostrarAlerta("erro", "Falha", String(e && e.message ? e.message : e));
          }
        } finally {
          botaoSalvar.disabled = false;
        }
      });
    }

    const modalEl = document.querySelector(seletorModal);
    if (modalEl) {
      modalEl.addEventListener("show.bs.modal", async () => {
        // se abriu pelo botão "+ Nova", modo criar
        if (idAtividadeEmEdicao <= 0) {
          modoModal = "criar";
          try { await carregarUsuariosAtivos(); } catch (e) { console.error(e); }
        }
      });

      modalEl.addEventListener("hidden.bs.modal", () => {
        limparFormularioModal();
      });
    }

    const buscaUsuarios = obterElemento(seletorBuscaUsuarios);
    if (buscaUsuarios) {
      buscaUsuarios.addEventListener("input", () => {
        renderizarListaUsuariosAtividade(buscaUsuarios.value);
      });
    }

    // Sincroniza o `Set` autoritativo com o estado real dos checkboxes
    // exibidos. Sem isso, marcar/desmarcar um checkbox visível não muda a
    // seleção real até o usuário disparar o salvar.
    const containerUsuarios = obterElemento(seletorListaUsuarios);
    if (containerUsuarios) {
      containerUsuarios.addEventListener("change", (ev) => {
        const alvo = ev.target;
        if (!(alvo instanceof HTMLInputElement)) return;
        if (alvo.type !== "checkbox") return;
        const idUsuario = Number(alvo.getAttribute("data-id-usuario") || 0);
        if (idUsuario <= 0) return;
        if (alvo.checked) idsUsuariosSelecionadosAtividade.add(idUsuario);
        else idsUsuariosSelecionadosAtividade.delete(idUsuario);
      });
    }
  }

  function registrarEventosBusca() {
    const busca = obterElemento(seletorBusca);
    if (busca) {
      let _debounceTimerAtividades = null;
      busca.addEventListener("input", () => {
        clearTimeout(_debounceTimerAtividades);
        _debounceTimerAtividades = setTimeout(() => aplicarFiltroETabela(), 300);
      });
    }

    // Toggle "Mostrar adm" (tarefa 11): persiste a preferência e re-renderiza
    // (o filtro de usuários também muda — adm entra/sai das opções).
    const chkAdm = obterElemento(seletorMostrarAdm);
    if (chkAdm) {
      try { chkAdm.checked = localStorage.getItem(CHAVE_PREF_MOSTRAR_ADM) === "1"; } catch (_) {}
      chkAdm.addEventListener("change", () => {
        try { localStorage.setItem(CHAVE_PREF_MOSTRAR_ADM, chkAdm.checked ? "1" : "0"); } catch (_) {}
        popularFiltroUsuarios();
        renderizarLegendaUsuarios();
        aplicarFiltroETabela();
      });
    }

    // Filtros de status e de usuário da lista.
    obterElemento(seletorFiltroStatus)?.addEventListener("change", () => aplicarFiltroETabela());
    obterElemento(seletorFiltroUsuario)?.addEventListener("change", () => aplicarFiltroETabela());

    // Legenda de usuários: clique alterna visível/oculto (persistido).
    document.getElementById("legendaUsuariosCanais")?.addEventListener("click", (ev) => {
      const btn = ev.target.closest("[data-toggle-usuario]");
      if (!btn) return;
      const uid = btn.getAttribute("data-toggle-usuario") || "";
      if (usuariosOcultos.has(uid)) usuariosOcultos.delete(uid);
      else usuariosOcultos.add(uid);
      salvarUsuariosOcultos();
      renderizarLegendaUsuarios();
      aplicarFiltroETabela();
    });
  }

  function tentarCarregarQuandoAbrirAba() {
    document.addEventListener("click", (ev) => {
      const alvo = ev.target;
      if (!(alvo instanceof HTMLElement)) return;
      if (alvo.matches('a.nav-link[data-aba="abaAtividades"]')) {
        carregarAtividades().catch(console.error);
      }
    });
  }

  function inicializar() {
    registrarEventosTabela();
    registrarEventosModal();
    registrarEventosBusca();
    tentarCarregarQuandoAbrirAba();
  }

  // API global
  window.recarregarAbaAtividades = function () {
    return carregarAtividades();
  };

  inicializar();

  // Página dedicada (canal.php): sem o SPA do index (#abaDashboard), carrega o
  // grid ao abrir. No index a carga é disparada ao clicar na aba "Canal"
  // (tentarCarregarQuandoAbrirAba) ou via window.recarregarAbaAtividades.
  if (!document.getElementById("abaDashboard") && document.querySelector(seletorLista)) {
    carregarAtividades().catch(console.error);
  }
})();
