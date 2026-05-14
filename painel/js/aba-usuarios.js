// js/aba-usuarios.js
// Aba Usuários (REAL no banco): listar + criar + gestão (editar/status/pagamentos)

(function () {
  "use strict";

  const nomeModulo = "usuarios";
  let usuarioGestaoAbertoId = "";

  function obterNucleo() {
    return window.PainelNucleo;
  }

  // ============================
  // URLs backend
  // ============================
  function urlListarUsuarios() { return "./commands/usuarios/listar.php"; }
  function urlCriarUsuario() { return "./commands/usuarios/criar.php"; }
  function urlEditarUsuario() { return "./commands/usuarios/editar.php"; }
  function urlAtualizarStatusUsuario() { return "./commands/usuarios/atualizar_status.php"; }
  function urlAlternarVisibilidadeDashboard() { return "./commands/usuarios/alternar_visibilidade_dashboard.php"; }

  function urlListarPagamentosPorUsuario(userId) {
    return `./commands/pagamentos/listar_por_usuario.php?user_id=${encodeURIComponent(userId)}`;
  }
  function urlCriarPagamento() { return "./commands/pagamentos/criar.php"; }
  function urlEditarPagamento() { return "./commands/pagamentos/editar.php"; }
  function urlExcluirPagamento() { return "./commands/pagamentos/excluir.php"; }

  // ============================
  // HTTP helper
  // ============================
  async function requisitarJson(url, opcoes = {}) {
    const resp = await fetch(url, { cache: "no-store", ...opcoes });
    let json = null;

    try {
      json = await resp.json();
    } catch {
      json = null;
    }

    if (!resp.ok) {
      const base = (json && json.mensagem) ? json.mensagem : `HTTP ${resp.status}`;
      const d = json && json.dados;
      const detalhe = (d && typeof d === "object")
        ? [d.erro, d.arquivo && `@${d.arquivo}:${d.linha || "?"}`].filter(Boolean).join(" ")
        : "";
      throw new Error(detalhe ? `${base} — ${detalhe}` : base);
    }

    if (!json || typeof json.ok !== "boolean") {
      throw new Error("Resposta inválida do servidor.");
    }

    return json;
  }

  // ============================
  // Backend
  // ============================
  async function buscarUsuariosDoBackend() {
    const json = await requisitarJson(urlListarUsuarios());
    if (!json.ok) throw new Error(json.mensagem || "Falha ao listar usuários.");
    return Array.isArray(json.dados) ? json.dados : [];
  }

  async function criarUsuarioNoBackend(payload) {
    const json = await requisitarJson(urlCriarUsuario(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao criar usuário.");
    return json.dados || null;
  }

  async function editarUsuarioNoBackend(payload) {
    const json = await requisitarJson(urlEditarUsuario(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao editar usuário.");
    return json.dados || null;
  }

  async function atualizarStatusUsuarioNoBackend(payload) {
    const json = await requisitarJson(urlAtualizarStatusUsuario(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao atualizar status.");
    return json.dados || null;
  }

  async function alternarVisibilidadeDashboardNoBackend(payload) {
    const json = await requisitarJson(urlAlternarVisibilidadeDashboard(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao alterar visibilidade.");
    return json.dados || null;
  }

  async function listarPagamentosDoBackend(userId) {
    const json = await requisitarJson(urlListarPagamentosPorUsuario(userId));
    if (!json.ok) throw new Error(json.mensagem || "Falha ao listar pagamentos.");
    return Array.isArray(json.dados) ? json.dados : [];
  }

  async function criarPagamentoNoBackend(payload) {
    const json = await requisitarJson(urlCriarPagamento(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao registrar pagamento.");
    return json.dados || null;
  }

  async function editarPagamentoNoBackend(payload) {
    const json = await requisitarJson(urlEditarPagamento(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(payload),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao editar pagamento.");
    return json.dados || null;
  }

  async function excluirPagamentoNoBackend(idPagamento) {
    const json = await requisitarJson(urlExcluirPagamento(), {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({ id_pagamento: idPagamento }),
    });
    if (!json.ok) throw new Error(json.mensagem || "Falha ao excluir pagamento.");
    return json.dados || null;
  }

  // ============================
  // Estado
  // ============================
  async function recarregarUsuariosNoEstado() {
    const nucleo = obterNucleo();
    const lista = await buscarUsuariosDoBackend();

    nucleo.estado.usuariosGestao = lista.map((u) => ({
      id_usuario: Number(u.id_usuario || 0),
      user_id: String(u.user_id || ""),
      nome_exibicao: String(u.nome_exibicao || ""),
      nivel: String(u.nivel || ""),
      valor_hora: Number(u.valor_hora || 0),
      chave: String(u.chave || ""),
      chave_pix: u.chave_pix == null ? "" : String(u.chave_pix),
      status_conta: String(u.status_conta || ""),
      ocultar_dashboard: Number(u.ocultar_dashboard || 0) ? 1 : 0,
      atualizado_em: String(u.atualizado_em || ""),
    }));
  }

  function buscarUsuarioGestao(uid) {
    const nucleo = obterNucleo();
    return (nucleo.estado.usuariosGestao || []).find((u) => u.user_id === uid) || null;
  }

  // ============================
  // Formatação
  // ============================
  function normalizarDinheiroBr(valor) {
    const t = String(valor || "").trim();
    if (!t) return 0;
    const num = parseFloat(t.replace("R$", "").replace(/\./g, "").replace(",", "."));
    return Number.isFinite(num) ? num : 0;
  }

  function formatarDinheiroBr(num) {
    const v = Number(num || 0);
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function badgeNivel(nivel) {
    const n = String(nivel || "").toLowerCase();
    if (n === "iniciante") return `<span class="badge text-bg-secondary">Iniciante</span>`;
    if (n === "intermediario") return `<span class="badge text-bg-info text-dark">Intermediário</span>`;
    if (n === "avancado") return `<span class="badge text-bg-warning text-dark">Avançado</span>`;
    return `<span class="badge text-bg-secondary">—</span>`;
  }

  function badgeStatusConta(status) {
    const s = String(status || "").toLowerCase();
    if (s === "ativa") return `<span class="badge text-bg-success">Ativa</span>`;
    if (s === "inativa") return `<span class="badge text-bg-secondary">Inativa</span>`;
    return `<span class="badge text-bg-secondary">—</span>`;
  }

  function botaoVisibilidadeDashboard(u) {
    const oculto = Number(u.ocultar_dashboard || 0) === 1;
    const uid = escapeHtmlSeguro(u.user_id);
    const icone = oculto ? "🚫" : "👁";
    const titulo = oculto ? "Oculto do Dashboard — clique para mostrar" : "Visível no Dashboard — clique para ocultar";
    const classe = oculto ? "btn-outline-secondary text-secondary" : "btn-outline-light text-light";
    return `
      <button class="btn btn-sm ${classe} px-2 py-0"
              type="button"
              title="${titulo}"
              aria-label="${titulo}"
              data-acao-usuario="alternar-visibilidade-dashboard"
              data-uid="${uid}"
              data-oculto-atual="${oculto ? 1 : 0}">
        <span style="font-size: 0.95rem; line-height: 1; opacity: ${oculto ? "0.5" : "1"};">${icone}</span>
      </button>
    `;
  }

  function classificarTipoPix(valor) {
    const v = String(valor || "").trim();
    if (!v) return null;
    if (v.includes("@")) return "email";
    const d = v.replace(/\D+/g, "");
    if (d.length === 14) return "cnpj";
    if (d.length === 10 || d.length === 11) return "celular";
    return null;
  }

  function rotuloTipoPix(tipo) {
    if (tipo === "cnpj") return "CNPJ";
    if (tipo === "celular") return "Celular";
    if (tipo === "email") return "E-mail";
    return "";
  }

  function renderCelulaChavePix(u) {
    const uid = escapeHtmlSeguro(u.user_id);
    const valor = String(u.chave_pix || "").trim();
    if (!valor) {
      return `<span class="texto-fraco small">Não cadastrada</span>`;
    }
    const tipo = classificarTipoPix(valor);
    const rotulo = rotuloTipoPix(tipo);
    const valorEsc = escapeHtmlSeguro(valor);
    const rotuloHtml = rotulo ? `<span class="texto-fraco small me-1">${rotulo}</span>` : "";
    return `
      <div class="d-inline-flex align-items-center gap-2 chave-pix-celula" data-uid="${uid}" data-revelado="0">
        ${rotuloHtml}
        <span class="texto-mono small chave-pix-valor" data-valor="${valorEsc}">••••••••</span>
        <button class="btn btn-sm btn-outline-light px-2 py-0"
                type="button"
                title="Mostrar/ocultar chave Pix"
                aria-label="Mostrar/ocultar chave Pix"
                data-acao-usuario="alternar-pix"
                data-uid="${uid}">
          <span style="font-size:0.95rem; line-height:1;">👁</span>
        </button>
      </div>
    `;
  }

  function dataHoraCurta(iso) {
    const nucleo = obterNucleo();
    return nucleo.utilidades.dataHoraCurta ? nucleo.utilidades.dataHoraCurta(iso) : String(iso || "—");
  }

  function dataIsoParaBrSeguro(valor) {
    const texto = String(valor || "").trim();
    if (!texto) return "—";

    const nucleo = obterNucleo();
    if (nucleo?.utilidades?.dataIsoParaBr) {
      return nucleo.utilidades.dataIsoParaBr(texto);
    }

    const partes = texto.split("-");
    if (partes.length !== 3) return texto;
    return `${partes[2]}/${partes[1]}/${partes[0]}`;
  }

  function dataHojeIsoSeguro() {
    const nucleo = obterNucleo();
    if (nucleo?.utilidades?.dataHojeIso) {
      return nucleo.utilidades.dataHojeIso();
    }

    const agora = new Date();
    const ano = String(agora.getFullYear());
    const mes = String(agora.getMonth() + 1).padStart(2, "0");
    const dia = String(agora.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  }

  function escapeHtmlSeguro(valor) {
    const texto = String(valor ?? "");
    const nucleo = obterNucleo();
    if (nucleo?.utilidades?.escapeHtml) {
      return nucleo.utilidades.escapeHtml(texto);
    }

    return texto
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatarPeriodoPagamento(referenciaInicio, referenciaFim) {
    const ini = String(referenciaInicio || "").trim();
    const fim = String(referenciaFim || "").trim();

    if (ini && fim) {
      return `${dataIsoParaBrSeguro(ini)} até ${dataIsoParaBrSeguro(fim)}`;
    }
    if (ini) {
      return `A partir de ${dataIsoParaBrSeguro(ini)}`;
    }
    if (fim) {
      return `Até ${dataIsoParaBrSeguro(fim)}`;
    }
    return "—";
  }

  // ============================
  // Bandeira 🚩 de auditoria
  // ============================
  function _renderizarBandeiraSync(user_id) {
    const flag = window.PainelAbaAuditoria?.obterFlagUsuarioSync?.(user_id);
    if (!flag) return "";
    if (flag.tem_flag_7dias) {
      return `<span title="App suspeito utilizado nos últimos 7 dias" style="font-size:1.05rem;line-height:1">🚩</span>`;
    }
    if ((flag.apps_detectados || []).length > 0) {
      return `<span title="Histórico de app suspeito (sem uso nos últimos 7 dias)" style="font-size:.95rem;line-height:1;opacity:.55">🏳️</span>`;
    }
    return "";
  }

  function _atualizarBandeirasUsuarios() {
    document.querySelectorAll("#tbodyUsuarios tr[data-user-id]").forEach((tr) => {
      const uid = tr.getAttribute("data-user-id");
      const alvo = tr.querySelector(".marcador-bandeira-auditoria");
      if (alvo) alvo.innerHTML = _renderizarBandeiraSync(uid);
    });
  }

  // Reagir ao evento disparado pela aba Auditoria quando o cache é atualizado
  try {
    window.addEventListener("painel:flags-auditoria-atualizadas", _atualizarBandeirasUsuarios);
  } catch (_) { /* noop */ }

  // ============================
  // Render: Aba Usuários
  // ============================
  function renderizarAbaUsuarios() {
    const nucleo = obterNucleo();
    const tbody = document.getElementById("tbodyUsuarios");
    if (!tbody) return;

    const entradaBusca = document.getElementById("entradaBuscaUsuarios");
    const busca = String(entradaBusca?.value || "").trim().toLowerCase();

    const lista = (nucleo.estado.usuariosGestao || [])
      .slice(0)
      .filter((u) => {
        if (!busca) return true;
        const hay = [u.user_id, u.nome_exibicao, u.nivel].join(" ").toLowerCase();
        return hay.includes(busca);
      })
      .sort((a, b) => String(a.user_id).localeCompare(String(b.user_id), "pt-BR", { sensitivity: "base" }));

    if (!lista.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="texto-fraco">Nenhum usuário cadastrado.</td></tr>`;
      return;
    }

    // Dispara carregamento do cache de flags de auditoria (não bloqueia a renderização).
    // Quando concluído, chama _atualizarBandeirasUsuarios() para colocar a 🚩 nas linhas
    // existentes sem precisar re-renderizar tudo.
    try {
      window.PainelAbaAuditoria?.garantirFlagsMap?.()
        .then(() => _atualizarBandeirasUsuarios())
        .catch(() => { /* silencioso */ });
    } catch (_) { /* silencioso */ }

    tbody.innerHTML = lista.map((u) => {
      const uid = escapeHtmlSeguro(u.user_id);
      const nomeLinha = u.nome_exibicao && u.nome_exibicao !== u.user_id
        ? `<div class="texto-fraco small">${escapeHtmlSeguro(u.nome_exibicao)}</div>`
        : "";

      // Marcador invisível — preenchido depois por _atualizarBandeirasUsuarios
      const bandeiraInicial = _renderizarBandeiraSync(u.user_id);

      return `
        <tr data-user-id="${uid}">
          <td>
            <div class="d-flex align-items-center gap-2">
              <span class="marcador-bandeira-auditoria">${bandeiraInicial}</span>
              <div>
                <div class="fw-semibold">${uid}</div>
                ${nomeLinha}
                <div class="texto-fraco small">Chave: <span class="texto-mono">${escapeHtmlSeguro(u.chave || "—")}</span></div>
              </div>
            </div>
          </td>

          <td class="text-center">${badgeNivel(u.nivel)}</td>

          <td class="text-center">
            <span class="fw-semibold">${escapeHtmlSeguro(formatarDinheiroBr(u.valor_hora))}</span>
          </td>

          <td class="text-center">
            ${renderCelulaChavePix(u)}
          </td>

          <td class="text-center">
            <div class="d-inline-flex align-items-center gap-2">
              ${badgeStatusConta(u.status_conta)}
              ${botaoVisibilidadeDashboard(u)}
            </div>
          </td>

          <td class="text-center">
            <span class="texto-mono">${escapeHtmlSeguro(dataHoraCurta(u.atualizado_em))}</span>
          </td>

          <td class="text-end">
            <div class="d-inline-flex gap-2">
              <button class="btn btn-sm btn-light" type="button" data-acao-usuario="abrir-gestao" data-uid="${uid}">
                Gestão
              </button>
            </div>
          </td>
        </tr>
      `;
    }).join("");

    vincularEventosUsuariosTabela();
  }

  let _usuariosTabelaDelegacaoVinculada = false;
  function vincularEventosUsuariosTabela() {
    if (_usuariosTabelaDelegacaoVinculada) return;
    _usuariosTabelaDelegacaoVinculada = true;
    const nucleo = obterNucleo();
    const tbody = document.getElementById("tbodyUsuarios");
    if (!tbody) return;
    tbody.addEventListener("click", async (ev) => {
      const btn = ev.target.closest("button[data-acao-usuario][data-uid]");
      if (!btn) return;
      const acao = btn.getAttribute("data-acao-usuario");
      const uid = btn.getAttribute("data-uid");
      if (acao === "abrir-gestao") {
        await abrirModalGestaoUsuario(uid);
        return;
      }
      if (acao === "alternar-pix") {
        const celula = btn.closest(".chave-pix-celula");
        const valorEl = celula ? celula.querySelector(".chave-pix-valor") : null;
        if (!celula || !valorEl) return;
        const revelado = celula.getAttribute("data-revelado") === "1";
        if (revelado) {
          valorEl.textContent = "••••••••";
          celula.setAttribute("data-revelado", "0");
        } else {
          valorEl.textContent = valorEl.getAttribute("data-valor") || "";
          celula.setAttribute("data-revelado", "1");
        }
        return;
      }
      if (acao === "alternar-visibilidade-dashboard") {
        const ocultoAtual = String(btn.getAttribute("data-oculto-atual") || "0") === "1";
        const novoOculto = ocultoAtual ? 0 : 1;
        btn.disabled = true;
        try {
          await alternarVisibilidadeDashboardNoBackend({ user_id: uid, ocultar_dashboard: novoOculto });
          const u = buscarUsuarioGestao(uid);
          if (u) u.ocultar_dashboard = novoOculto;
          renderizarAbaUsuarios();
          nucleo.utilidades.mostrarAlerta(
            "sucesso",
            novoOculto ? "Usuário oculto do Dashboard" : "Usuário visível no Dashboard",
            uid,
          );
        } catch (e) {
          btn.disabled = false;
          nucleo.utilidades.mostrarAlerta("erro", "Falha ao alterar visibilidade", String(e && e.message ? e.message : e));
        }
        return;
      }
      nucleo.utilidades.mostrarAlerta("info", "Ação", "Ação não implementada.");
    });
  }

  // ============================
  // Modal: adicionar usuário
  // ============================
  function prepararModalAdicionarUsuario() {
    const elId = document.getElementById("entradaNovoUsuarioId");
    const elNome = document.getElementById("entradaNovoUsuarioNome");
    const elNivel = document.getElementById("entradaNovoUsuarioNivel");
    const elValor = document.getElementById("entradaNovoUsuarioValorHora");

    if (elId) elId.value = "";
    if (elNome) elNome.value = "";
    if (elNivel) elNivel.value = "intermediario";
    if (elValor) elValor.value = "";
  }

  async function confirmarAdicionarUsuario() {
    const nucleo = obterNucleo();

    const elId = document.getElementById("entradaNovoUsuarioId");
    const elNome = document.getElementById("entradaNovoUsuarioNome");
    const elNivel = document.getElementById("entradaNovoUsuarioNivel");
    const elValor = document.getElementById("entradaNovoUsuarioValorHora");

    const uid = String(elId?.value || "").trim().toLowerCase();
    const nome = String(elNome?.value || "").trim();
    const nivel = String(elNivel?.value || "intermediario").toLowerCase();
    const valorHora = normalizarDinheiroBr(elValor?.value);

    if (!uid) {
      nucleo.utilidades.mostrarAlerta("aviso", "user_id inválido", "Informe um usuário.");
      return;
    }
    if (!nome) {
      nucleo.utilidades.mostrarAlerta("aviso", "Nome inválido", "Informe o nome de exibição.");
      return;
    }
    if (!["iniciante", "intermediario", "avancado"].includes(nivel)) {
      nucleo.utilidades.mostrarAlerta("aviso", "Nível inválido", "Escolha um nível válido.");
      return;
    }
    if (!Number.isFinite(valorHora) || valorHora < 0) {
      nucleo.utilidades.mostrarAlerta("aviso", "Valor por hora inválido", "Informe um valor maior ou igual a zero.");
      return;
    }

    try {
      await criarUsuarioNoBackend({
        user_id: uid,
        nome_exibicao: nome,
        nivel,
        valor_hora: valorHora,
      });

      await recarregarUsuariosNoEstado();
      renderizarAbaUsuarios();

      const modalEl = document.getElementById("modalAdicionarUsuario");
      if (modalEl && window.bootstrap) window.bootstrap.Modal.getOrCreateInstance(modalEl).hide();

      nucleo.utilidades.mostrarAlerta("sucesso", "Usuário criado", `Usuário: ${uid}`);
    } catch (e) {
      nucleo.utilidades.mostrarAlerta("erro", "Erro ao criar usuário", String(e && e.message ? e.message : e));
    }
  }

  // ============================
  // Modal: gestão (REAL)
  // ============================
  function alternarModoEdicao(ativar) {
    const blocoVisual = document.getElementById("blocoGestaoVisual");
    const blocoEdicao = document.getElementById("blocoGestaoEdicao");
    if (blocoVisual) blocoVisual.classList.toggle("d-none", !!ativar);
    if (blocoEdicao) blocoEdicao.classList.toggle("d-none", !ativar);
  }

  function preencherCamposEdicao(u) {
    const elNome = document.getElementById("entradaEditarNome");
    const elNivel = document.getElementById("entradaEditarNivel");
    const elValor = document.getElementById("entradaEditarValorHora");

    if (elNome) elNome.value = String(u.nome_exibicao || "");
    if (elNivel) elNivel.value = String(u.nivel || "intermediario");
    if (elValor) elValor.value = String((u.valor_hora || 0)).replace(".", ",");
  }

  function prepararCamposPagamentoPadrao() {
    const elData = document.getElementById("entradaPagamentoData");
    const elValor = document.getElementById("entradaPagamentoValor");
    const elObs = document.getElementById("entradaPagamentoObs");

    if (elData) elData.value = dataHojeIsoSeguro();
    if (elValor) elValor.value = "";
    if (elObs) elObs.value = "";
  }

  async function carregarPagamentosNoModal(uid) {
    const nucleo = obterNucleo();
    const tbody = document.getElementById("tbodyGestaoPagamentos");
    const elTotal = document.getElementById("textoGestaoTotalPago");

    try {
      if (tbody) tbody.innerHTML = `<tr><td colspan="4" class="texto-fraco">Carregando…</td></tr>`;

      const lista = await listarPagamentosDoBackend(uid);
      const ordenada = lista.slice(0).sort((a, b) => String(b.data_pagamento || "").localeCompare(String(a.data_pagamento || "")));
      _pagamentosCache = ordenada;

      const total = ordenada.reduce((acc, p) => acc + Number(p.valor || 0), 0);
      if (elTotal) elTotal.textContent = formatarDinheiroBr(total);

      if (!tbody) return;

      if (!ordenada.length) {
        tbody.innerHTML = `<tr><td colspan="4" class="texto-fraco">Nenhum pagamento registrado.</td></tr>`;
        return;
      }

      tbody.innerHTML = ordenada.map((p, idx) => {
        const dataPagamento = dataIsoParaBrSeguro(String(p.data_pagamento || ""));
        const observacao = String(p.observacao || "").trim() || "—";
        const idPag = Number(p.id_pagamento || 0);
        const editavel = idx < 2; // Apenas os 2 mais recentes

        const botoes = editavel
          ? `<button class="btn btn-sm btn-outline-light me-1" onclick="window.__editarPagamento(${idPag})" title="Editar">✏️</button>
             <button class="btn btn-sm btn-outline-danger" onclick="window.__excluirPagamento(${idPag})" title="Excluir">🗑️</button>`
          : `<span class="texto-fraco small">🔒</span>`;

        return `
          <tr>
            <td>${escapeHtmlSeguro(dataPagamento)}</td>
            <td class="text-end fw-semibold">${escapeHtmlSeguro(formatarDinheiroBr(p.valor))}</td>
            <td>${escapeHtmlSeguro(observacao)}</td>
            <td class="text-end" style="white-space:nowrap;">${botoes}</td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="4" class="texto-fraco">Falha ao carregar.</td></tr>`;
      nucleo.utilidades.mostrarAlerta("erro", "Falha ao listar pagamentos", String(e && e.message ? e.message : e));
    }
  }

  // Limpa "#7 - Título (status)" → "Título"
  function limparCanal(texto) {
    if (!texto) return "";
    return String(texto)
      .replace(/^#\d+\s*-\s*/, "")
      .replace(/\s*\([^)]*\)\s*$/, "")
      .trim();
  }

  function formatarHm(segundos) {
    const s = Math.max(0, Math.round(Number(segundos) || 0));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${String(m).padStart(2, "0")}m`;
  }

  let _resumoPeriodoAtivo = "tudo"; // 'tudo' | '30dias'
  let _resumoUidAtual = null;
  let _resumoValorHoraAtual = 0;

  async function carregarResumoHorasPagamento(uid, valorHora) {
    _resumoUidAtual = uid;
    _resumoValorHoraAtual = valorHora;

    const elTrab = document.getElementById("gestaoResumoTrabalhado");
    const elDecl = document.getElementById("gestaoResumoDeclarado");
    const elNaoDecl = document.getElementById("gestaoResumoNaoDeclarado");
    const elOcioso = document.getElementById("gestaoResumoOcioso");
    const elAPagar = document.getElementById("gestaoResumoAPagar");
    const elPago = document.getElementById("gestaoResumoPago");

    try {
      const rSub = await requisitarJson(`./commands/atividades_subtarefas/listar.php?user_id=${encodeURIComponent(uid)}&resumo_periodo=${encodeURIComponent(_resumoPeriodoAtivo)}`);
      const subs = rSub.dados || [];
      const first = subs.length > 0 ? subs[0] : {};

      // Dados do cronômetro (cronometro_relatorios) + declarações + pagamentos
      const declarado    = Number(first.segundos_declarados_total_geral || 0);
      const naoDeclarado = Number(first.segundos_nao_declarado_total || 0);
      const trabalhado   = declarado + naoDeclarado;
      const ocioso       = Number(first.segundos_ocioso_total || 0);
      const totalPago    = Number(first.total_pago || 0);
      const aPagar       = Math.max(0, (declarado * (valorHora / 3600)) - totalPago);

      if (elTrab) elTrab.textContent = formatarHm(trabalhado);
      if (elDecl) elDecl.textContent = formatarHm(declarado);
      if (elNaoDecl) elNaoDecl.textContent = formatarHm(naoDeclarado);
      if (elOcioso) elOcioso.textContent = formatarHm(ocioso);
      if (elAPagar) elAPagar.textContent = formatarDinheiroBr(aPagar);
      if (elPago) elPago.textContent = formatarDinheiroBr(totalPago);
    } catch (_) {
      if (elTrab) elTrab.textContent = "—";
      if (elDecl) elDecl.textContent = "—";
      if (elNaoDecl) elNaoDecl.textContent = "—";
      if (elOcioso) elOcioso.textContent = "—";
      if (elAPagar) elAPagar.textContent = "—";
      if (elPago) elPago.textContent = "—";
    }
  }

  async function abrirModalGestaoUsuario(uid) {
    const u = buscarUsuarioGestao(uid);
    if (!u) return;

    usuarioGestaoAbertoId = uid;

    const elSub = document.getElementById("textoGestaoSubtitulo");
    const elUsuario = document.getElementById("textoGestaoUsuario");
    const elChave = document.getElementById("textoGestaoChave");
    const elStatus = document.getElementById("textoGestaoStatusConta");
    const elSwitch = document.getElementById("switchGestaoAtiva");

    const elNome = document.getElementById("textoGestaoNome");
    const elNivel = document.getElementById("textoGestaoNivel");
    const elValorHora = document.getElementById("textoGestaoValorHora");

    if (elSub) elSub.textContent = `Usuário: ${u.user_id}`;
    if (elUsuario) elUsuario.textContent = u.user_id;
    if (elChave) elChave.textContent = u.chave || "—";

    const ativo = String(u.status_conta || "").toLowerCase() === "ativa";
    if (elStatus) elStatus.textContent = ativo ? "Ativa" : "Inativa";
    if (elSwitch) elSwitch.checked = !!ativo;

    if (elNome) elNome.textContent = u.nome_exibicao || "—";
    if (elNivel) {
      elNivel.textContent =
        String(u.nivel).toLowerCase() === "iniciante" ? "Iniciante"
          : String(u.nivel).toLowerCase() === "avancado" ? "Avançado"
            : "Intermediário";
    }

    if (elValorHora) elValorHora.textContent = formatarDinheiroBr(u.valor_hora);

    prepararCamposPagamentoPadrao();

    alternarModoEdicao(false);
    preencherCamposEdicao(u);

    await Promise.all([
      carregarPagamentosNoModal(uid),
      carregarResumoHorasPagamento(uid, u.valor_hora),
      carregarTarefasDoUsuario(uid),
      carregarCanaisDoUsuario(uid),
    ]);

    // Alertas de auditoria (opcional — silencioso se o módulo não estiver disponível)
    try {
      await window.PainelAbaAuditoria?.renderizarAlertasNaGestao?.(uid);
    } catch (_) { /* silencioso */ }

    const abaGestaoEl = document.getElementById("abaGestaoUsuario");
    if (abaGestaoEl) abaGestaoEl.setAttribute("data-user-id", uid);

    if (typeof window.PainelNucleo_trocarAba === "function") {
      window.PainelNucleo_trocarAba("abaGestaoUsuario");
    }
  }

  let _tarefasGestaoCache = [];
  // Ordenação manual: pagas sempre embaixo, não pagas em cima.
  // Critério secundário escolhido pelo admin via #selectOrdemTarefasGestao.
  let _ordemTarefasGestao = "data"; // "data" | "canal" | "tarefa"

  function _ordenarTarefasGestao(lista) {
    const ordem = _ordemTarefasGestao;
    const copia = lista.slice();
    copia.sort((a, b) => {
      // 1) Não pagas (bloqueada=false) sempre antes das pagas.
      const pagaA = a.bloqueada_pagamento ? 1 : 0;
      const pagaB = b.bloqueada_pagamento ? 1 : 0;
      if (pagaA !== pagaB) return pagaA - pagaB;

      // 2) Critério secundário escolhido pelo admin.
      if (ordem === "canal") {
        const ca = (limparCanal(a.canal_entrega) || "").toLowerCase();
        const cb = (limparCanal(b.canal_entrega) || "").toLowerCase();
        const cmp = ca.localeCompare(cb, "pt-BR");
        if (cmp !== 0) return cmp;
      } else if (ordem === "tarefa") {
        const ta = String(a.titulo || "").toLowerCase();
        const tb = String(b.titulo || "").toLowerCase();
        const cmp = ta.localeCompare(tb, "pt-BR");
        if (cmp !== 0) return cmp;
      }

      // 3) Tiebreaker (e ordem default "data"): mais recente primeiro,
      //    depois id_subtarefa decrescente.
      const da = String(a.referencia_data || "");
      const db = String(b.referencia_data || "");
      if (da !== db) return db.localeCompare(da);
      return (b.id_subtarefa || 0) - (a.id_subtarefa || 0);
    });
    return copia;
  }

  function _renderTarefasGestao() {
    const tbody = document.getElementById("tbodyGestaoTarefas");
    if (!tbody) return;
    if (!_tarefasGestaoCache.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="texto-fraco">Nenhuma tarefa declarada.</td></tr>`;
      return;
    }
    const ordenada = _ordenarTarefasGestao(_tarefasGestaoCache);
    tbody.innerHTML = ordenada.map(t => {
      const seg = t.segundos_gastos || 0;
      const bloqueada = t.bloqueada_pagamento;
      const btnEditar = bloqueada
        ? `<button class="btn btn-sm btn-outline-secondary" disabled title="Bloqueada por pagamento">Editar</button>`
        : `<button class="btn btn-sm btn-outline-light botao-mini" onclick="window.__editarTarefaGestao(${t.id_subtarefa})">Editar</button>`;
      const obs = String(t.observacao || "").trim();
      const obsHtml = obs
        ? `<span title="${escapeHtmlSeguro(obs)}" style="display:inline-block;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;vertical-align:bottom;">${escapeHtmlSeguro(obs)}</span>`
        : '<span class="texto-fraco">—</span>';
      // Badge [CANCELADO] quando o canal foi cancelado — visual apenas, sub
      // continua editável e segue contando nos cálculos.
      const canalCancelado = String(t.status_atividade || "").toLowerCase() === "cancelada";
      const canalBadge = canalCancelado
        ? ' <span class="badge bg-secondary" title="Canal cancelado pelo admin — subtarefa preservada">[CANCELADO]</span>'
        : '';
      const linhaStyle = canalCancelado ? ' style="opacity:0.55;"' : '';
      return `<tr${linhaStyle}>
        <td>${escapeHtmlSeguro(dataIsoParaBrSeguro(String(t.referencia_data || "")))}</td>
        <td>${escapeHtmlSeguro(limparCanal(t.canal_entrega) || "—")}${canalBadge}</td>
        <td>${escapeHtmlSeguro(String(t.titulo || "—"))}</td>
        <td>${formatarHm(seg)}</td>
        <td class="text-center">${t.concluida
          ? '<span class="badge text-bg-success">Concluída</span>'
          : '<span class="badge text-bg-secondary">Aberta</span>'}</td>
        <td>${obsHtml}</td>
        <td class="text-end">${btnEditar}</td>
      </tr>`;
    }).join("");
  }

  // Wiring do select de ordenação (uma vez, idempotente).
  function _wirarSelectOrdemTarefasGestao() {
    const sel = document.getElementById("selectOrdemTarefasGestao");
    if (!sel || sel.dataset.wired === "1") return;
    sel.dataset.wired = "1";
    sel.value = _ordemTarefasGestao;
    sel.addEventListener("change", () => {
      _ordemTarefasGestao = String(sel.value || "data");
      _renderTarefasGestao();
    });
  }

  // ─── Canais vinculados ao usuário (Gestão do Usuário) ────────────────
  //
  // Permite o admin vincular/desvincular vários canais ao usuário sem ter
  // que abrir cada canal individualmente. Espelho do que `aba-atividades.js`
  // faz no eixo oposto (lista usuários de UM canal); aqui listamos canais
  // de UM usuário. Backend: `commands/usuarios/salvar_canais.php`.
  let _canaisGestaoCache = []; // [{ id_atividade, titulo, status, vinculado:boolean }]

  async function carregarCanaisDoUsuario(uid) {
    const lista = document.getElementById("listaCanaisGestao");
    const total = document.getElementById("textoGestaoTotalCanais");

    if (lista) lista.innerHTML = `<div class="col-12"><div class="texto-fraco">Carregando canais…</div></div>`;
    if (total) total.textContent = "—";

    try {
      const json = await requisitarJson("./commands/atividades/listar.php");
      const atividades = Array.isArray(json.dados) ? json.dados : [];

      _canaisGestaoCache = atividades
        .filter(a => String(a.status || "").toLowerCase() !== "cancelada")
        .map((a) => ({
          id_atividade: Number(a.id_atividade || 0),
          titulo: String(a.titulo || ""),
          status: String(a.status || ""),
          vinculado: Array.isArray(a.usuarios) && a.usuarios.some(
            (uu) => String(uu.user_id || "") === String(uid)
          ),
        }));

      _renderCanaisGestao();
    } catch (e) {
      if (lista) lista.innerHTML = `<div class="col-12"><div class="text-warning small">Falha ao carregar canais.</div></div>`;
    }
  }

  function _renderCanaisGestao() {
    const lista = document.getElementById("listaCanaisGestao");
    const total = document.getElementById("textoGestaoTotalCanais");
    if (!lista) return;

    if (!_canaisGestaoCache.length) {
      lista.innerHTML = `<div class="col-12"><div class="texto-fraco">Nenhum canal cadastrado.</div></div>`;
      if (total) total.textContent = "0 / 0";
      return;
    }

    const marcados = _canaisGestaoCache.filter((c) => c.vinculado).length;
    if (total) total.textContent = `${marcados} / ${_canaisGestaoCache.length}`;

    lista.innerHTML = _canaisGestaoCache.map((c) => `
      <div class="col-12 col-md-6 col-lg-4">
        <label class="cartao-grafite p-2 d-flex align-items-center gap-2" style="cursor:pointer;">
          <input type="checkbox" class="form-check-input m-0" data-canal-id="${c.id_atividade}" ${c.vinculado ? "checked" : ""}>
          <div class="flex-grow-1">
            <div class="fw-semibold">${escapeHtmlSeguro(c.titulo)}</div>
            <div class="texto-fraco small">#${c.id_atividade} · ${escapeHtmlSeguro(c.status)}</div>
          </div>
        </label>
      </div>
    `).join("");

    lista.querySelectorAll('input[type="checkbox"][data-canal-id]').forEach((cb) => {
      cb.addEventListener("change", () => {
        const id = Number(cb.getAttribute("data-canal-id") || 0);
        const item = _canaisGestaoCache.find((c) => c.id_atividade === id);
        if (item) item.vinculado = cb.checked;
        const novaContagem = _canaisGestaoCache.filter((c) => c.vinculado).length;
        if (total) total.textContent = `${novaContagem} / ${_canaisGestaoCache.length}`;
      });
    });
  }

  async function salvarCanaisDoUsuario() {
    const nucleo = obterNucleo();
    if (!usuarioGestaoAbertoId) return;

    const ids = _canaisGestaoCache.filter((c) => c.vinculado).map((c) => c.id_atividade);
    const btn = document.getElementById("btnSalvarCanaisGestao");
    if (btn) { btn.disabled = true; btn.textContent = "Salvando…"; }

    try {
      const json = await requisitarJson("./commands/usuarios/salvar_canais.php", {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ user_id: usuarioGestaoAbertoId, ids_atividades: ids }),
      });
      if (json && json.ok === false) throw new Error(json.mensagem || "Falha ao salvar canais.");
      nucleo.utilidades?.mostrarAlerta?.("ok", "Canais atualizados", "Vínculos do usuário foram salvos.");
      // Recarrega a lista para refletir o estado do servidor (canais que
      // tenham sido apagados externamente, etc.)
      await carregarCanaisDoUsuario(usuarioGestaoAbertoId);
      // Reflete possível mudança em outras abas que consumem `atividades_usuarios`.
      try { window.recarregarAbaAtividades && window.recarregarAbaAtividades(); } catch (_) {}
    } catch (e) {
      nucleo.utilidades?.mostrarAlerta?.("erro", "Erro", e?.message || "Não foi possível salvar os canais.");
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Salvar canais"; }
    }
  }

  // Wiring do botão "Salvar canais" — idempotente.
  (function _wirarSalvarCanais() {
    document.addEventListener("DOMContentLoaded", () => {
      const btn = document.getElementById("btnSalvarCanaisGestao");
      if (!btn || btn.dataset.wired === "1") return;
      btn.dataset.wired = "1";
      btn.addEventListener("click", salvarCanaisDoUsuario);
    });
    // Fallback caso o script rode após o DOMContentLoaded.
    if (document.readyState !== "loading") {
      const btn = document.getElementById("btnSalvarCanaisGestao");
      if (btn && btn.dataset.wired !== "1") {
        btn.dataset.wired = "1";
        btn.addEventListener("click", salvarCanaisDoUsuario);
      }
    }
  })();

  // Paginação atual da Gestão (50 tarefas por página). Refeita a cada
  // chamada de `carregarTarefasDoUsuario` ou ao clicar em um número.
  let _paginaTarefasGestao = 1;
  const _perPageTarefasGestao = 50;

  async function carregarTarefasDoUsuario(uid, pagina) {
    const tbody = document.getElementById("tbodyGestaoTarefas");
    const elTotal = document.getElementById("textoGestaoTotalTarefas");
    const elNav = document.getElementById("paginacaoGestaoTarefas");
    _wirarSelectOrdemTarefasGestao();

    if (typeof pagina === "number" && pagina >= 1) {
      _paginaTarefasGestao = pagina;
    } else if (pagina === undefined) {
      _paginaTarefasGestao = 1;
    }

    try {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="texto-fraco">Carregando…</td></tr>`;

      const url = `./commands/atividades_subtarefas/listar.php`
        + `?user_id=${encodeURIComponent(uid)}`
        + `&page=${_paginaTarefasGestao}`
        + `&per_page=${_perPageTarefasGestao}`;
      const json = await requisitarJson(url);
      const lista = Array.isArray(json.dados) ? json.dados : [];
      _tarefasGestaoCache = lista;

      const pag = json.paginacao || {};
      const total = Number(pag.total ?? lista.length);
      const totalPages = Number(pag.total_pages ?? 1);
      const pageAtual = Number(pag.page ?? _paginaTarefasGestao);
      _paginaTarefasGestao = pageAtual;

      if (elTotal) elTotal.textContent = `${total} tarefa(s)`;

      _renderTarefasGestao();
      _renderPaginacaoGestaoTarefas(elNav, uid, pageAtual, totalPages);
    } catch (e) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="texto-fraco">Falha ao carregar tarefas.</td></tr>`;
      if (elNav) elNav.innerHTML = "";
    }
  }

  function _renderPaginacaoGestaoTarefas(container, uid, pageAtual, totalPages) {
    if (!container) return;
    if (!totalPages || totalPages <= 1) {
      container.innerHTML = "";
      return;
    }
    container.innerHTML = _renderHtmlPaginacao(pageAtual, totalPages, "gestao");
    container.querySelectorAll("button[data-pag]").forEach((b) => {
      b.addEventListener("click", () => {
        const p = Number(b.getAttribute("data-pag") || 1);
        if (p >= 1 && p !== pageAtual) carregarTarefasDoUsuario(uid, p);
      });
    });
  }

  // Gera HTML de paginação compacta (até 7 botões: <, 1, ..., n-1, n, n+1, ..., last, >).
  // Reutilizada também pela aba Gerenciar Tarefas via janela global.
  function _renderHtmlPaginacao(pageAtual, totalPages, prefixo) {
    const segura = (n) => Math.max(1, Math.min(totalPages, n));
    const itens = new Set([1, totalPages, pageAtual, segura(pageAtual - 1), segura(pageAtual + 1)]);
    const sorted = Array.from(itens).sort((a, b) => a - b);
    const partes = [];
    partes.push(`<ul class="pagination pagination-sm mb-0" role="navigation">`);
    partes.push(`<li class="page-item ${pageAtual <= 1 ? "disabled" : ""}">
      <button class="page-link bg-transparent text-light border-secondary" data-pag="${segura(pageAtual - 1)}" ${pageAtual <= 1 ? "disabled" : ""} aria-label="Anterior">«</button>
    </li>`);
    let anterior = 0;
    for (const n of sorted) {
      if (anterior && n - anterior > 1) {
        partes.push(`<li class="page-item disabled"><span class="page-link bg-transparent text-light border-secondary">…</span></li>`);
      }
      const ativa = n === pageAtual;
      partes.push(`<li class="page-item ${ativa ? "active" : ""}">
        <button class="page-link ${ativa ? "" : "bg-transparent text-light"} border-secondary" data-pag="${n}" ${ativa ? "aria-current=\"page\"" : ""}>${n}</button>
      </li>`);
      anterior = n;
    }
    partes.push(`<li class="page-item ${pageAtual >= totalPages ? "disabled" : ""}">
      <button class="page-link bg-transparent text-light border-secondary" data-pag="${segura(pageAtual + 1)}" ${pageAtual >= totalPages ? "disabled" : ""} aria-label="Próxima">»</button>
    </li>`);
    partes.push(`</ul>`);
    return partes.join("");
  }

  // Expõe o helper de HTML pra outras abas (aba-gerenciar-tarefas.js usa).
  window.__paginacaoTarefasHtml = _renderHtmlPaginacao;

  window.__editarTarefaGestao = function (idSubtarefa) {
    const tarefa = _tarefasGestaoCache.find(t => t.id_subtarefa === idSubtarefa);
    if (!tarefa || typeof window.gtAbrirEdicao !== "function") return;
    window.gtAbrirEdicao(idSubtarefa, tarefa);
  };

  window.__onTarefaEditada = function () {
    if (usuarioGestaoAbertoId) {
      carregarTarefasDoUsuario(usuarioGestaoAbertoId);
      const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
      if (u) carregarResumoHorasPagamento(u.user_id, u.valor_hora);
    }
  };

  async function salvarEdicaoUsuario() {
    const nucleo = obterNucleo();
    if (!usuarioGestaoAbertoId) return;

    const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
    if (!u) return;

    const elNome = document.getElementById("entradaEditarNome");
    const elNivel = document.getElementById("entradaEditarNivel");
    const elValor = document.getElementById("entradaEditarValorHora");

    const nome = String(elNome?.value || "").trim();
    const nivel = String(elNivel?.value || "").toLowerCase();
    const valorHora = normalizarDinheiroBr(elValor?.value);

    if (!nome) {
      nucleo.utilidades.mostrarAlerta("aviso", "Nome inválido", "Informe o nome de exibição.");
      return;
    }
    if (!["iniciante", "intermediario", "avancado"].includes(nivel)) {
      nucleo.utilidades.mostrarAlerta("aviso", "Nível inválido", "Escolha um nível válido.");
      return;
    }
    if (!Number.isFinite(valorHora) || valorHora < 0) {
      nucleo.utilidades.mostrarAlerta("aviso", "Valor inválido", "Informe um valor maior ou igual a zero.");
      return;
    }

    try {
      await editarUsuarioNoBackend({
        user_id: u.user_id,
        nome_exibicao: nome,
        nivel,
        valor_hora: valorHora,
      });

      await recarregarUsuariosNoEstado();
      renderizarAbaUsuarios();
      await abrirModalGestaoUsuario(u.user_id);

      nucleo.utilidades.mostrarAlerta("sucesso", "Usuário atualizado", `Usuário: ${u.user_id}`);
    } catch (e) {
      nucleo.utilidades.mostrarAlerta("erro", "Erro ao editar usuário", String(e && e.message ? e.message : e));
    }
  }

  async function alternarStatusContaNoModal(novoAtivo) {
    const nucleo = obterNucleo();
    if (!usuarioGestaoAbertoId) return;

    const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
    if (!u) return;

    try {
      await atualizarStatusUsuarioNoBackend({
        user_id: u.user_id,
        status_conta: novoAtivo ? "ativa" : "inativa",
      });

      await recarregarUsuariosNoEstado();
      renderizarAbaUsuarios();
      await abrirModalGestaoUsuario(u.user_id);

      nucleo.utilidades.mostrarAlerta("sucesso", "Status atualizado", `${u.user_id}: ${novoAtivo ? "ativa" : "inativa"}`);
    } catch (e) {
      nucleo.utilidades.mostrarAlerta("erro", "Erro ao atualizar status", String(e && e.message ? e.message : e));
    }
  }

  // ============================
  // Editar / Excluir pagamento
  // ============================
  let _pagamentosCache = [];

  async function editarPagamentoModal(idPagamento) {
    const nucleo = obterNucleo();
    const pag = _pagamentosCache.find(p => Number(p.id_pagamento) === idPagamento);
    if (!pag) {
      nucleo.utilidades.mostrarAlerta("erro", "Erro", "Pagamento não encontrado.");
      return;
    }

    const dataPag = String(pag.data_pagamento || "");
    const valor = formatarDinheiroBr(pag.valor);
    const obs = String(pag.observacao || "");

    const html = `
      <div class="mb-2"><label class="form-label small texto-fraco mb-1">Data pagamento</label>
        <input type="date" class="form-control form-control-sm bg-dark text-light border-secondary" id="_editPagData" value="${escapeHtmlSeguro(dataPag)}"></div>
      <div class="mb-2"><label class="form-label small texto-fraco mb-1">Valor (R$)</label>
        <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary" id="_editPagValor" value="${escapeHtmlSeguro(valor)}"></div>
      <div class="mb-2"><label class="form-label small texto-fraco mb-1">Observação</label>
        <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary" id="_editPagObs" value="${escapeHtmlSeguro(obs)}"></div>
    `;

    // Criar modal dinamicamente
    let modal = document.getElementById("modalEditarPagamento");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "modalEditarPagamento";
      modal.className = "modal fade";
      modal.tabIndex = -1;
      modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered">
          <div class="modal-content bg-dark text-light border-secondary">
            <div class="modal-header border-secondary">
              <h6 class="modal-title">Editar Pagamento #${idPagamento}</h6>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="_editPagBody">${html}</div>
            <div class="modal-footer border-secondary">
              <button type="button" class="btn btn-sm btn-secondary" data-bs-dismiss="modal">Cancelar</button>
              <button type="button" class="btn btn-sm btn-primary" id="_editPagSalvar">Salvar</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    } else {
      modal.querySelector(".modal-title").textContent = `Editar Pagamento #${idPagamento}`;
      modal.querySelector("#_editPagBody").innerHTML = html;
    }

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    const btnSalvar = modal.querySelector("#_editPagSalvar");
    const novoBtn = btnSalvar.cloneNode(true);
    btnSalvar.parentNode.replaceChild(novoBtn, btnSalvar);

    novoBtn.addEventListener("click", async () => {
      const novaData = document.getElementById("_editPagData")?.value || "";
      const novoValor = normalizarDinheiroBr(document.getElementById("_editPagValor")?.value);
      const novaObs = document.getElementById("_editPagObs")?.value || "";

      if (!novaData) {
        nucleo.utilidades.mostrarAlerta("aviso", "Data inválida", "Informe a data do pagamento.");
        return;
      }
      if (novoValor <= 0) {
        nucleo.utilidades.mostrarAlerta("aviso", "Valor inválido", "Informe um valor maior que zero.");
        return;
      }

      try {
        // O modal atual não expõe edição de período. Antes o payload mandava
        // `referencia_inicio: null`, `referencia_fim: null` e
        // `travado_ate_data: novaData`; o backend interpretava como mudança
        // de período e reprocessava travas, destravando/travando tarefas
        // sem o admin pedir. Agora só enviamos o que a UI realmente edita —
        // a cobertura salva fica intacta.
        await editarPagamentoNoBackend({
          id_pagamento: idPagamento,
          data_pagamento: novaData,
          valor: novoValor,
          observacao: novaObs,
        });

        bsModal.hide();

        if (usuarioGestaoAbertoId) {
          const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
          await Promise.all([
            carregarPagamentosNoModal(usuarioGestaoAbertoId),
            u ? carregarResumoHorasPagamento(u.user_id, u.valor_hora) : Promise.resolve(),
            carregarTarefasDoUsuario(usuarioGestaoAbertoId),
          ]);
        }

        nucleo.utilidades.mostrarAlerta("sucesso", "Pagamento atualizado", `Pagamento #${idPagamento} salvo.`);
      } catch (e) {
        nucleo.utilidades.mostrarAlerta("erro", "Erro ao editar", String(e && e.message ? e.message : e));
      }
    });
  }

  async function excluirPagamentoConfirmar(idPagamento) {
    const nucleo = obterNucleo();

    if (!confirm(`Excluir pagamento #${idPagamento}?\n\nAs subtarefas travadas por este pagamento serão destravadas.`)) {
      return;
    }

    try {
      const resultado = await excluirPagamentoNoBackend(idPagamento);
      const destravadas = resultado?.tarefas_destravadas || 0;

      if (usuarioGestaoAbertoId) {
        const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
        await Promise.all([
          carregarPagamentosNoModal(usuarioGestaoAbertoId),
          u ? carregarResumoHorasPagamento(u.user_id, u.valor_hora) : Promise.resolve(),
          carregarTarefasDoUsuario(usuarioGestaoAbertoId),
        ]);
      }

      nucleo.utilidades.mostrarAlerta("sucesso", "Pagamento excluído", `Pagamento removido. ${destravadas} tarefa(s) destravada(s).`);
    } catch (e) {
      nucleo.utilidades.mostrarAlerta("erro", "Erro ao excluir", String(e && e.message ? e.message : e));
    }
  }

  // Expor para onclick inline
  window.__editarPagamento = editarPagamentoModal;
  window.__excluirPagamento = excluirPagamentoConfirmar;

  async function registrarPagamentoReal() {
    const nucleo = obterNucleo();
    if (!usuarioGestaoAbertoId) return;

    const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
    if (!u) return;

    const elData = document.getElementById("entradaPagamentoData");
    const elValor = document.getElementById("entradaPagamentoValor");
    const elObs = document.getElementById("entradaPagamentoObs");

    const data = String(elData?.value || "").trim();
    const valor = normalizarDinheiroBr(elValor?.value);
    const obs = String(elObs?.value || "").trim();

    if (!data) {
      nucleo.utilidades.mostrarAlerta("aviso", "Data inválida", "Informe a data do pagamento.");
      return;
    }
    if (valor <= 0) {
      nucleo.utilidades.mostrarAlerta("aviso", "Valor inválido", "Informe um valor maior que zero.");
      return;
    }

    try {
      await criarPagamentoNoBackend({
        user_id: u.user_id,
        data_pagamento: data,
        referencia_inicio: null,
        referencia_fim: null,
        travado_ate_data: data,
        valor,
        observacao: obs,
      });

      prepararCamposPagamentoPadrao();
      await Promise.all([
        carregarPagamentosNoModal(u.user_id),
        carregarResumoHorasPagamento(u.user_id, u.valor_hora),
        carregarTarefasDoUsuario(u.user_id),
      ]);

      nucleo.utilidades.mostrarAlerta("sucesso", "Pagamento registrado", `${u.user_id}: ${formatarDinheiroBr(valor)}`);
    } catch (e) {
      nucleo.utilidades.mostrarAlerta("erro", "Erro ao registrar pagamento", String(e && e.message ? e.message : e));
    }
  }

  // ============================
  // Init
  // ============================
  async function iniciarUsuarios() {
    const nucleo = obterNucleo();
    nucleo.estado.usuariosGestao = [];

    try {
      await recarregarUsuariosNoEstado();
    } catch (e) {
      nucleo.utilidades.mostrarAlerta("erro", "Falha ao carregar usuários", String(e && e.message ? e.message : e));
    }
  }

  function vincularEventosUsuarios() {
    const entradaBuscaUsuarios = document.getElementById("entradaBuscaUsuarios");
    let _debounceTimerUsuarios = null;
    if (entradaBuscaUsuarios) entradaBuscaUsuarios.addEventListener("input", () => {
      clearTimeout(_debounceTimerUsuarios);
      _debounceTimerUsuarios = setTimeout(renderizarAbaUsuarios, 300);
    });

    const modalAddUsuario = document.getElementById("modalAdicionarUsuario");
    if (modalAddUsuario) modalAddUsuario.addEventListener("show.bs.modal", prepararModalAdicionarUsuario);

    const botaoSalvarUsuario = document.getElementById("botaoConfirmarAdicionarUsuario");
    if (botaoSalvarUsuario) botaoSalvarUsuario.addEventListener("click", () => confirmarAdicionarUsuario());

    const botaoEditar = document.getElementById("botaoEditarDadosUsuario");
    if (botaoEditar) botaoEditar.addEventListener("click", () => alternarModoEdicao(true));

    const botaoCancelar = document.getElementById("botaoCancelarEdicaoUsuario");
    if (botaoCancelar) botaoCancelar.addEventListener("click", () => alternarModoEdicao(false));

    const botaoSalvarEdicao = document.getElementById("botaoSalvarEdicaoUsuario");
    if (botaoSalvarEdicao) botaoSalvarEdicao.addEventListener("click", () => salvarEdicaoUsuario());

    const elSwitch = document.getElementById("switchGestaoAtiva");
    if (elSwitch) {
      elSwitch.addEventListener("change", () => {
        alternarStatusContaNoModal(!!elSwitch.checked);
      });
    }

    const botaoRegistrarPagamento = document.getElementById("botaoRegistrarPagamento");
    if (botaoRegistrarPagamento) botaoRegistrarPagamento.addEventListener("click", () => registrarPagamentoReal());

    const botaoVoltar = document.getElementById("botaoVoltarUsuarios");
    if (botaoVoltar) {
      botaoVoltar.addEventListener("click", () => {
        usuarioGestaoAbertoId = "";
        alternarModoEdicao(false);
        if (typeof window.PainelNucleo_trocarAba === "function") {
          window.PainelNucleo_trocarAba("abaUsuarios");
        }
      });
    }

    // Filtros de período do "Resumo para pagamento"
    document.querySelectorAll("[data-resumo-periodo]").forEach(btn => {
      btn.addEventListener("click", () => {
        const periodo = btn.getAttribute("data-resumo-periodo");
        if (periodo === _resumoPeriodoAtivo) return;
        _resumoPeriodoAtivo = periodo;
        // Atualiza estado visual dos botões
        document.querySelectorAll("[data-resumo-periodo]").forEach(b => {
          const ativo = b.getAttribute("data-resumo-periodo") === periodo;
          b.classList.toggle("btn-light", ativo);
          b.classList.toggle("active", ativo);
          b.classList.toggle("btn-outline-light", !ativo);
        });
        // Recarrega o resumo com o novo filtro
        if (_resumoUidAtual) {
          carregarResumoHorasPagamento(_resumoUidAtual, _resumoValorHoraAtual);
        }
      });
    });
  }

  // API do módulo
  window.PainelAbaUsuarios = {
    nomeModulo,
    iniciarUsuarios,
    vincularEventosUsuarios,
    renderizarAbaUsuarios,
    recarregarUsuariosNoEstado,
    abrirModalGestaoUsuario,
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", vincularEventosUsuarios);
  } else {
    vincularEventosUsuarios();
  }
})();