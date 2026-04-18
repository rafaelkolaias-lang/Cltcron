(function () {
  "use strict";

  const urlApiGraficos = "./commands/graficos/graficos.php";
  const seletorAbaGraficos = "#areaGraficos";
  const seletorAreaAlertas = "#areaAlertas";

  let requisicaoEmAndamento = false;
  let metaCarregada = false;

  // Instâncias ECharts (reutilizadas para evitar memory leaks)
  let chartDonut = null;
  let chartBarras = null;
  let chartTimeline = null;

  // Paleta de cores RK Produções (gradiente pink → laranja → amarelo → roxo → azul)
  const PALETA = [
    "#ff1f5b", "#ff6b1f", "#ffd600", "#a800ff", "#1a1aff",
    "#ff4d8d", "#ff9944", "#ffe566", "#c84bff", "#5577ff",
    "#ff3d7a", "#ffb833", "#b300e0", "#3355ee", "#ff8040",
  ];

  // ─── Mapa de cores fixas por aplicativo ─────────────────────
  const MAPA_CORES_APPS = {
    "DaVinci Resolve":     "#ef4444",
    "Adobe Premiere Pro":  "#8b5cf6",
    "Adobe After Effects": "#cc44ff",
    "Adobe Photoshop":     "#31a8ff",
    "Google Chrome":       "#3b82f6",
    "chrome.exe":          "#3b82f6",
    "File Explorer":       "#64748b",
    "WhatsApp":            "#25d366",
    "CapCut":              "#10b981",
    "Telegram":            "#0088cc",
    "discord.exe":         "#5865f2",
    "Slack.exe":           "#4a154b",
    "VLC media player.exe":"#f97316",
    "Microsoft Word.exe":  "#2b579a",
  };

  let CORES_CUSTOMIZADAS = JSON.parse(localStorage.getItem("rk_cores_apps") || "{}");
  let _cacheCorApps = {};  // Cache de cores calculadas — evita recalcular em loops

  function _obterCorApp(nome) {
    const n = String(nome || "—").trim();
    if (_cacheCorApps[n]) return _cacheCorApps[n];
    let cor;
    if (CORES_CUSTOMIZADAS[n])    cor = CORES_CUSTOMIZADAS[n]; // 1º: customizada pelo usuário
    else if (MAPA_CORES_APPS[n])  cor = MAPA_CORES_APPS[n];    // 2º: mapa fixo
    else {                                                      // 3º: hash determinístico
      let hash = 0;
      for (let i = 0; i < n.length; i++) hash = n.charCodeAt(i) + ((hash << 5) - hash);
      cor = PALETA[Math.abs(hash) % PALETA.length];
    }
    _cacheCorApps[n] = cor;
    return cor;
  }

  function _invalidarCacheCores() {
    CORES_CUSTOMIZADAS = JSON.parse(localStorage.getItem("rk_cores_apps") || "{}");
    _cacheCorApps = {};
  }

  // ─── Utilidades ─────────────────────────────────────────────
  /** Clareia uma cor hex misturando com branco (fator 0–1). */
  function _clarearCor(hex, fator) {
    const r = parseInt(hex.slice(1,3), 16);
    const g = parseInt(hex.slice(3,5), 16);
    const b = parseInt(hex.slice(5,7), 16);
    const f = fator || 0.35;
    const rc = Math.round(r + (255-r)*f).toString(16).padStart(2,"0");
    const gc = Math.round(g + (255-g)*f).toString(16).padStart(2,"0");
    const bc = Math.round(b + (255-b)*f).toString(16).padStart(2,"0");
    return `#${rc}${gc}${bc}`;
  }

  /** Cria um LinearGradient horizontal com efeito de brilho central. */
  function _gradienteBarra(corBase) {
    return new echarts.graphic.LinearGradient(0, 0, 1, 0, [
      { offset: 0,    color: _clarearCor(corBase, 0.25) },
      { offset: 0.45, color: _clarearCor(corBase, 0.55) },
      { offset: 0.55, color: _clarearCor(corBase, 0.55) },
      { offset: 1,    color: _clarearCor(corBase, 0.2)  },
    ]);
  }

  function escaparHtml(t) {
    return String(t ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  function hhmmss(seg) {
    const t = Math.max(0, Number(seg || 0));
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), s = Math.floor(t % 60);
    return `${String(h).padStart(2,"0")}:${String(m).padStart(2,"0")}:${String(s).padStart(2,"0")}`;
  }

  function hhmm(seg) {
    const t = Math.max(0, Number(seg || 0));
    const h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60);
    if (h > 0) return `${h}h${String(m).padStart(2,"0")}`;
    return `${m}min`;
  }

  function dataHoraCurta(v) {
    const t = String(v || "").trim();
    if (!t) return "—";
    const p = t.split(" ");
    if (p.length !== 2) return t;
    const d = p[0].split("-"), h = p[1].split(":");
    if (d.length !== 3 || h.length < 2) return t;
    return `${d[2]}/${d[1]} ${h[0]}:${h[1]}`;
  }

  function obterDataHojeIso() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  }

  function subtrairDiasIso(iso, n) {
    const p = String(iso).split("-");
    if (p.length !== 3) return iso;
    const d = new Date(+p[0], +p[1]-1, +p[2]);
    d.setDate(d.getDate() - Number(n || 0));
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
  }

  function mostrarAlerta(tipo, titulo, msg) {
    const area = document.querySelector(seletorAreaAlertas);
    if (!area) return;
    const cls = tipo === "sucesso" ? "alert-success" : tipo === "aviso" ? "alert-warning" : "alert-danger";
    area.insertAdjacentHTML("afterbegin", `
      <div class="alert ${cls} alert-dismissible fade show" role="alert">
        <strong>${escaparHtml(titulo)}</strong> ${escaparHtml(msg)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
      </div>
    `);
  }

  function abaGraficosEstaVisivel() {
    // Gráficos agora vivem dentro do #abaDashboard
    const dash = document.getElementById("abaDashboard");
    return !!dash && !dash.classList.contains("d-none");
  }

  async function requisitarJson(url, corpo) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(corpo || {}),
      cache: "no-store",
    });
    let json = null;
    try { json = await resp.json(); } catch (_) {}
    if (!resp.ok || !json || json.ok !== true) {
      const base = json?.mensagem || `HTTP ${resp.status}`;
      // inclui detalhe do backend quando disponível (dados.erro, dados.arquivo, dados.linha)
      const d = json?.dados;
      const detalhe = (d && typeof d === "object")
        ? [d.erro, d.arquivo && `@${d.arquivo}:${d.linha || "?"}`].filter(Boolean).join(" ")
        : "";
      throw new Error(detalhe ? `${base} — ${detalhe}` : base);
    }
    return json.dados;
  }

  function iniciais(nome) {
    const p = String(nome || "?").trim().split(/\s+/);
    return (p[0]?.[0] || "?").toUpperCase() + (p.length > 1 ? p[p.length-1][0].toUpperCase() : "");
  }

  function classeStatus(s) {
    const t = String(s || "").toLowerCase();
    if (t === "trabalhando") return "indicador-status--trabalhando";
    if (t === "ocioso") return "indicador-status--ocioso";
    if (t === "pausado") return "indicador-status--pausado";
    return "indicador-status--sem_status";
  }

  function textoStatus(s) {
    const t = String(s || "").toLowerCase();
    if (t === "trabalhando") return "Trabalhando";
    if (t === "ocioso") return "Ocioso";
    if (t === "pausado") return "Pausado";
    return "Offline";
  }

  // ─── Filtro interativo por App ────────────────────────────
  function alternarFiltroApp(nome) {
    const idx = FILTROS_APPS_ATIVOS.indexOf(nome);
    if (idx === -1) FILTROS_APPS_ATIVOS.push(nome);
    else FILTROS_APPS_ATIVOS.splice(idx, 1);
    // Re-renderiza só os charts de apps sem re-fetch — a legenda fica completa
    _reRenderizarFiltroApps();
  }

  function _reRenderizarFiltroApps() {
    if (!_dadosPainelAtual) return;
    const userId = (document.getElementById("filtroGraficosUsuarioDetalhe") || {}).value || "";
    const usuarios = _dadosPainelAtual.usuarios || [];
    if (!userId) {
      renderizarGlobalApps(usuarios);
      _renderizarTeamTimelineDoDia();
    } else {
      const u = usuarios.find(x => x.user_id === userId) || usuarios[0];
      if (u) {
        renderizarGlobalApps(usuarios);
        _renderizarTeamTimelineDoDia();
        renderizarTimelineAbertosDoDia();
      }
    }
  }

  function _renderizarLegendaLateral(appsItems, containerId) {
    const area = document.getElementById(containerId);
    if (!area) return;
    area.innerHTML = appsItems.map(a => {
      const nome = a.nome || a.nome_app || "—";
      const ativo = FILTROS_APPS_ATIVOS.length === 0 || FILTROS_APPS_ATIVOS.includes(nome);
      return `<div class="item-legenda ${ativo ? "active" : ""}" data-app="${escaparHtml(nome)}">
        <span class="item-legenda__dot" style="background:${_obterCorApp(nome)}"></span>
        <span class="item-legenda__label">${escaparHtml(nome)}</span>
      </div>`;
    }).join("");
    // Event delegation: um listener no container em vez de onclick em cada item
    area.onclick = (e) => {
      const item = e.target.closest(".item-legenda");
      if (item && item.dataset.app) alternarFiltroApp(item.dataset.app);
    };
  }

  // ─── Estrutura HTML ────────────────────────────────────────
  function garantirEstruturaSimplificada() {
    const aba = document.querySelector(seletorAbaGraficos);
    if (!aba) return;
    if (document.getElementById("painelGraficosSimplificado")) return;

    aba.innerHTML = `
      <div id="painelGraficosSimplificado" class="container-fluid px-0">

        <!-- Cards de resumo - status em tempo real -->
        <div class="row g-3 secao-graficos">
          <div class="col-6 col-md-4 col-xl-2">
            <div class="card-metrica">
              <div class="card-metrica__rotulo">Trabalhando</div>
              <div class="card-metrica__valor text-success" id="numeroResumoTrabalhandoAgora">0</div>
            </div>
          </div>
          <div class="col-6 col-md-4 col-xl-2">
            <div class="card-metrica">
              <div class="card-metrica__rotulo">Ociosos</div>
              <div class="card-metrica__valor text-warning" id="numeroResumoOciososAgora">0</div>
            </div>
          </div>
          <div class="col-6 col-md-4 col-xl-2">
            <div class="card-metrica">
              <div class="card-metrica__rotulo">Pausados</div>
              <div class="card-metrica__valor" id="numeroResumoPausadosAgora">0</div>
            </div>
          </div>
          <div class="col-6 col-md-4 col-xl-2">
            <div class="card-metrica">
              <div class="card-metrica__rotulo">Trabalhado</div>
              <div class="card-metrica__valor texto-mono text-success" style="font-size:1.1rem" id="textoResumoTempoTrabalhando">00:00:00</div>
            </div>
          </div>
          <div class="col-6 col-md-4 col-xl-2">
            <div class="card-metrica">
              <div class="card-metrica__rotulo">Ocioso</div>
              <div class="card-metrica__valor texto-mono text-warning" style="font-size:1.1rem" id="textoResumoTempoOcioso">00:00:00</div>
            </div>
          </div>
          <div class="col-6 col-md-4 col-xl-2">
            <div class="card-metrica">
              <div class="card-metrica__rotulo">Pausado</div>
              <div class="card-metrica__valor texto-mono" style="font-size:1.1rem" id="textoResumoTempoPausado">00:00:00</div>
            </div>
          </div>
        </div>

        <!-- Tabela de usuários com status -->
        <div class="cartao-grafite p-3 secao-graficos">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h6 class="mb-0 fw-bold">Visão Geral da Equipe</h6>
            <div class="texto-fraco small" id="textoTotalUsuarios"></div>
          </div>
          <div class="table-responsive tabela-limite" style="max-height:400px">
            <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
              <thead>
                <tr class="texto-fraco small">
                  <th>Membro</th>
                  <th>Status</th>
                  <th>Atividade</th>
                  <th>App em foco</th>
                  <th class="text-center">Conta</th>
                  <th class="text-end">R$/hora</th>
                  <th class="text-end">Trabalhado</th>
                  <th class="text-end">Ocioso</th>
                  <th class="text-end">Apps</th>
                  <th class="text-end">Ações</th>
                </tr>
              </thead>
              <tbody id="tbodyResumoUsuariosGraficos">
                <tr><td colspan="6" class="texto-fraco">Carregando…</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Detalhe do usuário selecionado -->
        <div class="cartao-grafite p-3 secao-graficos">
          <!-- Cabeçalho com título + filtros integrados -->
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
            <div>
              <h5 class="mb-0 fw-bold">Monitoramento de Atividade</h5>
              <div class="texto-fraco small mt-1">Controle em tempo real dos apps utilizados por cada membro da equipe</div>
            </div>
            <div class="texto-fraco small pt-1"><span id="textoGraficosUltimaAtualizacao">—</span></div>
          </div>
          <div class="filtros-compactos mb-3">
            <div>
              <label>Início</label>
              <input type="date" id="filtroGraficosDataInicio" class="form-control form-control-sm bg-transparent text-white border-secondary" style="width:145px">
            </div>
            <div>
              <label>Fim</label>
              <input type="date" id="filtroGraficosDataFim" class="form-control form-control-sm bg-transparent text-white border-secondary" style="width:145px">
            </div>
            <div class="d-flex gap-1 align-items-end">
              <button type="button" id="botaoAplicarFiltrosGraficos" class="btn btn-sm btn-light botao-mini">Aplicar data</button>
              <button type="button" id="botaoLimparFiltrosGraficos" class="btn btn-sm btn-outline-light botao-mini">Limpar data</button>
            </div>
            <div>
              <label>Membro</label>
              <select id="filtroGraficosUsuarioDetalhe" class="form-select form-select-sm bg-transparent text-white border-secondary" style="width:220px"></select>
            </div>
            <div class="d-flex align-items-end">
              <button type="button" id="botaoAbrirModalCores" class="btn btn-sm btn-outline-warning botao-mini" title="Personalizar cores dos aplicativos">🎨 Cores</button>
            </div>
          </div>
          <hr class="separador-sutil" style="margin-top:0">
          <div id="areaUsuarioSelecionadoGraficos">
            <div id="_chartsMsgVazio" class="texto-fraco">Selecione um membro para ver os detalhes.</div>

            <!-- Header (compartilhado) -->
            <div id="_chartsHeader" class="d-none">
              <div class="perfil-usuario-header mb-3">
                <div class="flex-grow-1">
                  <h5 class="mb-1 fw-bold" id="_tituloSecao"></h5>
                  <div class="texto-fraco small" id="_subtituloSecao"></div>
                </div>
              </div>
              <hr class="separador-sutil">
            </div>

            <!-- Seção comparativo (só equipe) -->
            <div id="_secaoComparativo" class="d-none mb-4">
              <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Tempo por membro</div>
              <div id="chartGlobalComparativo" class="grafico-container" style="height:200px"></div>
            </div>

            <!-- Seção apps: donut + legenda + barras (barras só individual) -->
            <div id="_secaoApps" class="d-none mb-4">
              <div class="row g-3">
                <div id="_colDonut" class="col-12 col-xl-5">
                  <div class="texto-fraco small fw-semibold mb-2" id="_tituloApps" style="text-transform:uppercase;letter-spacing:.3px"></div>
                  <div class="d-flex flex-wrap flex-md-nowrap gap-3 align-items-start">
                    <div id="chartGlobalApps" class="grafico-container" style="flex:1;min-width:180px;height:300px"></div>
                    <div id="legendaGlobalApps" class="legenda-lateral-apps"></div>
                  </div>
                </div>
                <div id="_colBarras" class="col-12 col-xl-7 d-none">
                  <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Todos os programas — foco vs 2.º plano</div>
                  <div id="chartBarrasApps" class="grafico-container" style="height:300px"></div>
                </div>
              </div>
            </div>

            <!-- Seção timeline (compartilhada) -->
            <div id="_secaoTimeline" class="d-none mb-3">
              <div class="d-flex align-items-center justify-content-between mb-2">
                <div class="texto-fraco small fw-semibold" id="_tituloTimeline" style="text-transform:uppercase;letter-spacing:.3px"></div>
                <div class="d-flex align-items-center gap-2">
                  <button id="btnTeamTimelineDiaAnterior" class="btn btn-sm btn-outline-light botao-mini" style="padding:2px 10px;font-size:.85rem" title="Dia anterior">&larr;</button>
                  <span id="teamTimelineDiaLabel" class="fw-semibold" style="min-width:120px;text-align:center;font-size:.88rem">—</span>
                  <button id="btnTeamTimelineDiaProximo" class="btn btn-sm btn-outline-light botao-mini" style="padding:2px 10px;font-size:.85rem" title="Próximo dia">&rarr;</button>
                </div>
              </div>
              <div id="_labelEmFoco" class="d-none texto-fraco small mb-1" style="opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:.3px">Em foco</div>
              <div class="chart-shimmer-wrapper" id="_shimmerTimeline">
                <div id="chartGlobalTimeline" class="grafico-container" style="height:200px"></div>
              </div>
              <div id="_wrapperTimelineAbertos" class="d-none mt-3">
                <div class="texto-fraco small mb-1" style="opacity:.55;font-size:.75rem;text-transform:uppercase;letter-spacing:.3px">Todos os apps abertos (foco + 2.º plano)</div>
                <div class="chart-shimmer-wrapper" id="_shimmerAbertos">
                  <div id="chartTimelineAbertos" class="grafico-container" style="height:200px"></div>
                </div>
              </div>
            </div>

          </div>
        </div>

        <!-- Tempo declarado -->
        <div class="cartao-grafite p-3 secao-graficos">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <div>
              <h6 class="mb-0 fw-bold">Tempo Declarado</h6>
              <div class="texto-fraco small mt-1">Apenas o tempo que o membro declarou como trabalhado</div>
            </div>
            <span class="badge badge-suave">declarado</span>
          </div>
          <div class="row g-3 mb-3" id="cardsDeclarado">
            <div class="col-6 col-md-2"><div class="card-metrica"><div class="card-metrica__rotulo">Total declarado</div><div class="card-metrica__valor texto-mono" id="declTotalHoras">—</div></div></div>
            <div class="col-6 col-md-2"><div class="card-metrica"><div class="card-metrica__rotulo">Pagamento Pendente</div><div class="card-metrica__valor text-warning" id="declTotalValor">—</div></div></div>
            <div class="col-6 col-md-2"><div class="card-metrica"><div class="card-metrica__rotulo">Pago</div><div class="card-metrica__valor text-success" id="declTotalPago">—</div></div></div>
            <div class="col-6 col-md-2"><div class="card-metrica"><div class="card-metrica__rotulo">Membros</div><div class="card-metrica__valor" id="declTotalEditores">—</div></div></div>
            <div class="col-6 col-md-4"><div class="card-metrica"><div class="card-metrica__rotulo">Período</div><div class="card-metrica__valor" style="font-size:1rem" id="declPeriodo">—</div></div></div>
          </div>
          <div id="areaDeclaradoPorUsuario"><div class="texto-fraco small">Carregando…</div></div>
        </div>

      </div>
    `;
  }

  // ─── Filtros ───────────────────────────────────────────────
  function garantirDatasPadrao() {
    const fim = document.getElementById("filtroGraficosDataFim");
    const ini = document.getElementById("filtroGraficosDataInicio");
    if (!fim || !ini) return;
    if (!fim.value) fim.value = obterDataHojeIso();
    if (!ini.value) ini.value = obterDataHojeIso();
  }

  function obterFiltros() {
    const userId = (document.getElementById("filtroGraficosUsuarioDetalhe") || {}).value || "";

    if (foiAplicadoManualmente) {
      // Usa exatamente o que está nos inputs
      garantirDatasPadrao();
      return {
        data_inicio: (document.getElementById("filtroGraficosDataInicio") || {}).value || "",
        data_fim:    (document.getElementById("filtroGraficosDataFim")    || {}).value || "",
        usuarios: userId ? [userId] : [],
        apps: [],
        usuario_detalhe: userId,
      };
    }

    // Sem filtro manual: mostra apenas o dia atual (tanto na visão geral quanto ao filtrar por membro)
    const hoje = obterDataHojeIso();
    return {
      data_inicio: hoje,
      data_fim: hoje,
      usuarios: userId ? [userId] : [],
      apps: [],
      usuario_detalhe: userId,
    };
  }

  function preencherSelect(id, itens, valKey, txtKey) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = "";
    (itens || []).forEach(item => {
      const v = String(item[valKey] ?? ""), t = String(item[txtKey] ?? v);
      if (!v) return;
      const opt = document.createElement("option");
      opt.value = v; opt.textContent = t;
      el.appendChild(opt);
    });
  }

  async function carregarMetaFiltros() {
    if (metaCarregada) return;
    const dados = await requisitarJson(urlApiGraficos, { acao: "meta" });
    const usuarios = (dados.usuarios || []).map(u => ({
      user_id: String(u.user_id || ""),
      texto: `${u.nome_exibicao || u.user_id || "—"}`
    })).filter(u => u.user_id);

    const sel = document.getElementById("filtroGraficosUsuarioDetalhe");
    if (sel) {
      sel.innerHTML = `<option value="">— Todos (visão geral da equipe) —</option>`;
      usuarios.forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.user_id; opt.textContent = u.texto;
        sel.appendChild(opt);
      });
    }
    metaCarregada = true;
  }

  // ─── Montar resumo geral ──────────────────────────────────
  function setTexto(id, txt) { const el = document.getElementById(id); if (el) el.textContent = txt; }

  // Retorna o dia selecionado na timeline da equipe, ou null quando mostra o período inteiro
  function _diaRecorteEquipe() {
    if (_modoTotalPeriodo) return null;
    return _teamTimelineDias[_teamTimelineIdxDia] || null;
  }

  // Tempos globais considerando o recorte atual (dia selecionado ou período inteiro)
  function _temposGlobaisNoRecorte(dados) {
    const r = dados.resumo_geral || {};
    const dia = _diaRecorteEquipe();
    if (!dia) {
      return {
        segundos_trabalhando: r.segundos_trabalhando_total || 0,
        segundos_ocioso: r.segundos_ocioso_total || 0,
        segundos_pausado: r.segundos_pausado_total || 0,
      };
    }
    const t = (r.tempos_por_dia || {})[dia] || {};
    return {
      segundos_trabalhando: t.segundos_trabalhando || 0,
      segundos_ocioso: t.segundos_ocioso || 0,
      segundos_pausado: t.segundos_pausado || 0,
    };
  }

  // Tempos de um usuário considerando o recorte atual (dia ou período inteiro)
  function _temposUsuarioNoRecorte(usuario) {
    const dia = _diaRecorteEquipe();
    if (!dia) {
      return {
        segundos_trabalhando: usuario.segundos_trabalhando_total || 0,
        segundos_ocioso: usuario.segundos_ocioso_total || 0,
        segundos_pausado: usuario.segundos_pausado_total || 0,
      };
    }
    const t = (usuario.tempos_por_dia || {})[dia] || {};
    return {
      segundos_trabalhando: t.segundos_trabalhando || 0,
      segundos_ocioso: t.segundos_ocioso || 0,
      segundos_pausado: t.segundos_pausado || 0,
    };
  }

  function montarResumo(dados) {
    const r = dados.resumo_geral || {};
    const st = r.status_atual || {};
    setTexto("numeroResumoTrabalhandoAgora", String(st.trabalhando || 0));
    setTexto("numeroResumoOciososAgora", String(st.ocioso || 0));
    setTexto("numeroResumoPausadosAgora", String(st.pausado || 0));
    const t = _temposGlobaisNoRecorte(dados);
    setTexto("textoResumoTempoTrabalhando", hhmmss(t.segundos_trabalhando));
    setTexto("textoResumoTempoOcioso", hhmmss(t.segundos_ocioso));
    setTexto("textoResumoTempoPausado", hhmmss(t.segundos_pausado));
  }

  // ─── Tabela da equipe ─────────────────────────────────────
  function montarTabelaUsuarios(dados) {
    const tbody = document.getElementById("tbodyResumoUsuariosGraficos");
    if (!tbody) return;
    const usuarios = dados.usuarios || [];
    setTexto("textoTotalUsuarios", `${usuarios.length} membro${usuarios.length !== 1 ? "s" : ""}`);

    if (!usuarios.length) {
      tbody.innerHTML = `<tr><td colspan="10" class="texto-fraco">Sem dados para este período.</td></tr>`;
      return;
    }

    tbody.innerHTML = usuarios.map(u => {
      const nome = escaparHtml(u.nome_exibicao || u.user_id || "—");
      const uid = escaparHtml(u.user_id || "");
      const status = u.status_atual || "sem_status";
      const ativ = escaparHtml(String(u.atividade_atual || "").trim() || "—");
      const app = escaparHtml(u.app_principal || "—");
      const tu = _temposUsuarioNoRecorte(u);

      return `<tr>
        <td>
          <div class="d-flex align-items-center gap-2">
            <div class="perfil-avatar" style="width:32px;height:32px;font-size:.75rem;border-radius:8px">${iniciais(u.nome_exibicao || u.user_id)}</div>
            <div>
              <div class="fw-semibold" style="font-size:.88rem">${nome}</div>
              <div class="texto-fraco" style="font-size:.72rem">${uid}</div>
            </div>
          </div>
        </td>
        <td><span class="indicador-status ${classeStatus(status)}">${textoStatus(status)}</span></td>
        <td class="texto-fraco" style="font-size:.85rem;max-width:180px" title="${ativ}"><div class="text-truncate">${ativ}</div></td>
        <td style="font-size:.85rem">${app !== "—" ? `<span class="pill-app"><span class="pill-app__dot"></span>${app}</span>` : '<span class="texto-fraco">—</span>'}</td>
        <td class="text-center"><span class="badge ${(u.status_conta||"").toLowerCase() === "ativa" ? "text-bg-success" : "text-bg-secondary"}">${escaparHtml((u.status_conta||"—").charAt(0).toUpperCase() + (u.status_conta||"").slice(1))}</span></td>
        <td class="text-end fw-semibold" style="font-size:.85rem">R$ ${Number(u.valor_hora || 0).toFixed(2).replace(".",",")}</td>
        <td class="text-end texto-mono text-success" style="font-size:.85rem">${hhmmss(tu.segundos_trabalhando)}</td>
        <td class="text-end texto-mono text-warning" style="font-size:.85rem">${hhmmss(tu.segundos_ocioso)}</td>
        <td class="text-end">${Number(u.quantidade_apps_usados || 0)}</td>
        <td class="text-end"><button class="btn btn-sm btn-outline-light" type="button" data-gestao-uid="${uid}">Gestão</button></td>
      </tr>`;
    }).join("");

    // Event delegation para botão Gestão
    tbody.onclick = (e) => {
      const btn = e.target.closest("button[data-gestao-uid]");
      if (btn) window.PainelAbaUsuarios?.abrirModalGestaoUsuario?.(btn.dataset.gestaoUid);
    };
  }

  // ─── Gráficos ECharts ─────────────────────────────────────

  function criarOuObterChart(containerId, minH) {
    let el = document.getElementById(containerId);
    if (!el) return null;
    el.style.minHeight = (minH || 280) + "px";
    const existente = echarts.getInstanceByDom(el);
    if (existente) return existente;
    return echarts.init(el, null, { renderer: "canvas" });
  }

  function renderizarBarrasApps(usuario) {
    const chart = criarOuObterChart("chartBarrasApps", 260);
    if (!chart) return;

    // Calcular a partir de periodos_abertos clipados no dia/período
    let bIniMs, bFimMs;
    if (_modoTotalPeriodo) {
      const ini = (document.getElementById("filtroGraficosDataInicio") || {}).value || obterDataHojeIso();
      const fim = (document.getElementById("filtroGraficosDataFim") || {}).value || obterDataHojeIso();
      bIniMs = new Date(ini + "T00:00:00").getTime();
      bFimMs = new Date(fim + "T23:59:59.999").getTime();
    } else {
      const dia = _teamTimelineDias[_teamTimelineIdxDia] || obterDataHojeIso();
      bIniMs = new Date(dia + "T00:00:00").getTime();
      bFimMs = new Date(dia + "T23:59:59.999").getTime();
    }

    const mapaFoco = {};
    const mapaBg = {};
    (usuario.periodos_abertos || []).forEach(p => {
      if (!p.inicio_em) return;
      const ini = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
      const fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
      if (ini > bFimMs || fim < bIniMs) return;
      const nome = p.nome_app || "—";
      const clipIni = Math.max(ini, bIniMs);
      const clipFim = Math.min(fim, bFimMs);
      const durTotal = Math.max(1, fim - ini);
      const fator = Math.max(0, Math.min(1, (clipFim - clipIni) / durTotal));
      const segFoco = Math.max(0, Math.round((p.segundos_em_foco || 0) * fator));
      const segBg   = Math.max(0, Math.round((p.segundos_segundo_plano || 0) * fator));
      mapaFoco[nome] = (mapaFoco[nome] || 0) + segFoco;
      mapaBg[nome]   = (mapaBg[nome]   || 0) + segBg;
    });

    const apps = Object.keys(mapaFoco).map(nome => ({
      nome_app: nome,
      segundos_em_foco: mapaFoco[nome] || 0,
      segundos_segundo_plano: mapaBg[nome] || 0,
    })).sort((a, b) => (b.segundos_em_foco + b.segundos_segundo_plano) - (a.segundos_em_foco + a.segundos_segundo_plano)).slice(0, 10);

    if (!apps.length) { chart.clear(); return; }

    const nomes = apps.map(a => a.nome_app || "—").reverse();
    const foco = apps.map(a => a.segundos_em_foco || 0).reverse();
    const bg = apps.map(a => a.segundos_segundo_plano || 0).reverse();

    chart.setOption({
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (params) => {
          const nome = params[0]?.axisValue || "";
          let html = `<strong>${escaparHtml(nome)}</strong>`;
          params.forEach(p => { html += `<br/>${p.marker} ${p.seriesName}: ${hhmm(p.value)}`; });
          return html;
        },
      },
      legend: {
        data: ["Em foco", "2.º plano"],
        textStyle: { color: "rgba(255,255,255,.65)", fontSize: 12 },
        top: 0,
      },
      grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: "value", axisLabel: { color: "rgba(255,255,255,.4)", formatter: v => hhmm(v) }, splitLine: { lineStyle: { color: "rgba(255,255,255,.06)" } } },
      yAxis: { type: "category", data: nomes, axisLabel: { color: "rgba(255,255,255,.7)", fontSize: 11, width: 120, overflow: "truncate" }, axisTick: { show: false }, axisLine: { show: false } },
      series: [
        { name: "Em foco", type: "bar", stack: "total", data: foco, itemStyle: { color: "#6366f1", borderRadius: [0,0,0,0] }, barMaxWidth: 18 },
        { name: "2.º plano", type: "bar", stack: "total", data: bg, itemStyle: { color: "rgba(99,102,241,.25)", borderRadius: [0,3,3,0] }, barMaxWidth: 18 },
      ],
    }, true);
  }

  // Último payload completo da API — usado pelo modal de cores
  let _dadosPainelAtual = null;

  // Estado do filtro manual (seção 23)
  let foiAplicadoManualmente = false;
  let FILTROS_APPS_ATIVOS = [];

  // Estado da team timeline (visão global)
  let _teamTimelineDias = [];
  let _teamTimelineIdxDia = 0;
  let _teamTimelineUsuarios = null;

  // Controle de modo — evita rebuild de HTML a cada filtro
  let _htmlModoAtual = null; // "individual" | "equipe" | null

  // Estado da timeline geral (todos os apps abertos — foco + 2.º plano)
  let _timelineAbertosDias = [];
  let _timelineAbertosIdxDia = 0;
  let _timelineAbertosUsuario = null;

  function _extrairDiaIso(datetimeStr) {
    const m = String(datetimeStr || "").match(/^(\d{4}-\d{2}-\d{2})/);
    return m ? m[1] : null;
  }

  function _formatarDiaBr(iso) {
    const p = iso.split("-");
    if (p.length !== 3) return iso;
    const d = new Date(+p[0], +p[1]-1, +p[2]);
    const semana = d.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".","").toUpperCase();
    return `${semana} ${p[2]}/${p[1]}`;
  }

  let _modoTotalPeriodo = false; // true quando filtro tem múltiplos dias

  // Clipa sobreposições: dentro de cada lane (value[0]), ordena por início e corta
  // cada período onde o seguinte começa — sem sobreposição, sem redundância.
  // Remove períodos "fantasma" — mantém apenas o mais recente por app quando fim_em é vazio
  function _limparPeriodosFantasma(periodos) {
    const abertoPorApp = {};
    // Primeiro, encontrar o período aberto mais recente por app
    periodos.forEach(p => {
      if (p.fim_em) return; // tem fim, não é fantasma
      const app = p.nome_app || "—";
      const ini = new Date(String(p.inicio_em || "").replace(" ", "T")).getTime();
      if (!abertoPorApp[app] || ini > abertoPorApp[app]) {
        abertoPorApp[app] = ini;
      }
    });
    // Filtrar: manter períodos com fim, e sem fim apenas o mais recente por app
    return periodos.filter(p => {
      if (p.fim_em) return true;
      const app = p.nome_app || "—";
      const ini = new Date(String(p.inicio_em || "").replace(" ", "T")).getTime();
      return ini === abertoPorApp[app];
    });
  }

  // Calcula segundos não-sobrepostos de periodos_foco dentro de uma janela.
  // Foco é exclusivo (1 janela por vez) — períodos fantasma de apps diferentes
  // se sobrepõem quando clipados ao mesmo dia; mesclar evita contagem dupla.
  function _segundosFocoMesclados(periodos, cIniMs, cFimMs) {
    const clips = [];
    _limparPeriodosFantasma(periodos).forEach(p => {
      if (!p.inicio_em) return;
      const ini = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
      const fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
      if (ini <= cFimMs && fim >= cIniMs) {
        clips.push([Math.max(ini, cIniMs), Math.min(fim, cFimMs)]);
      }
    });
    clips.sort((a, b) => a[0] - b[0]);
    let total = 0, curEnd = 0;
    clips.forEach(([s, e]) => {
      if (s >= curEnd) { total += e - s; curEnd = e; }
      else if (e > curEnd) { total += e - curEnd; curEnd = e; }
    });
    return Math.max(0, Math.round(total / 1000));
  }

  function _cliparSobreposicoes(dados) {
    const porLane = {};
    dados.forEach(d => {
      const lane = d.value[0];
      (porLane[lane] = porLane[lane] || []).push(d);
    });
    const resultado = [];
    Object.values(porLane).forEach(grupo => {
      grupo.sort((a, b) => a.value[1] - b.value[1]);
      for (let i = 0; i < grupo.length; i++) {
        const d = grupo[i];
        const ini = d.value[1];
        const fim = (i + 1 < grupo.length && grupo[i + 1].value[1] < d.value[2])
          ? grupo[i + 1].value[1]
          : d.value[2];
        if (fim > ini) resultado.push({ ...d, value: [d.value[0], ini, fim, ...d.value.slice(3)] });
      }
    });
    return resultado;
  }

  function _extrairDiasAbrangidos(inicioStr, fimStr) {
    // Retorna todos os dias (YYYY-MM-DD) que um período toca
    const dias = [];
    const inicio = inicioStr ? new Date(String(inicioStr).replace(" ", "T")) : null;
    const fim = fimStr ? new Date(String(fimStr).replace(" ", "T")) : new Date();
    if (!inicio || isNaN(inicio.getTime())) return dias;
    if (isNaN(fim.getTime())) return dias;

    const d = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate());
    const fimDia = new Date(fim.getFullYear(), fim.getMonth(), fim.getDate());
    while (d <= fimDia) {
      dias.push(d.toISOString().slice(0, 10));
      d.setDate(d.getDate() + 1);
    }
    return dias;
  }

  function _gerarDiasContiguos(dataInicio, dataFim) {
    // Gera todos os dias de dataInicio até dataFim (inclusive), sem pular
    const dias = [];
    const d = new Date(dataInicio + "T00:00:00");
    const fim = new Date(dataFim + "T00:00:00");
    if (isNaN(d.getTime()) || isNaN(fim.getTime())) return dias;
    while (d <= fim) {
      dias.push(d.toISOString().slice(0, 10));
      d.setDate(d.getDate() + 1);
    }
    return dias;
  }

  // ─── Visão Global (todos os usuários) ─────────────────────

  // ─── Timeline Geral (todos os apps abertos: foco + 2.º plano) ─────────────

  function _atualizarLabelTimelineAbertos() {
    const label = document.getElementById("timelineAbertosLabel");
    if (!label || !_timelineAbertosDias.length) return;
    label.textContent = _formatarDiaBr(_timelineAbertosDias[_timelineAbertosIdxDia]);
    const btnAnt  = document.getElementById("btnTimelineAbertosDiaAnterior");
    const btnProx = document.getElementById("btnTimelineAbertosDiaProximo");
    if (btnAnt)  btnAnt.disabled  = _timelineAbertosIdxDia >= _timelineAbertosDias.length - 1;
    if (btnProx) btnProx.disabled = _timelineAbertosIdxDia <= 0;
  }

  function renderizarTimelineAbertosDoDia() {
    const chart = criarOuObterChart("chartTimelineAbertos", 200);
    if (!chart || !_timelineAbertosUsuario) return;

    // v4.6: usa o controle unificado de dias (mesmo _teamTimelineDias/_teamTimelineIdxDia)
    const diaSelecionado = _teamTimelineDias[_teamTimelineIdxDia];
    if (!diaSelecionado) { chart.clear(); return; }

    const diaInicioMs = new Date(diaSelecionado + "T00:00:00").getTime();
    const diaFimMs    = new Date(diaSelecionado + "T23:59:59.999").getTime();

    // Considera qualquer período que sobreponha o dia selecionado (mesma regra da timeline principal)
    const periodos = (_timelineAbertosUsuario.periodos_abertos || [])
      .filter(p => {
        if (!p.inicio_em) return false;
        const ini = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
        const fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
        return !isNaN(ini) && ini <= diaFimMs && fim >= diaInicioMs;
      })
      .filter(p => FILTROS_APPS_ATIVOS.length === 0 || FILTROS_APPS_ATIVOS.includes(p.nome_app || "—"));

    if (!periodos.length) {
      chart.clear();
      chart.setOption({ title: { text: "Sem atividade neste dia", left: "center", top: "center", textStyle: { color: "rgba(255,255,255,.3)", fontSize: 14 } } }, true);
      return;
    }

    const appsUnicos = [...new Set(periodos.map(p => p.nome_app || "—"))];

    // Clipa cada período às fronteiras 00:00:00 → 23:59:59 do dia selecionado
    const dados = _cliparSobreposicoes(
      periodos.map(p => {
        const app    = p.nome_app || "—";
        const iniMs  = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
        const fimOrig = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
        const inicio = Math.max(iniMs, diaInicioMs);
        const fim    = Math.min(isNaN(fimOrig) ? Date.now() : fimOrig, diaFimMs);
        // value[3] é a duração do trecho clipado — tooltip precisa refletir só o que aparece neste dia
        const segsClipados = Math.max(0, Math.round((fim - inicio) / 1000));
        return {
          name: app,
          value: [app, inicio, fim, segsClipados],
          itemStyle: { color: _obterCorApp(app) },
        };
      }).filter(d => !isNaN(d.value[1]) && d.value[2] > d.value[1])
    );

    if (!dados.length) { chart.clear(); return; }

    // Eixo X fixo nos limites do dia/período — cobre 00:00:00 até 23:59:59 mesmo sem dados
    const xMin = diaInicioMs;
    const xMax = diaFimMs;

    const alturaChart = Math.max(120, Math.min(400, appsUnicos.length * 36 + 60));
    const el = document.getElementById("chartTimelineAbertos");
    if (el) el.style.height = alturaChart + "px";
    chart.resize();

    chart.setOption({
      tooltip: {
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (p) => {
          const v = p.value;
          const ini = new Date(v[1]).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
          const f   = new Date(v[2]).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
          return `<strong>${escaparHtml(v[0])}</strong><br/>${ini} → ${f}<br/>Total aberto: ${hhmm(v[3])}`;
        },
      },
      grid: { left: 8, right: 16, top: 8, bottom: 32, containLabel: true },
      xAxis: {
        type: "time", min: xMin, max: xMax,
        minInterval: 15 * 60 * 1000, maxInterval: 2 * 3600 * 1000,
        axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 11, formatter: (v) => new Date(v).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) },
        splitLine: { lineStyle: { color: "rgba(255,255,255,.04)" } },
      },
      yAxis: { type: "category", data: appsUnicos, axisLabel: { color: "rgba(255,255,255,.7)", fontSize: 11, width: 100, overflow: "truncate" }, axisTick: { show: false }, axisLine: { show: false } },
      series: [{
        type: "custom",
        renderItem: (params, api) => {
          const catIdx = api.value(0);
          const inicio = api.coord([api.value(1), catIdx]);
          const fim    = api.coord([api.value(2), catIdx]);
          const bandH  = Math.min(api.size([0, 1])[1] * 0.6, 18); // v4.8: máx 18px
          return {
            type: "rect",
            shape: { x: inicio[0], y: inicio[1] - bandH / 2, width: Math.max(fim[0] - inicio[0], 2), height: bandH },
            style: { ...api.style(), fill: api.visual("color") },
            styleEmphasis: { ...api.style(), opacity: 1 },
          };
        },
        encode: { x: [1, 2], y: 0 },
        data: dados,
      }],
    }, true);
  }

  function renderizarTimelineAbertos(usuario) {
    // v4.6: dias geridos pelo controle unificado (_teamTimelineDias/_teamTimelineIdxDia)
    _timelineAbertosUsuario = usuario;
    renderizarTimelineAbertosDoDia();
  }

  function renderizarComparativoUsuarios(usuarios) {
    const chart = criarOuObterChart("chartGlobalComparativo", 260);
    if (!chart) return;
    if (!usuarios.length) { chart.clear(); return; }

    const nomes = usuarios.map(u => u.nome_exibicao || u.user_id || "—").reverse();
    // Trabalhado líquido vem de cronometro_relatorios.segundos_trabalhando no recorte atual
    // (mesma fonte de Ocioso/Pausado) para manter a decomposição coerente: T + O + P = tempo cronometrado.
    const trabalhando = usuarios.map(u => _temposUsuarioNoRecorte(u).segundos_trabalhando).reverse();
    const ocioso = usuarios.map(u => _temposUsuarioNoRecorte(u).segundos_ocioso).reverse();
    const pausado = usuarios.map(u => _temposUsuarioNoRecorte(u).segundos_pausado).reverse();

    chart.setOption({
      tooltip: {
        trigger: "axis",
        axisPointer: { type: "shadow" },
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (params) => {
          const nome = params[0]?.axisValue || "";
          let html = `<strong>${escaparHtml(nome)}</strong>`;
          params.forEach(p => { html += `<br/>${p.marker} ${p.seriesName}: ${hhmm(p.value)}`; });
          return html;
        },
      },
      legend: {
        data: ["Trabalhado", "Ocioso", "Pausado"],
        textStyle: { color: "rgba(255,255,255,.65)", fontSize: 12 },
        top: 0,
      },
      grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
      xAxis: { type: "value", axisLabel: { color: "rgba(255,255,255,.4)", formatter: v => hhmm(v) }, splitLine: { lineStyle: { color: "rgba(255,255,255,.06)" } } },
      yAxis: { type: "category", data: nomes, axisLabel: { color: "rgba(255,255,255,.7)", fontSize: 11, width: 120, overflow: "truncate" }, axisTick: { show: false }, axisLine: { show: false } },
      series: [
        { name: "Trabalhado", type: "bar", stack: "total", data: trabalhando, itemStyle: { color: "#34d399" }, barMaxWidth: 22 },
        { name: "Ocioso", type: "bar", stack: "total", data: ocioso, itemStyle: { color: "#fbbf24" }, barMaxWidth: 22 },
        { name: "Pausado", type: "bar", stack: "total", data: pausado, itemStyle: { color: "rgba(99,102,241,.35)", borderRadius: [0,3,3,0] }, barMaxWidth: 22 },
      ],
    }, true);
  }

  function renderizarGlobalApps(usuarios) {
    const chart = criarOuObterChart("chartGlobalApps", 300);
    if (!chart) return;

    // Usa periodos_foco filtrado pelo dia/período atual
    let gIniMs, gFimMs;
    if (_modoTotalPeriodo) {
      const ini = (document.getElementById("filtroGraficosDataInicio") || {}).value || obterDataHojeIso();
      const fim = (document.getElementById("filtroGraficosDataFim") || {}).value || obterDataHojeIso();
      gIniMs = new Date(ini + "T00:00:00").getTime();
      gFimMs = new Date(fim + "T23:59:59.999").getTime();
    } else {
      const diaSelecionado = _teamTimelineDias[_teamTimelineIdxDia] || obterDataHojeIso();
      gIniMs = new Date(diaSelecionado + "T00:00:00").getTime();
      gFimMs = new Date(diaSelecionado + "T23:59:59.999").getTime();
    }
    const mapaApps = {};
    usuarios.forEach(u => {
      _limparPeriodosFantasma(u.periodos_foco || [])
        .filter(p => {
          if (!p.inicio_em) return false;
          const ini = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
          const fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
          return ini <= gFimMs && fim >= gIniMs;
        })
        .forEach(p => {
          const nome = p.nome_app || "—";
          const ini = Math.max(new Date(String(p.inicio_em).replace(" ", "T")).getTime(), gIniMs);
          const fim = Math.min(p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now(), gFimMs);
          mapaApps[nome] = (mapaApps[nome] || 0) + Math.max(0, Math.round((fim - ini) / 1000));
        });
    });

    const todosApps = Object.entries(mapaApps)
      .map(([nome, seg]) => ({ nome, seg }))
      .sort((a, b) => b.seg - a.seg)
      .slice(0, 12);

    if (!todosApps.length) { chart.clear(); return; }

    // Filtra apenas o dado do gráfico; a legenda sempre exibe todos
    const appsGrafico = FILTROS_APPS_ATIVOS.length > 0
      ? todosApps.filter(a => FILTROS_APPS_ATIVOS.includes(a.nome))
      : todosApps;

    const dados = appsGrafico.map((a) => ({
      name: a.nome,
      value: a.seg,
      itemStyle: { color: _obterCorApp(a.nome) },
    }));

    chart.setOption({
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 13 },
        formatter: (p) => `<strong>${escaparHtml(p.name)}</strong><br/>Foco total: ${hhmm(p.value)}<br/>${p.percent?.toFixed(1)}%`,
      },
      legend: { show: false },
      series: [{
        type: "pie", radius: ["48%", "74%"], center: ["50%", "50%"],
        avoidLabelOverlap: true, padAngle: 2,
        itemStyle: { borderRadius: 6, borderColor: "rgba(11,18,32,.8)", borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: "bold", color: "#fff" },
          itemStyle: { shadowBlur: 20, shadowColor: "rgba(99,102,241,.4)" },
        },
        data: dados,
      }],
    }, true);

    chart.off("click");
    chart.on("click", (params) => { if (params.name) alternarFiltroApp(params.name); });

    // Legenda usa todosApps (todos os apps, não só os filtrados)
    _renderizarLegendaLateral(todosApps.map(a => ({ nome: a.nome })), "legendaGlobalApps");
  }

  function _atualizarLabelTeamTimeline() {
    const label = document.getElementById("teamTimelineDiaLabel");
    const btnAnt = document.getElementById("btnTeamTimelineDiaAnterior");
    const btnProx = document.getElementById("btnTeamTimelineDiaProximo");
    if (!label) return;

    if (_modoTotalPeriodo) {
      const ini = (document.getElementById("filtroGraficosDataInicio") || {}).value || "";
      const fim = (document.getElementById("filtroGraficosDataFim") || {}).value || "";
      label.textContent = `${_formatarDiaBr(ini)} → ${_formatarDiaBr(fim)}`;
      if (btnAnt) btnAnt.disabled = true;
      if (btnProx) btnProx.disabled = true;
      return;
    }

    if (!_teamTimelineDias.length) {
      label.textContent = "—";
      if (btnAnt) btnAnt.disabled = true;
      if (btnProx) btnProx.disabled = true;
      return;
    }
    const diaAtual = _teamTimelineDias[_teamTimelineIdxDia] || "";
    label.textContent = _formatarDiaBr(diaAtual);
    if (btnAnt) btnAnt.disabled = _teamTimelineIdxDia >= _teamTimelineDias.length - 1;
    if (btnProx) btnProx.disabled = _teamTimelineIdxDia <= 0 || diaAtual >= obterDataHojeIso();
  }

  function _renderizarTeamTimelineDoDia() {
    const chart = criarOuObterChart("chartGlobalTimeline", 200);
    if (!chart || !_teamTimelineUsuarios) return;

    let diaInicioMs, diaFimMs;

    if (_modoTotalPeriodo) {
      const ini = (document.getElementById("filtroGraficosDataInicio") || {}).value || obterDataHojeIso();
      const fim = (document.getElementById("filtroGraficosDataFim") || {}).value || obterDataHojeIso();
      diaInicioMs = new Date(ini + "T00:00:00").getTime();
      diaFimMs = new Date(fim + "T23:59:59.999").getTime();
    } else {
      const diaSelecionado = _teamTimelineDias[_teamTimelineIdxDia];
      if (!diaSelecionado) { chart.clear(); return; }
      diaInicioMs = new Date(diaSelecionado + "T00:00:00").getTime();
      diaFimMs = new Date(diaSelecionado + "T23:59:59.999").getTime();
    }

    const userNomes = [];
    const dados = [];

    _teamTimelineUsuarios.forEach((u) => {
      const nome = u.nome_exibicao || u.user_id || "—";
      if (!userNomes.includes(nome)) userNomes.push(nome);

      _limparPeriodosFantasma(u.periodos_foco || [])
        .filter(p => {
          if (!p.inicio_em) return false;
          const ini = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
          const fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
          return ini <= diaFimMs && fim >= diaInicioMs;
        })
        .filter(p => FILTROS_APPS_ATIVOS.length === 0 || FILTROS_APPS_ATIVOS.includes(p.nome_app || "—"))
        .forEach(p => {
          let inicio = new Date(String(p.inicio_em).replace(" ", "T")).getTime();
          let fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")).getTime() : Date.now();
          inicio = Math.max(inicio, diaInicioMs);
          fim = Math.min(fim, diaFimMs);
          if (!isNaN(inicio) && fim > inicio) {
            dados.push({
              name: p.nome_app || "—",
              value: [nome, inicio, fim, Math.round((fim - inicio) / 1000), p.nome_app || "—"],
              itemStyle: { color: _obterCorApp(p.nome_app) },
            });
          }
        });
    });

    if (!dados.length) {
      chart.clear();
      chart.setOption({ title: { text: "Sem atividade neste dia", left: "center", top: "center", textStyle: { color: "rgba(255,255,255,.3)", fontSize: 14 } } }, true);
      return;
    }

    const dadosClipados = _cliparSobreposicoes(dados);

    // Eixo X fixo nos limites do dia/período — cobre 00:00:00 até 23:59:59 mesmo sem dados
    const xMin = diaInicioMs;
    const xMax = diaFimMs;

    const alturaChart = Math.max(120, Math.min(400, userNomes.length * 48 + 60));
    const el = document.getElementById("chartGlobalTimeline");
    if (el) el.style.height = alturaChart + "px";
    chart.resize();

    // Linhas de meia-noite no modo período
    const markLines = [];
    if (_modoTotalPeriodo) {
      const dIni = new Date(diaInicioMs);
      const dFim = new Date(diaFimMs);
      const cursor = new Date(dIni.getFullYear(), dIni.getMonth(), dIni.getDate() + 1);
      while (cursor <= dFim) {
        markLines.push({
          xAxis: cursor.getTime(),
          label: { formatter: cursor.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }), color: "rgba(255,255,255,.5)", fontSize: 10, position: "start" },
          lineStyle: { color: "rgba(255,255,255,.15)", type: "dashed", width: 1 },
        });
        cursor.setDate(cursor.getDate() + 1);
      }
    }

    // Formato do eixo X: inclui dia se modo período
    const xLabelFmt = _modoTotalPeriodo
      ? (v) => new Date(v).toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
      : (v) => new Date(v).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    const xInterval = _modoTotalPeriodo ? 6 * 3600 * 1000 : 2 * 3600 * 1000;

    chart.setOption({
      tooltip: {
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (p) => {
          if (p.componentType === "markLine") return "";
          const v = p.value;
          const dtFmt = { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
          const ini = new Date(v[1]).toLocaleString("pt-BR", dtFmt);
          const f = new Date(v[2]).toLocaleString("pt-BR", dtFmt);
          return `<strong>${escaparHtml(v[0])}</strong><br/>${escaparHtml(v[4])}<br/>${ini} → ${f}<br/>Duração: ${hhmm(v[3])}`;
        },
      },
      grid: { left: 8, right: 16, top: 8, bottom: 36, containLabel: true },
      xAxis: {
        type: "time", min: xMin, max: xMax,
        minInterval: _modoTotalPeriodo ? 3600 * 1000 : 15 * 60 * 1000,
        maxInterval: xInterval,
        axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 10, formatter: xLabelFmt, rotate: _modoTotalPeriodo ? 30 : 0 },
        splitLine: { lineStyle: { color: "rgba(255,255,255,.04)" } },
      },
      yAxis: { type: "category", data: userNomes, axisLabel: { color: "rgba(255,255,255,.7)", fontSize: 11, width: 120, overflow: "truncate" }, axisTick: { show: false }, axisLine: { show: false } },
      series: [{
        type: "custom",
        renderItem: (params, api) => {
          const catIdx = api.value(0);
          const inicio = api.coord([api.value(1), catIdx]);
          const fim = api.coord([api.value(2), catIdx]);
          const bandH = Math.min(api.size([0, 1])[1] * 0.6, 18);
          return {
            type: "rect",
            shape: { x: inicio[0], y: inicio[1] - bandH / 2, width: Math.max(fim[0] - inicio[0], 2), height: bandH },
            style: { ...api.style(), fill: api.visual("color") },
            styleEmphasis: { ...api.style(), opacity: 1 },
          };
        },
        encode: { x: [1, 2], y: 0 },
        data: dadosClipados,
        markLine: markLines.length > 0 ? { silent: true, symbol: "none", data: markLines } : undefined,
      }],
    }, true);
  }

  function _mostrarOcultar(id, mostrar) {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("d-none", !mostrar);
  }

  function montarVisaoGeralTodosUsuarios(dados) {
    const area = document.getElementById("areaUsuarioSelecionadoGraficos");
    if (!area) return;

    const usuarios = dados.usuarios || [];
    if (!usuarios.length) {
      const elMsg = document.getElementById("_chartsMsgVazio");
      if (elMsg) elMsg.textContent = "Sem dados para o período selecionado.";
      _mostrarOcultar("_chartsMsgVazio", true);
      _mostrarOcultar("_chartsHeader", false);
      _mostrarOcultar("_secaoComparativo", false);
      _mostrarOcultar("_secaoApps", false);
      _mostrarOcultar("_secaoTimeline", false);
      const existente = document.getElementById("_resumoDetalhadoApps");
      if (existente) existente.remove();
      _htmlModoAtual = null;
      return;
    }

    const individual = usuarios.length === 1;
    const modo = individual ? "individual" : "equipe";
    const nome = individual ? (usuarios[0].nome_exibicao || usuarios[0].user_id || "—") : "";

    const tituloSecao = individual ? `Visão Geral: ${nome}` : "Visão Geral da Equipe";
    const tituloApps  = individual ? `Top apps de ${nome}` : "Top apps da equipe (foco agregado)";
    const tituloTL    = individual ? `Timelines de atividade` : "Timeline da equipe";

    // Mostrar seções, ocultar mensagem vazia
    _mostrarOcultar("_chartsMsgVazio", false);
    _mostrarOcultar("_chartsHeader", true);
    _mostrarOcultar("_secaoApps", true);
    _mostrarOcultar("_secaoTimeline", true);

    // Toggle seções por modo (sem destruir DOM)
    _mostrarOcultar("_secaoComparativo", !individual);
    _mostrarOcultar("_colBarras", individual);
    _mostrarOcultar("_labelEmFoco", individual);
    _mostrarOcultar("_wrapperTimelineAbertos", individual);

    // Ajustar colunas do donut: col-5 individual, col-12 equipe
    const colDonut = document.getElementById("_colDonut");
    if (colDonut) {
      colDonut.classList.toggle("col-xl-5", individual);
      colDonut.classList.toggle("col-xl-12", !individual);
    }

    // Ajustar altura do comparativo e timeline conforme quantidade de membros
    const elComp = document.getElementById("chartGlobalComparativo");
    if (elComp) elComp.style.height = Math.max(160, usuarios.length * 40 + 60) + "px";
    const elTL = document.getElementById("chartGlobalTimeline");
    if (elTL) elTL.style.height = Math.max(120, usuarios.length * 48 + 60) + "px";

    // Atualizar textos dinâmicos
    const elTitulo = document.getElementById("_tituloSecao");
    const elSub = document.getElementById("_subtituloSecao");
    const elApps = document.getElementById("_tituloApps");
    const elTLtitulo = document.getElementById("_tituloTimeline");
    if (elTitulo) elTitulo.textContent = tituloSecao;
    if (elSub) elSub.textContent = `${usuarios.length} membro${usuarios.length !== 1 ? "s" : ""} no período`;
    if (elApps) elApps.textContent = tituloApps;
    if (elTLtitulo) elTLtitulo.textContent = tituloTL;

    _htmlModoAtual = modo;
    _teamTimelineUsuarios = usuarios;
    // _teamTimelineDias / _teamTimelineIdxDia / _modoTotalPeriodo já foram recalculados
    // antes de montarResumo/montarTabelaUsuarios no atualizarGraficos — não refazer aqui.

    setTimeout(() => {
      if (individual) {
        renderizarGlobalApps(usuarios);
        renderizarBarrasApps(usuarios[0]);
        renderizarTimelineAbertos(usuarios[0]);
      } else {
        renderizarComparativoUsuarios(usuarios);
        renderizarGlobalApps(usuarios);
      }
      _atualizarLabelTeamTimeline();
      _renderizarTeamTimelineDoDia();

      // Remover shimmer após render
      document.querySelectorAll(".chart-shimmer-wrapper").forEach(el => el.classList.remove("chart-shimmer-wrapper"));

      // Resize charts após render (colunas podem ter mudado de largura ao alternar modo)
      setTimeout(() => resizarGraficos(), 80);
    }, 50);
  }

  // ─── Detalhe do usuário selecionado ───────────────────────
  // Sempre delega para montarVisaoGeralTodosUsuarios, que lida com
  // 1 membro (títulos dinâmicos) ou N membros (visão de equipe).
  // A API já filtra por usuário quando userId está definido.
  function montarDetalheUsuario(dados, userId) {
    const area = document.getElementById("areaUsuarioSelecionadoGraficos");
    if (!area) return;

    const usuarios = dados.usuarios || [];
    if (!usuarios.length) {
      montarVisaoGeralTodosUsuarios(dados); // oculta seções e mostra mensagem vazia
      return;
    }

    // Mesma função para equipe e individual — títulos se adaptam automaticamente
    montarVisaoGeralTodosUsuarios(dados);

    // Quando é um membro individual, adiciona tabela detalhada de apps ao final
    if (userId && usuarios[0]) {
      setTimeout(() => {
        const a = document.getElementById("areaUsuarioSelecionadoGraficos");
        if (!a) return;

        // Remover resumo anterior se existir
        const existente = document.getElementById("_resumoDetalhadoApps");
        if (existente) existente.remove();

        const u = usuarios[0];
        const status = u.status_atual || "sem_status";
        const appsAbertos = u.apps_abertos_agora || [];
        const wrapper = document.createElement("div");
        wrapper.id = "_resumoDetalhadoApps";
        wrapper.innerHTML = `
          <div class="perfil-usuario-header mt-3">
            <div class="perfil-avatar">${iniciais(u.nome_exibicao || u.user_id)}</div>
            <div class="flex-grow-1">
              <div class="d-flex flex-wrap align-items-center gap-2">
                <span class="fw-semibold">${escaparHtml(u.user_id || "")}</span>
                <span class="indicador-status ${classeStatus(status)}">${textoStatus(status)}</span>
              </div>
              <div class="texto-fraco small">${escaparHtml(String(u.atividade_atual || "").trim() || "Sem atividade")}</div>
            </div>
            ${appsAbertos.length ? `<div class="d-flex flex-wrap gap-2">${appsAbertos.map(ap => `<span class="pill-app"><span class="pill-app__dot"></span>${escaparHtml(ap.nome_app || "—")}</span>`).join("")}</div>` : ""}
          </div>
          <hr class="separador-sutil">
          <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Resumo detalhado por app</div>
          ${montarTabelaApps(u.apps_resumo || [])}`;
        a.appendChild(wrapper);
      }, 120);
    }
  }

  function montarTabelaApps(apps) {
    if (!apps.length) return `<div class="texto-fraco small">Sem apps no período.</div>`;

    return `<div class="table-responsive" style="max-height:320px">
      <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky small">
        <thead><tr class="texto-fraco">
          <th>App</th><th class="text-end">Foco</th><th class="text-end">2.º plano</th><th class="text-end">Total</th><th>Primeiro uso</th><th>Último uso</th>
        </tr></thead>
        <tbody>${apps.map((a,i) => `<tr>
          <td><div class="d-flex align-items-center gap-2"><span style="width:10px;height:10px;border-radius:3px;background:${_obterCorApp(a.nome_app)};flex-shrink:0"></span><span class="fw-semibold">${escaparHtml(a.nome_app || "—")}</span></div></td>
          <td class="text-end texto-mono">${hhmmss(a.segundos_em_foco || 0)}</td>
          <td class="text-end texto-mono texto-fraco">${hhmmss(a.segundos_segundo_plano || 0)}</td>
          <td class="text-end texto-mono">${hhmmss(a.segundos_total_aberto || 0)}</td>
          <td class="texto-fraco">${dataHoraCurta(a.primeiro_uso_em)}</td>
          <td class="texto-fraco">${dataHoraCurta(a.ultimo_uso_em)}</td>
        </tr>`).join("")}</tbody>
      </table>
    </div>`;
  }

  // ─── Tempo Declarado ──────────────────────────────────────
  function formatarRs(v) { return Number(v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" }); }

  function dataIsoBrCurta(iso) {
    const m = String(iso ?? "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return iso ?? "—";
    const d = new Date(iso + "T12:00:00");
    const ds = d.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", "").toUpperCase();
    return `<span class="badge badge-suave me-1">${ds}</span>${m[3]}/${m[2]}`;
  }

  async function carregarTempoDeclarado() {
    const area = document.getElementById("areaDeclaradoPorUsuario");
    if (!area) return;
    area.innerHTML = `<div class="texto-fraco small">Carregando…</div>`;
    try {
      // Sempre últimos 30 dias, independente do filtro de data
      const hoje = obterDataHojeIso();
      const inicio30 = subtrairDiasIso(hoje, 29);

      const [dados, pagamentos] = await Promise.all([
        requisitarJson("./commands/relatorio/tempo_trabalhado.php", {
          data_inicio: inicio30, data_fim: hoje, usuarios: [],
        }),
        (async () => {
          try {
            // Buscar pagamentos de todos os usuários nos últimos 30 dias
            const r = await requisitarJson("./commands/usuarios/listar.php");
            const users = Array.isArray(r) ? r : (Array.isArray(r?.dados) ? r.dados : []);
            let totalPago = 0;
            for (const u of users) {
              try {
                const rp = await requisitarJson(`./commands/pagamentos/listar_por_usuario.php?user_id=${encodeURIComponent(u.user_id)}`);
                const pags = Array.isArray(rp) ? rp : (Array.isArray(rp?.dados) ? rp.dados : []);
                pags.forEach(p => {
                  if (p.data_pagamento && p.data_pagamento >= inicio30 && p.data_pagamento <= hoje) {
                    totalPago += Number(p.valor || 0);
                  }
                });
              } catch (_) {}
            }
            return totalPago;
          } catch (_) { return 0; }
        })(),
      ]);

      renderizarTempoDeclarado(dados, pagamentos);
    } catch (e) {
      area.innerHTML = `<div class="texto-fraco small text-danger">Erro: ${escaparHtml(e.message)}</div>`;
    }
  }

  function renderizarTempoDeclarado(dados, totalPago) {
    const area = document.getElementById("areaDeclaradoPorUsuario");
    if (!area) return;
    const periodo = dados.periodo ?? {};
    setTexto("declTotalHoras", dados.total_geral_horas ?? "—");
    // Pendente = total geral - total pago (soma de todos os pagamentos)
    const totalGeralValor = dados.total_geral_valor ?? 0;
    const valorPendente = Math.max(0, totalGeralValor - (totalPago ?? 0));
    setTexto("declTotalValor", formatarRs(valorPendente));
    setTexto("declTotalPago", formatarRs(totalPago ?? 0));
    setTexto("declTotalEditores", String((dados.totais_por_usuario ?? []).length));
    const elP = document.getElementById("declPeriodo");
    if (elP) {
      const di = String(periodo.data_inicio ?? "").slice(8,10) + "/" + String(periodo.data_inicio ?? "").slice(5,7);
      const df = String(periodo.data_fim ?? "").slice(8,10) + "/" + String(periodo.data_fim ?? "").slice(5,7);
      elP.textContent = di && df ? `${di} → ${df}` : "—";
    }

    const totais = dados.totais_por_usuario ?? [];
    const linhasRaw = dados.linhas ?? [];
    if (!totais.length) { area.innerHTML = `<div class="texto-fraco small">Nenhuma declaração no período.</div>`; return; }

    const porUser = {};
    for (const ln of linhasRaw) { if (!porUser[ln.user_id]) porUser[ln.user_id] = []; porUser[ln.user_id].push(ln); }

    let html = `<div class="d-flex flex-column gap-3">`;
    for (const tot of totais) {
      const linhas = (porUser[tot.user_id] ?? []).sort((a,b) => b.referencia_data.localeCompare(a.referencia_data));
      const temValor = tot.valor_hora > 0;
      const barraMax = totais[0].segundos_total || 1;
      const pct = Math.round((tot.segundos_total / barraMax) * 100);

      html += `<div class="card-metrica" style="padding:16px">
        <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
          <div class="d-flex align-items-center gap-2">
            <div class="perfil-avatar" style="width:32px;height:32px;font-size:.72rem;border-radius:8px">${iniciais(tot.nome_exibicao || tot.user_id)}</div>
            <div>
              <div class="fw-semibold">${escaparHtml(tot.nome_exibicao || tot.user_id)}</div>
              <div class="texto-fraco small">${escaparHtml(tot.user_id)}${temValor ? ` · ${formatarRs(tot.valor_hora)}/h` : ""}</div>
            </div>
          </div>
          <div class="d-flex gap-3 text-end">
            <div><div class="texto-fraco small">Dias</div><div class="fw-bold">${tot.dias_trabalhados}</div></div>
            <div><div class="texto-fraco small">Declarado</div><div class="fw-bold texto-mono">${escaparHtml(tot.horas_formatado)}</div></div>
            ${temValor ? `<div><div class="texto-fraco small">A pagar</div><div class="fw-bold text-success">${formatarRs(tot.valor_pendente ?? tot.valor_estimado)}</div></div>` : ""}
          </div>
        </div>
        <div style="height:3px;background:rgba(255,255,255,.06);border-radius:2px" class="mb-3">
          <div style="height:3px;width:${pct}%;background:#6366f1;border-radius:2px;transition:width .4s"></div>
        </div>
        <div class="table-responsive">
          <table class="table table-dark table-borderless align-middle mb-0" style="font-size:.8rem">
            <thead><tr class="texto-fraco" style="border-bottom:1px solid rgba(255,255,255,.06)">
              <th style="min-width:100px">Data</th><th class="text-center">Tempo</th><th class="text-center">Registros</th>${temValor ? '<th class="text-end">Valor</th>' : ""}
            </tr></thead>
            <tbody>${linhas.map(ln => `<tr>
              <td>${dataIsoBrCurta(ln.referencia_data)}</td>
              <td class="text-center fw-semibold texto-mono">${escaparHtml(ln.horas_formatado)}</td>
              <td class="text-center texto-fraco">${ln.total_declaracoes}</td>
              ${temValor ? `<td class="text-end">${formatarRs(ln.valor_estimado)}</td>` : ""}
            </tr>`).join("")}</tbody>
          </table>
        </div>
      </div>`;
    }
    html += `</div>`;
    area.innerHTML = html;
  }

  // Recalcula _teamTimelineDias / _teamTimelineIdxDia / _modoTotalPeriodo a partir do payload.
  // Deve rodar ANTES de montarResumo/montarTabelaUsuarios para evitar flash de valores do recorte anterior.
  function _recalcularTeamTimelineDias(dados, usuarioDetalheId) {
    const usuarios = (dados && dados.usuarios) || [];
    const hoje = obterDataHojeIso();
    _modoTotalPeriodo = _filtroTemMultiplosDias();

    if (_modoTotalPeriodo) {
      const ini = (document.getElementById("filtroGraficosDataInicio") || {}).value || hoje;
      const fim = (document.getElementById("filtroGraficosDataFim") || {}).value || hoje;
      _teamTimelineDias = _gerarDiasContiguos(ini, fim).reverse();
      _teamTimelineIdxDia = 0;
      return;
    }

    const individual = !!usuarioDetalheId && usuarios.length === 1;
    const diasSet = new Set();
    usuarios.forEach(u => {
      (u.periodos_foco || []).forEach(p => {
        _extrairDiasAbrangidos(p.inicio_em, p.fim_em).forEach(d => diasSet.add(d));
      });
      if (individual) {
        (u.periodos_abertos || []).forEach(p => {
          _extrairDiasAbrangidos(p.inicio_em, p.fim_em).forEach(d => diasSet.add(d));
        });
      }
    });

    if (diasSet.size > 0) {
      const todos = [...diasSet].sort();
      const maisAntigo = todos[0];
      const maisRecente = todos[todos.length - 1] > hoje ? todos[todos.length - 1] : hoje;
      _teamTimelineDias = _gerarDiasContiguos(maisAntigo, maisRecente).reverse();
    } else {
      // Sem dados: se o usuário aplicou uma data manual, respeitar o dia do filtro; caso contrário, hoje
      const fimFiltro = (document.getElementById("filtroGraficosDataFim") || {}).value || "";
      _teamTimelineDias = [foiAplicadoManualmente && fimFiltro ? fimFiltro : hoje];
    }
    _teamTimelineIdxDia = 0;
  }

  // ─── Fluxo principal ──────────────────────────────────────
  async function atualizarGraficos() {
    if (!abaGraficosEstaVisivel()) return;
    if (requisicaoEmAndamento) return;
    requisicaoEmAndamento = true;

    try {
      garantirEstruturaSimplificada();
      await carregarMetaFiltros();
      const filtros = obterFiltros();

      const [dadosPainel] = await Promise.all([
        requisitarJson(urlApiGraficos, {
          acao: "painel",
          data_inicio: filtros.data_inicio, data_fim: filtros.data_fim,
          usuarios: filtros.usuarios, apps: filtros.apps,
        }),
        carregarTempoDeclarado(),
      ]);

      _dadosPainelAtual = dadosPainel;
      setTexto("textoGraficosUltimaAtualizacao", dataHoraCurta(dadosPainel.atualizado_em));
      _recalcularTeamTimelineDias(dadosPainel, filtros.usuario_detalhe);
      montarResumo(dadosPainel);
      montarTabelaUsuarios(dadosPainel);
      montarDetalheUsuario(dadosPainel, filtros.usuario_detalhe);
    } catch (e) {
      mostrarAlerta("erro", "Gráficos:", String(e?.message || e));
    } finally {
      requisicaoEmAndamento = false;
    }
  }

  function limparFiltros() {
    foiAplicadoManualmente = false;
    _modoTotalPeriodo = false;
    _teamTimelineIdxDia = 0;
    FILTROS_APPS_ATIVOS = [];
    const ini = document.getElementById("filtroGraficosDataInicio");
    const fim = document.getElementById("filtroGraficosDataFim");
    if (ini) { ini.value = ""; ini.classList.remove("filtro-pendente"); }
    if (fim) { fim.value = ""; fim.classList.remove("filtro-pendente"); }
    _atualizarLabelTeamTimeline();
  }

  function _filtroTemMultiplosDias() {
    if (!foiAplicadoManualmente) return false;
    const ini = (document.getElementById("filtroGraficosDataInicio") || {}).value || "";
    const fim = (document.getElementById("filtroGraficosDataFim") || {}).value || "";
    return ini && fim && ini !== fim;
  }

  function configurarGatilhos() {
    document.querySelectorAll('#menuAbas a[data-aba]').forEach(link => {
      link.addEventListener("click", () => {
        if (link.getAttribute("data-aba") === "abaGraficos") setTimeout(atualizarGraficos, 80);
      });
    });

    document.addEventListener("click", (ev) => {
      if (ev.target?.id === "botaoAplicarFiltrosGraficos") {
        foiAplicadoManualmente = true;
        document.getElementById("filtroGraficosDataInicio")?.classList.remove("filtro-pendente");
        document.getElementById("filtroGraficosDataFim")?.classList.remove("filtro-pendente");
        atualizarGraficos();
      }
      if (ev.target?.id === "botaoLimparFiltrosGraficos") { limparFiltros(); atualizarGraficos(); }
      if (ev.target?.id === "botaoAbrirModalCores") _abrirModalCores();
    });

    // Destaca inputs de data alterados até o usuário clicar em "Aplicar"
    document.addEventListener("input", (ev) => {
      const id = ev.target?.id;
      if (id === "filtroGraficosDataInicio" || id === "filtroGraficosDataFim") {
        ev.target.classList.add("filtro-pendente");
      }
    });

    document.addEventListener("change", (ev) => {
      if (ev.target?.id === "filtroGraficosUsuarioDetalhe") atualizarGraficos();
    });

    // Navegação dia a dia na timeline (event delegation — registra 1 vez)
    document.addEventListener("click", (ev) => {
      if (ev.target?.id === "btnTeamTimelineDiaAnterior") {
        if (_teamTimelineIdxDia < _teamTimelineDias.length - 1) {
          _teamTimelineIdxDia++;
          _atualizarLabelTeamTimeline();
          _renderizarTeamTimelineDoDia();
          if (_dadosPainelAtual) {
            montarResumo(_dadosPainelAtual);
            montarTabelaUsuarios(_dadosPainelAtual);
          }
          if (_teamTimelineUsuarios) {
            renderizarGlobalApps(_teamTimelineUsuarios);
            renderizarComparativoUsuarios(_teamTimelineUsuarios);
            if (_teamTimelineUsuarios.length === 1) renderizarBarrasApps(_teamTimelineUsuarios[0]);
          }
          if (_timelineAbertosUsuario) renderizarTimelineAbertosDoDia();
        }
      }
      if (ev.target?.id === "btnTeamTimelineDiaProximo") {
        if (_teamTimelineIdxDia > 0) {
          _teamTimelineIdxDia--;
          _atualizarLabelTeamTimeline();
          _renderizarTeamTimelineDoDia();
          if (_dadosPainelAtual) {
            montarResumo(_dadosPainelAtual);
            montarTabelaUsuarios(_dadosPainelAtual);
          }
          if (_teamTimelineUsuarios) {
            renderizarGlobalApps(_teamTimelineUsuarios);
            renderizarComparativoUsuarios(_teamTimelineUsuarios);
            if (_teamTimelineUsuarios.length === 1) renderizarBarrasApps(_teamTimelineUsuarios[0]);
          }
          if (_timelineAbertosUsuario) renderizarTimelineAbertosDoDia();
        }
      }
    });
  }

  // ─── Modal de Cores ────────────────────────────────────────
  function _abrirModalCores() {
    // Coleta todos os apps únicos do último payload
    const appsSet = new Set();
    const usuarios = _dadosPainelAtual?.usuarios || [];
    usuarios.forEach(u => {
      (u.apps_resumo || []).forEach(a => { if (a.nome_app) appsSet.add(a.nome_app); });
      (u.periodos_foco || []).forEach(p => { if (p.nome_app) appsSet.add(p.nome_app); });
    });
    const apps = [...appsSet].sort();

    const linhas = apps.map(app => {
      const cor = _obterCorApp(app);
      return `
        <div class="d-flex align-items-center gap-3 py-2" style="border-bottom:1px solid rgba(255,255,255,.06)">
          <input type="color" value="${cor}" data-app="${escaparHtml(app)}"
            class="rk-color-picker flex-shrink-0"
            style="width:36px;height:28px;border:none;background:none;cursor:pointer;border-radius:4px;overflow:hidden">
          <span class="small" style="flex:1">${escaparHtml(app)}</span>
          <button type="button" class="btn btn-sm btn-link text-danger p-0 rk-reset-cor" data-app="${escaparHtml(app)}" title="Restaurar padrão" style="font-size:.75rem">Resetar</button>
        </div>`;
    }).join("");

    // Inject / reutilizar modal
    let modal = document.getElementById("modalRkCoresApps");
    if (!modal) {
      modal = document.createElement("div");
      modal.className = "modal fade";
      modal.id = "modalRkCoresApps";
      modal.setAttribute("tabindex", "-1");
      modal.innerHTML = `
        <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
          <div class="modal-content bg-dark text-white border-secondary">
            <div class="modal-header border-secondary">
              <h5 class="modal-title">🎨 Cores dos Aplicativos</h5>
              <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body" id="modalRkCoresCorpo" style="max-height:420px;overflow-y:auto"></div>
            <div class="modal-footer border-secondary">
              <button type="button" class="btn btn-outline-danger btn-sm" id="btnRkResetarTudo">Resetar Tudo</button>
              <button type="button" class="btn btn-light btn-sm" id="btnRkSalvarCores">Salvar</button>
            </div>
          </div>
        </div>`;
      document.body.appendChild(modal);
    }

    document.getElementById("modalRkCoresCorpo").innerHTML =
      apps.length ? linhas : '<div class="texto-fraco text-center py-3">Carregue os gráficos primeiro.</div>';

    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();

    modal.querySelector("#btnRkSalvarCores")?.addEventListener("click", () => {
      modal.querySelectorAll(".rk-color-picker").forEach(inp => {
        CORES_CUSTOMIZADAS[inp.dataset.app] = inp.value;
      });
      localStorage.setItem("rk_cores_apps", JSON.stringify(CORES_CUSTOMIZADAS));
      _cacheCorApps = {};  // invalidar cache
      bsModal.hide();
      atualizarGraficos();
    }, { once: true });

    modal.querySelector("#btnRkResetarTudo")?.addEventListener("click", () => {
      CORES_CUSTOMIZADAS = {};
      _cacheCorApps = {};  // invalidar cache
      localStorage.removeItem("rk_cores_apps");
      bsModal.hide();
      atualizarGraficos();
    }, { once: true });

    modal.querySelectorAll(".rk-reset-cor").forEach(btn => {
      btn.addEventListener("click", () => {
        const app = btn.dataset.app;
        const picker = modal.querySelector(`.rk-color-picker[data-app="${app}"]`);
        if (picker) picker.value = MAPA_CORES_APPS[app] || "#888888";
      });
    });
  }

  function resizarGraficos() {
    ["chartBarrasApps", "chartGlobalComparativo", "chartGlobalApps",
     "chartGlobalTimeline", "chartTimelineAbertos"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) echarts.getInstanceByDom(el)?.resize();
    });
  }

  // ─── API pública ──────────────────────────────────────────
  window._alternarFiltroApp = alternarFiltroApp;

  window.PainelAbaGraficos = {
    iniciarGraficos: () => {},
    renderizarAbaGraficos: atualizarGraficos,
    recarregarGraficosNoEstado: () => Promise.resolve(),
    resizarGraficos,
  };

  document.addEventListener("DOMContentLoaded", () => {
    garantirEstruturaSimplificada();
    garantirDatasPadrao();
    configurarGatilhos();

    // Resize listener único — redimensiona todos os charts ECharts de uma vez
    window.addEventListener("resize", resizarGraficos);

    if (abaGraficosEstaVisivel()) atualizarGraficos();
  });
})();
