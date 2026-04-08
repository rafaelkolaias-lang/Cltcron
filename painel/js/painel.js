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

  window.PainelNucleo_trocarAba = function(idAba) { trocarAba(idAba); };

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

  function renderizarDashboard() {
    const elUltima = document.getElementById("textoUltimaAtualizacao");
    if (elUltima) elUltima.textContent = agoraTexto();

    const total = estado.usuariosDashboard.length;
    const ativos = estado.usuariosDashboard.filter((u) => String(u.status_conta).toLowerCase() === "ativa").length;

    const elNumeroUsuarios = document.getElementById("numeroUsuarios");
    const elNumeroAtivos = document.getElementById("numeroUsuariosAtivos");
    if (elNumeroUsuarios) elNumeroUsuarios.textContent = String(total);
    if (elNumeroAtivos) elNumeroAtivos.textContent = String(ativos);
  }

  // ==========================================================
  // Navegação
  // ==========================================================
  function trocarAba(idAba) {
    const abas = ["abaDashboard", "abaUsuarios", "abaGestaoUsuario", "abaAtividades", "abaGerenciarTarefas", "abaRelatorio"];

    abas.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.classList.toggle("d-none", id !== idAba);
    });

    document.querySelectorAll("#menuAbas .nav-link").forEach((a) => {
      a.classList.toggle("active", a.getAttribute("data-aba") === idAba);
    });

    const subt = {
      abaDashboard: "Dashboard · visão geral e gráficos",
      abaUsuarios: "Usuários · gestão e pagamentos",
      abaGestaoUsuario: "Gestão do Usuário · dados e pagamentos",
      abaAtividades: "Atividades · atribuições",
      abaGerenciarTarefas: "Gerenciar Tarefas · declarações",
      abaRelatorio: "Relatório · tempo trabalhado declarado",
    }[idAba] || "";

    const elSub = document.getElementById("textoSubtitulo");
    if (elSub) elSub.textContent = subt;

    // ✅ Render específico por aba
    if (idAba === "abaGestaoUsuario") {
      // Conteúdo carregado ao abrir via abrirModalGestaoUsuario
      return;
    }

    if (idAba === "abaUsuarios") {
      window.PainelAbaUsuarios?.renderizarAbaUsuarios?.();
      return;
    }

    if (idAba === "abaAtividades") {
      window.PainelAbaAtividades?.renderizarAbaAtividades?.();
      return;
    }

    if (idAba === "abaGerenciarTarefas") {
      window.recarregarAbaGerenciarTarefas?.();
      return;
    }

    if (idAba === "abaRelatorio") {
      window.PainelAbaRelatorio?.renderizarAbaRelatorio?.();
      return;
    }

    // Dashboard — renderiza tabela + carrega gráficos
    renderizarDashboard();
    window.PainelAbaGraficos?.renderizarAbaGraficos?.();
    setTimeout(() => window.PainelAbaGraficos?.resizarGraficos?.(), 50);
  }

  function obterAbaVisivel() {
    const abaGestaoUsuario = document.getElementById("abaGestaoUsuario");
    if (abaGestaoUsuario && !abaGestaoUsuario.classList.contains("d-none")) return "abaGestaoUsuario";

    const abaAtividades = document.getElementById("abaAtividades");
    if (abaAtividades && !abaAtividades.classList.contains("d-none")) return "abaAtividades";

    const abaGerenciarTarefas = document.getElementById("abaGerenciarTarefas");
    if (abaGerenciarTarefas && !abaGerenciarTarefas.classList.contains("d-none")) return "abaGerenciarTarefas";

    const abaUsuarios = document.getElementById("abaUsuarios");
    if (abaUsuarios && !abaUsuarios.classList.contains("d-none")) return "abaUsuarios";

    const abaRelatorio = document.getElementById("abaRelatorio");
    if (abaRelatorio && !abaRelatorio.classList.contains("d-none")) return "abaRelatorio";

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

      if (aba === "abaGerenciarTarefas") {
        await window.recarregarAbaGerenciarTarefas?.();
        return;
      }

      // Dashboard — recarrega tabela + gráficos
      await carregarUsuariosParaDashboard();
      renderizarDashboard();
      window.PainelAbaGraficos?.renderizarAbaGraficos?.();
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

    const botaoAtualizar = document.getElementById("botaoAtualizarTudo");
    if (botaoAtualizar) botaoAtualizar.addEventListener("click", () => {
      rerenderizarAbaAtual();
      mostrarAlerta("sucesso", "Atualizado", "Recarreguei os dados do banco.");
    });

    const botaoRecarregar = document.getElementById("botaoRecarregarAba");
    if (botaoRecarregar) botaoRecarregar.addEventListener("click", () => {
      rerenderizarAbaAtual();
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
