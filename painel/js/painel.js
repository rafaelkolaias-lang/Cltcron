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
    const mapaCor = { sucesso: "#3ecf6e", erro: "#ff5555", aviso: "#f0a500", info: "#60a5fa" };
    const mapaBorda = { sucesso: "#2a7d44", erro: "#8b2020", aviso: "#7a5500", info: "#2a5090" };
    const cor = mapaCor[tipo] || "#60a5fa";
    const borda = mapaBorda[tipo] || "#2a5090";

    let modal = document.getElementById("modalAlertaGlobal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "modalAlertaGlobal";
      modal.className = "modal fade";
      modal.tabIndex = -1;
      modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-sm">
          <div class="modal-content bg-dark text-light" style="border:1px solid ${borda};" id="modalAlertaConteudo">
            <div class="modal-body text-center py-4">
              <div class="fw-bold mb-1" style="color:${cor};" id="modalAlertaTitulo"></div>
              <div class="small texto-fraco" id="modalAlertaDetalhe"></div>
            </div>
            <div class="modal-footer border-secondary justify-content-center py-2">
              <button type="button" class="btn btn-sm btn-outline-light" data-bs-dismiss="modal">OK</button>
            </div>
          </div>
        </div>
      `;
      document.body.appendChild(modal);
    }

    const elConteudo = modal.querySelector("#modalAlertaConteudo");
    if (elConteudo) elConteudo.style.borderColor = borda;
    const elTitulo = modal.querySelector("#modalAlertaTitulo");
    const elDetalhe = modal.querySelector("#modalAlertaDetalhe");
    if (elTitulo) { elTitulo.textContent = titulo || "Aviso"; elTitulo.style.color = cor; }
    if (elDetalhe) elDetalhe.textContent = detalhe || "";

    const bsModal = bootstrap.Modal.getOrCreateInstance(modal);
    bsModal.show();
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

    const _formatarErro = (j, status) => {
      const base = (j && j.mensagem) ? j.mensagem : `HTTP ${status}`;
      const d = j && j.dados;
      const detalhe = (d && typeof d === "object")
        ? [d.erro, d.arquivo && `@${d.arquivo}:${d.linha || "?"}`].filter(Boolean).join(" ")
        : "";
      return detalhe ? `${base} — ${detalhe}` : base;
    };

    if (!resp.ok) {
      throw new Error(_formatarErro(json, resp.status));
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
    const abas = ["abaDashboard", "abaUsuarios", "abaGestaoUsuario", "abaAtividades", "abaGerenciarTarefas", "abaRelatorio", "abaCredenciais", "abaAuditoria", "abaMega"];

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
      abaCredenciais: "Credenciais e APIs · segredos por usuário",
      abaAuditoria: "Auditoria · apps suspeitos e alertas por usuário",
      abaMega: "MEGA · upload obrigatório por canal e usuário",
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

    if (idAba === "abaCredenciais") {
      // aba-credenciais.js observa mudanças em #abaCredenciais e carrega sozinho
      return;
    }

    if (idAba === "abaAuditoria") {
      window.PainelAbaAuditoria?.renderizarAbaAuditoria?.();
      return;
    }

    if (idAba === "abaMega") {
      window.PainelAbaMega?.renderizarAbaMega?.();
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

    const abaCredenciais = document.getElementById("abaCredenciais");
    if (abaCredenciais && !abaCredenciais.classList.contains("d-none")) return "abaCredenciais";

    const abaMega = document.getElementById("abaMega");
    if (abaMega && !abaMega.classList.contains("d-none")) return "abaMega";

    const abaAuditoria = document.getElementById("abaAuditoria");
    if (abaAuditoria && !abaAuditoria.classList.contains("d-none")) return "abaAuditoria";

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

      if (aba === "abaAuditoria") {
        window.PainelAbaAuditoria?.renderizarAbaAuditoria?.();
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
