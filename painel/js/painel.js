// js/painel.js
// Núcleo do painel + Dashboard + navegação + eventos gerais (REAL: banco)

(function () {
  // ==========================================================
  // Utilidades base
  // ==========================================================
  function agoraTexto() {
    return new Date().toLocaleString("pt-BR");
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function mostrarAlerta(tipo, titulo, detalhe) {
    const area = document.getElementById("areaAlertas");
    if (!area) return;

    const mapa = { sucesso: "success", erro: "danger", aviso: "warning", info: "info" };
    const classe = mapa[tipo] || "info";

    area.innerHTML = `
      <div class="alert alert-${classe} alert-dismissible fade show cartao-grafite" role="alert">
        <div class="fw-semibold">${escapeHtml(titulo || "Aviso")}</div>
        ${detalhe ? `<div class="small texto-fraco mt-1">${escapeHtml(detalhe)}</div>` : ""}
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
      </div>
    `;
  }

  function dataHojeIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }

  function dataIsoParaBr(iso) {
    if (!iso) return "—";
    const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return String(iso);
    return `${m[3]}/${m[2]}/${m[1]}`;
  }

  function dataHoraCurta(iso) {
    if (!iso) return "—";
    const s = String(iso).replace(" ", "T");
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return String(iso).slice(0, 16);
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  // ==========================================================
  // Estado global
  // ==========================================================
  const estado = {
    usuariosDashboard: [],
    usuariosGestao: [],
  };

  window.PainelNucleo = {
    estado,
    utilidades: {
      agoraTexto,
      escapeHtml,
      mostrarAlerta,
      dataHojeIso,
      dataIsoParaBr,
      dataHoraCurta,
    },
  };

  // ==========================================================
  // API helpers
  // ==========================================================
  async function requisitarJson(url, opcoes = {}) {
    const resp = await fetch(url, { cache: "no-store", ...opcoes });

    let json = null;
    try { json = await resp.json(); } catch { json = null; }

    if (!resp.ok) {
      const msg = (json && json.mensagem) ? json.mensagem : `HTTP ${resp.status}`;
      throw new Error(msg);
    }

    if (!json || typeof json.ok !== "boolean") {
      throw new Error("Resposta inválida do servidor.");
    }

    return json;
  }

  async function carregarUsuariosParaDashboard() {
    const json = await requisitarJson("./commands/usuarios/listar.php");
    if (!json.ok) throw new Error(json.mensagem || "Falha ao listar usuários.");
    const lista = Array.isArray(json.dados) ? json.dados : [];

    estado.usuariosDashboard = lista.map((u) => ({
      user_id: String(u.user_id || ""),
      nome_exibicao: String(u.nome_exibicao || ""),
      nivel: String(u.nivel || ""),
      valor_hora: Number(u.valor_hora || 0),
      status_conta: String(u.status_conta || ""),
      atualizado_em: String(u.atualizado_em || ""),
    }));
  }

  function badgeStatusConta(status) {
    const s = String(status || "").toLowerCase();
    if (s === "ativa") return `<span class="badge text-bg-success">Ativa</span>`;
    if (s === "inativa") return `<span class="badge text-bg-secondary">Inativa</span>`;
    if (s === "bloqueada") return `<span class="badge text-bg-danger">Bloqueada</span>`;
    return `<span class="badge text-bg-secondary">—</span>`;
  }

  function badgeNivel(nivel) {
    const n = String(nivel || "").toLowerCase();
    if (n === "iniciante") return `<span class="badge text-bg-secondary">Iniciante</span>`;
    if (n === "intermediario") return `<span class="badge text-bg-info text-dark">Intermediário</span>`;
    if (n === "avancado") return `<span class="badge text-bg-warning text-dark">Avançado</span>`;
    return `<span class="badge text-bg-secondary">—</span>`;
  }

  function formatarDinheiroBr(num) {
    const v = Number(num || 0);
    return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  let _dashboardDelegacaoVinculada = false;
  function vincularAcoesDashboard() {
    if (_dashboardDelegacaoVinculada) return;
    _dashboardDelegacaoVinculada = true;
    const tbody = document.getElementById("tbodyResumoUsuarios");
    if (!tbody) return;
    tbody.addEventListener("click", (ev) => {
      const btn = ev.target.closest("button[data-acao-dashboard][data-uid]");
      if (!btn) return;
      const identificador_usuario = btn.getAttribute("data-uid") || "";
      if (window.PainelAbaUsuarios?.abrirModalGestaoUsuario) {
        window.PainelAbaUsuarios.abrirModalGestaoUsuario(identificador_usuario);
      }
    });
  }

  function renderizarDashboard() {
    const elUltima = document.getElementById("textoUltimaAtualizacao");
    if (elUltima) elUltima.textContent = agoraTexto();

    const total = estado.usuariosDashboard.length;
    const ativos = estado.usuariosDashboard.filter((u) => String(u.status_conta).toLowerCase() === "ativa").length;

    const elNumeroUsuarios = document.getElementById("numeroUsuarios");
    const elNumeroAtivos = document.getElementById("numeroUsuariosAtivos");
    if (elNumeroUsuarios) elNumeroUsuarios.textContent = String(total);
    if (elNumeroAtivos) elNumeroAtivos.textContent = String(ativos);

    const entradaBusca = document.getElementById("entradaBuscaGeral");
    const busca = String(entradaBusca?.value || "").trim().toLowerCase();

    const lista = estado.usuariosDashboard
      .slice(0)
      .filter((u) => {
        if (!busca) return true;
        const hay = [u.user_id, u.nome_exibicao, u.nivel].join(" ").toLowerCase();
        return hay.includes(busca);
      })
      .sort((a, b) => String(a.user_id).localeCompare(String(b.user_id), "pt-BR", { sensitivity: "base" }));

    const tbody = document.getElementById("tbodyResumoUsuarios");
    if (!tbody) return;

    if (!lista.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="texto-fraco">Nenhum usuário encontrado.</td></tr>`;
      return;
    }

    tbody.innerHTML = lista.map((u) => {
      const identificador_usuario = escapeHtml(u.user_id);
      const nomeLinha = u.nome_exibicao && u.nome_exibicao !== u.user_id
        ? `<div class="texto-fraco small">${escapeHtml(u.nome_exibicao)}</div>`
        : "";

      return `
        <tr>
          <td>
            <div class="fw-semibold">${identificador_usuario}</div>
            ${nomeLinha}
          </td>
          <td class="text-center">${badgeStatusConta(u.status_conta)}</td>
          <td class="text-center">${badgeNivel(u.nivel)}</td>
          <td class="text-center"><span class="fw-semibold">${escapeHtml(formatarDinheiroBr(u.valor_hora))}</span></td>
          <td class="text-center"><span class="texto-mono">${escapeHtml(dataHoraCurta(u.atualizado_em))}</span></td>
          <td class="text-end">
            <button class="btn btn-sm btn-outline-light" type="button" data-acao-dashboard="gestao" data-uid="${identificador_usuario}">
              Gestão
            </button>
          </td>
        </tr>
      `;
    }).join("");

    vincularAcoesDashboard(); // event delegation — registra apenas 1 vez
  }

  // ==========================================================
  // Navegação
  // ==========================================================
  function trocarAba(idAba) {
    const abas = ["abaDashboard", "abaUsuarios", "abaAtividades", "abaGraficos", "abaRelatorio"];

    abas.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle("d-none", id !== idAba);
    });

    document.querySelectorAll("#menuAbas .nav-link").forEach((a) => {
      a.classList.toggle("active", a.getAttribute("data-aba") === idAba);
    });

    const subt = {
      abaDashboard: "Dashboard · visão geral",
      abaUsuarios: "Usuários · gestão e pagamentos",
      abaAtividades: "Atividades · atribuições",
      abaGraficos: "Gráficos · apps e uso",
      abaRelatorio: "Relatório · tempo trabalhado declarado",
    }[idAba] || "";

    const elSub = document.getElementById("textoSubtitulo");
    if (elSub) elSub.textContent = subt;

    // ✅ Render específico por aba
    if (idAba === "abaUsuarios") {
      window.PainelAbaUsuarios?.renderizarAbaUsuarios?.();
      return;
    }

    if (idAba === "abaAtividades") {
      window.PainelAbaAtividades?.renderizarAbaAtividades?.();
      return;
    }

    if (idAba === "abaGraficos") {
      window.PainelAbaGraficos?.renderizarAbaGraficos?.();
      return;
    }

    if (idAba === "abaRelatorio") {
      window.PainelAbaRelatorio?.renderizarAbaRelatorio?.();
      return;
    }

    renderizarDashboard();
  }

  function obterAbaVisivel() {
    const abaGraficos = document.getElementById("abaGraficos");
    if (abaGraficos && !abaGraficos.classList.contains("d-none")) return "abaGraficos";

    const abaAtividades = document.getElementById("abaAtividades");
    if (abaAtividades && !abaAtividades.classList.contains("d-none")) return "abaAtividades";

    const abaUsuarios = document.getElementById("abaUsuarios");
    if (abaUsuarios && !abaUsuarios.classList.contains("d-none")) return "abaUsuarios";

    return "abaDashboard";
  }

  async function rerenderizarAbaAtual() {
    const aba = obterAbaVisivel();

    try {
      if (aba === "abaUsuarios") {
        await window.PainelAbaUsuarios?.recarregarUsuariosNoEstado?.();
        window.PainelAbaUsuarios?.renderizarAbaUsuarios?.();
        return;
      }

      if (aba === "abaAtividades") {
        await window.PainelAbaAtividades?.recarregarAtividadesNoEstado?.();
        window.PainelAbaAtividades?.renderizarAbaAtividades?.();
        return;
      }

      if (aba === "abaGraficos") {
        await window.PainelAbaGraficos?.recarregarGraficosNoEstado?.();
        window.PainelAbaGraficos?.renderizarAbaGraficos?.();
        return;
      }

      await carregarUsuariosParaDashboard();
      renderizarDashboard();
    } catch (e) {
      mostrarAlerta("erro", "Falha ao atualizar", String(e && e.message ? e.message : e));
    }
  }

  // ==========================================================
  // Eventos gerais
  // ==========================================================
  function configurarEventosGerais() {
    document.querySelectorAll("#menuAbas a[data-aba]").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        trocarAba(a.getAttribute("data-aba"));
      });
    });

    const entradaBusca = document.getElementById("entradaBuscaGeral");
    let _debounceTimerBusca = null;
    if (entradaBusca) entradaBusca.addEventListener("input", () => {
      clearTimeout(_debounceTimerBusca);
      _debounceTimerBusca = setTimeout(renderizarDashboard, 300);
    });

    const botaoLimpar = document.getElementById("botaoLimparBusca");
    if (botaoLimpar) botaoLimpar.addEventListener("click", () => {
      if (entradaBusca) entradaBusca.value = "";
      renderizarDashboard();
    });

    const botaoAtualizar = document.getElementById("botaoAtualizarTudo");
    if (botaoAtualizar) botaoAtualizar.addEventListener("click", () => {
      rerenderizarAbaAtual();
      mostrarAlerta("sucesso", "Atualizado", "Recarreguei os dados do banco.");
    });

    const botaoRecarregar = document.getElementById("botaoRecarregarAba");
    if (botaoRecarregar) botaoRecarregar.addEventListener("click", () => {
      rerenderizarAbaAtual();
    });

    let timerAuto = null;
    const botaoAuto = document.getElementById("botaoAutoAtualizacao");

    function _pararTimerAuto() {
      if (timerAuto) { clearInterval(timerAuto); timerAuto = null; }
    }
    function _iniciarTimerAuto() {
      _pararTimerAuto();
      timerAuto = setInterval(() => { rerenderizarAbaAtual(); }, 30000);
    }

    if (botaoAuto) botaoAuto.addEventListener("click", () => {
      const ativo = botaoAuto.getAttribute("data-ativo") === "1";

      if (ativo) {
        botaoAuto.setAttribute("data-ativo", "0");
        botaoAuto.textContent = "Auto: off";
        _pararTimerAuto();
        mostrarAlerta("info", "Auto atualização", "Desligada.");
        return;
      }

      botaoAuto.setAttribute("data-ativo", "1");
      botaoAuto.textContent = "Auto: on";
      _iniciarTimerAuto();
      mostrarAlerta("info", "Auto atualização", "Ligada (30s).");
    });

    // Pausar auto-atualização quando a aba do navegador fica oculta
    document.addEventListener("visibilitychange", () => {
      if (!botaoAuto || botaoAuto.getAttribute("data-ativo") !== "1") return;
      if (document.hidden) {
        _pararTimerAuto();
      } else {
        _iniciarTimerAuto();
      }
    });
  }

  // ==========================================================
  // Boot
  // ==========================================================
  async function iniciar() {
    configurarEventosGerais();

    try {
      await window.PainelAbaUsuarios?.iniciarUsuarios?.();
      await window.PainelAbaAtividades?.iniciarAtividades?.();
      await window.PainelAbaGraficos?.iniciarGraficos?.(); // ✅ novo
      await carregarUsuariosParaDashboard();
    } catch (e) {
      mostrarAlerta("erro", "Falha ao iniciar", String(e && e.message ? e.message : e));
    }

    trocarAba("abaDashboard");
    renderizarDashboard();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", iniciar);
  } else {
    iniciar();
  }
})();
