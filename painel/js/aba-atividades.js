/* painel/js/aba-atividades.js */
(function () {
  "use strict";

  const seletorTbody = "#tbodyAtividades";
  const seletorBusca = "#entradaBuscaAtividades";

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

  function textoStatus(s) {
    switch (s) {
      case "aberta": return "Aberta";
      case "em_andamento": return "Em andamento";
      case "concluida": return "Concluída";
      case "cancelada": return "Cancelada";
      default: return "—";
    }
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
    if (lista.length === 0) return '<span class="texto-fraco small">—</span>';

    return lista.map((u) => {
      const userId = escaparHtml(u.user_id || "");
      const nome = escaparHtml(u.nome_exibicao || u.user_id || "");
      return `<span class="chip" title="${nome}">${userId}</span>`;
    }).join(" ");
  }

  function montarLinhaAtividade(a) {
    const id = Number(a.id_atividade || 0);
    const titulo = escaparHtml(a.titulo || "");
    const descricao = escaparHtml(a.descricao || "");
    const dificuldade = obterTextoSeguro(a.dificuldade || "");
    const status = obterTextoSeguro(a.status || "");
    const estimativa = formatarHoras(a.estimativa_horas);
    const usuariosHtml = renderizarUsuariosChips(a.usuarios);

    const criado = formatarDataHoraPtBr(a.criado_em);

    return `
      <tr>
        <td>
          <div class="fw-semibold">${titulo}</div>
          <div class="texto-fraco small">${descricao || "—"}</div>
          <div class="texto-fraco small mt-1">Criada em: ${criado}</div>
        </td>

        <td class="text-center">
          <span class="badge badge-suave">${escaparHtml(textoDificuldade(dificuldade))}</span>
        </td>

        <td class="text-center">
          <span class="texto-mono">${escaparHtml(estimativa)}</span>
        </td>

        <td>${usuariosHtml}</td>

        <td class="text-center">
          <select class="form-select form-select-sm bg-transparent text-white border-secondary"
            data-acao="status" data-id="${id}">
            <option value="aberta" ${status === "aberta" ? "selected" : ""}>Aberta</option>
            <option value="em_andamento" ${status === "em_andamento" ? "selected" : ""}>Em andamento</option>
            <option value="concluida" ${status === "concluida" ? "selected" : ""}>Concluída</option>
            <option value="cancelada" ${status === "cancelada" ? "selected" : ""}>Cancelada</option>
          </select>
          <div class="texto-fraco small mt-1">${escaparHtml(textoStatus(status))}</div>
        </td>

        <td class="text-end">
          <div class="d-flex justify-content-end gap-2">
            <button class="btn btn-outline-light btn-sm" data-acao="editar" data-id="${id}">Editar</button>
            <button class="btn btn-outline-light btn-sm" data-acao="excluir" data-id="${id}">Excluir</button>
          </div>
        </td>
      </tr>
    `;
  }

  function aplicarFiltroETabela() {
    const tbody = obterElemento(seletorTbody);
    if (!tbody) return;

    const termo = obterTextoSeguro(obterElemento(seletorBusca)?.value).trim().toLowerCase();

    const filtradas = cacheAtividades.filter((a) => {
      const titulo = obterTextoSeguro(a.titulo).toLowerCase();
      const status = obterTextoSeguro(a.status).toLowerCase();
      const dif = obterTextoSeguro(a.dificuldade).toLowerCase();

      const usuarios = Array.isArray(a.usuarios) ? a.usuarios : [];
      const usuariosTexto = usuarios.map((u) => `${u.user_id} ${u.nome_exibicao}`).join(" ").toLowerCase();

      const base = `${titulo} ${status} ${dif} ${usuariosTexto}`;
      return termo === "" ? true : base.includes(termo);
    });

    if (filtradas.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="texto-fraco">Nenhuma atividade encontrada.</td></tr>`;
      return;
    }

    tbody.innerHTML = filtradas.map(montarLinhaAtividade).join("");
  }

  async function carregarAtividades() {
    const tbody = obterElemento(seletorTbody);
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="texto-fraco">Carregando…</td></tr>`;

    const json = await requisitarJson(urlListarAtividades, { method: "GET" });
    cacheAtividades = Array.isArray(json.dados) ? json.dados : [];
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
    if (!["aberta", "em_andamento", "concluida", "cancelada"].includes(status)) throw new Error("Selecione um status válido.");
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
          status,
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
          status,
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
    if (st) st.value = obterTextoSeguro(atividade.status || "aberta");

    marcarUsuariosNoModal(atividade.usuarios);
    abrirModal();
  }

  function registrarEventosTabela() {
    document.addEventListener("change", async (ev) => {
      const alvo = ev.target;
      if (!(alvo instanceof HTMLElement)) return;

      if (alvo.matches('select[data-acao="status"][data-id]')) {
        const id = Number(alvo.getAttribute("data-id") || 0);
        const status = obterTextoSeguro(alvo.value);
        if (id > 0) {
          try { await alterarStatusAtividade(id, status); } catch (e) { console.error(e); }
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
    if (!busca) return;
    let _debounceTimerAtividades = null;
    busca.addEventListener("input", () => {
      clearTimeout(_debounceTimerAtividades);
      _debounceTimerAtividades = setTimeout(() => aplicarFiltroETabela(), 300);
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
})();
