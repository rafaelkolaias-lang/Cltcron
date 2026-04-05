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

  function urlListarPagamentosPorUsuario(userId) {
    return `./commands/pagamentos/listar_por_usuario.php?user_id=${encodeURIComponent(userId)}`;
  }
  function urlCriarPagamento() { return "./commands/pagamentos/criar.php"; }

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
      const msg = (json && json.mensagem) ? json.mensagem : `HTTP ${resp.status}`;
      throw new Error(msg);
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
      status_conta: String(u.status_conta || ""),
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

    tbody.innerHTML = lista.map((u) => {
      const uid = escapeHtmlSeguro(u.user_id);
      const nomeLinha = u.nome_exibicao && u.nome_exibicao !== u.user_id
        ? `<div class="texto-fraco small">${escapeHtmlSeguro(u.nome_exibicao)}</div>`
        : "";

      return `
        <tr>
          <td>
            <div class="fw-semibold">${uid}</div>
            ${nomeLinha}
            <div class="texto-fraco small">Chave: <span class="texto-mono">${escapeHtmlSeguro(u.chave || "—")}</span></div>
          </td>

          <td class="text-center">${badgeNivel(u.nivel)}</td>

          <td class="text-center">
            <span class="fw-semibold">${escapeHtmlSeguro(formatarDinheiroBr(u.valor_hora))}</span>
          </td>

          <td class="text-center">${badgeStatusConta(u.status_conta)}</td>

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
    if (valorHora <= 0) {
      nucleo.utilidades.mostrarAlerta("aviso", "Valor por hora inválido", "Informe um valor maior que zero.");
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
    const elReferenciaInicio = document.getElementById("entradaPagamentoReferenciaInicio");
    const elReferenciaFim = document.getElementById("entradaPagamentoReferenciaFim");
    const elTravadoAte = document.getElementById("entradaPagamentoTravadoAte");
    const elValor = document.getElementById("entradaPagamentoValor");
    const elObs = document.getElementById("entradaPagamentoObs");

    if (elData) elData.value = dataHojeIsoSeguro();
    if (elReferenciaInicio) elReferenciaInicio.value = "";
    if (elReferenciaFim) elReferenciaFim.value = "";
    if (elTravadoAte) elTravadoAte.value = "";
    if (elValor) elValor.value = "";
    if (elObs) elObs.value = "";
  }

  function sincronizarTravadoAteComReferencia() {
    const elData = document.getElementById("entradaPagamentoData");
    const elReferenciaFim = document.getElementById("entradaPagamentoReferenciaFim");
    const elTravadoAte = document.getElementById("entradaPagamentoTravadoAte");

    if (!elTravadoAte) return;

    const referenciaFim = String(elReferenciaFim?.value || "").trim();
    const dataPagamento = String(elData?.value || "").trim();

    if (!String(elTravadoAte.value || "").trim()) {
      elTravadoAte.value = referenciaFim || dataPagamento || "";
    }
  }

  async function carregarPagamentosNoModal(uid) {
    const nucleo = obterNucleo();
    const tbody = document.getElementById("tbodyGestaoPagamentos");
    const elTotal = document.getElementById("textoGestaoTotalPago");

    try {
      if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="texto-fraco">Carregando…</td></tr>`;

      const lista = await listarPagamentosDoBackend(uid);
      const ordenada = lista.slice(0).sort((a, b) => String(b.data_pagamento || "").localeCompare(String(a.data_pagamento || "")));

      const total = ordenada.reduce((acc, p) => acc + Number(p.valor || 0), 0);
      if (elTotal) elTotal.textContent = formatarDinheiroBr(total);

      if (!tbody) return;

      if (!ordenada.length) {
        tbody.innerHTML = `<tr><td colspan="5" class="texto-fraco">Nenhum pagamento registrado.</td></tr>`;
        return;
      }

      tbody.innerHTML = ordenada.map((p) => {
        const dataPagamento = dataIsoParaBrSeguro(String(p.data_pagamento || ""));
        const periodo = formatarPeriodoPagamento(p.referencia_inicio, p.referencia_fim);
        const travado = p.travado_ate_data ? dataIsoParaBrSeguro(String(p.travado_ate_data || "")) : "—";
        const observacao = String(p.observacao || "").trim() || "—";

        return `
          <tr>
            <td>${escapeHtmlSeguro(dataPagamento)}</td>
            <td>${escapeHtmlSeguro(periodo)}</td>
            <td>${escapeHtmlSeguro(travado)}</td>
            <td class="text-end fw-semibold">${escapeHtmlSeguro(formatarDinheiroBr(p.valor))}</td>
            <td>${escapeHtmlSeguro(observacao)}</td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="texto-fraco">Falha ao carregar.</td></tr>`;
      nucleo.utilidades.mostrarAlerta("erro", "Falha ao listar pagamentos", String(e && e.message ? e.message : e));
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

    await carregarPagamentosNoModal(uid);

    const modalEl = document.getElementById("modalGestaoUsuario");
    if (modalEl && window.bootstrap) window.bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

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
    if (valorHora <= 0) {
      nucleo.utilidades.mostrarAlerta("aviso", "Valor inválido", "Informe um valor maior que zero.");
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

  async function registrarPagamentoReal() {
    const nucleo = obterNucleo();
    if (!usuarioGestaoAbertoId) return;

    const u = buscarUsuarioGestao(usuarioGestaoAbertoId);
    if (!u) return;

    const elData = document.getElementById("entradaPagamentoData");
    const elReferenciaInicio = document.getElementById("entradaPagamentoReferenciaInicio");
    const elReferenciaFim = document.getElementById("entradaPagamentoReferenciaFim");
    const elTravadoAte = document.getElementById("entradaPagamentoTravadoAte");
    const elValor = document.getElementById("entradaPagamentoValor");
    const elObs = document.getElementById("entradaPagamentoObs");

    const data = String(elData?.value || "").trim();
    const referenciaInicio = String(elReferenciaInicio?.value || "").trim();
    const referenciaFim = String(elReferenciaFim?.value || "").trim();
    const travadoAteInformado = String(elTravadoAte?.value || "").trim();
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
    if (referenciaInicio && referenciaFim && referenciaInicio > referenciaFim) {
      nucleo.utilidades.mostrarAlerta("aviso", "Período inválido", "A referência início não pode ser maior que a referência fim.");
      return;
    }

    const travadoAte = travadoAteInformado || referenciaFim || data;

    try {
      await criarPagamentoNoBackend({
        user_id: u.user_id,
        data_pagamento: data,
        referencia_inicio: referenciaInicio || null,
        referencia_fim: referenciaFim || null,
        travado_ate_data: travadoAte || null,
        valor,
        observacao: obs,
      });

      prepararCamposPagamentoPadrao();
      await carregarPagamentosNoModal(u.user_id);

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

    const elPagamentoData = document.getElementById("entradaPagamentoData");
    const elPagamentoReferenciaFim = document.getElementById("entradaPagamentoReferenciaFim");
    const elPagamentoTravadoAte = document.getElementById("entradaPagamentoTravadoAte");

    if (elPagamentoData) {
      elPagamentoData.addEventListener("change", () => sincronizarTravadoAteComReferencia());
    }
    if (elPagamentoReferenciaFim) {
      elPagamentoReferenciaFim.addEventListener("change", () => sincronizarTravadoAteComReferencia());
    }
    if (elPagamentoTravadoAte) {
      elPagamentoTravadoAte.addEventListener("focus", () => sincronizarTravadoAteComReferencia());
    }

    const modalGestao = document.getElementById("modalGestaoUsuario");
    if (modalGestao) {
      modalGestao.addEventListener("hidden.bs.modal", () => {
        usuarioGestaoAbertoId = "";
        alternarModoEdicao(false);
      });
    }
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