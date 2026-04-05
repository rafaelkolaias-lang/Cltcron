(function () {
  "use strict";

  const urlApiGraficos = "./commands/graficos/graficos.php";
  const seletorAbaGraficos = "#abaGraficos";
  const seletorAreaAlertas = "#areaAlertas";

  let intervaloAutoAtualizacao = null;
  let requisicaoEmAndamento = false;
  let metaCarregada = false;

  // Instâncias ECharts (reutilizadas para evitar memory leaks)
  let chartDonut = null;
  let chartBarras = null;
  let chartTimeline = null;

  // Paleta de cores harmônica (análoga azul-violeta, sutil no dark theme)
  const PALETA = [
    "#6366f1", "#8b5cf6", "#a78bfa", "#60a5fa", "#38bdf8",
    "#34d399", "#4ade80", "#fbbf24", "#f97316", "#f43f5e",
    "#e879f9", "#22d3ee", "#a3e635", "#fb923c", "#c084fc",
  ];

  // ─── Utilidades ─────────────────────────────────────────────
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
    const aba = document.querySelector(seletorAbaGraficos);
    return !!aba && !aba.classList.contains("d-none");
  }

  async function requisitarJson(url, corpo) {
    const resp = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(corpo || {}),
      cache: "no-store",
    });
    const json = await resp.json();
    if (!resp.ok || !json || json.ok !== true) throw new Error(json?.mensagem || "Falha ao buscar dados.");
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

  // ─── Estrutura HTML ────────────────────────────────────────
  function garantirEstruturaSimplificada() {
    const aba = document.querySelector(seletorAbaGraficos);
    if (!aba) return;
    if (document.getElementById("painelGraficosSimplificado")) return;

    aba.innerHTML = `
      <div id="painelGraficosSimplificado" class="container-fluid px-0">

        <!-- Filtros compactos -->
        <div class="cartao-grafite p-3 secao-graficos">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <div>
              <h5 class="mb-0 fw-bold">Monitoramento de Atividade</h5>
              <div class="texto-fraco small mt-1">Controle em tempo real dos apps utilizados por cada editor</div>
            </div>
            <div class="texto-fraco small">
              <span id="textoGraficosUltimaAtualizacao">—</span>
            </div>
          </div>

          <div class="filtros-compactos">
            <div>
              <label>Início</label>
              <input type="date" id="filtroGraficosDataInicio" class="form-control form-control-sm bg-transparent text-white border-secondary" style="width:150px">
            </div>
            <div>
              <label>Fim</label>
              <input type="date" id="filtroGraficosDataFim" class="form-control form-control-sm bg-transparent text-white border-secondary" style="width:150px">
            </div>
            <div>
              <label>Usuários</label>
              <select id="filtroGraficosUsuarios" class="form-select form-select-sm bg-transparent text-white border-secondary" multiple size="3" style="width:200px"></select>
            </div>
            <div>
              <label>Apps</label>
              <select id="filtroGraficosApps" class="form-select form-select-sm bg-transparent text-white border-secondary" multiple size="3" style="width:200px"></select>
            </div>
            <div class="d-flex gap-2 align-items-end">
              <button type="button" id="botaoAplicarFiltrosGraficos" class="btn btn-sm btn-light botao-mini">Aplicar</button>
              <button type="button" id="botaoLimparFiltrosGraficos" class="btn btn-sm btn-outline-light botao-mini">Limpar</button>
            </div>
          </div>
        </div>

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
            <h6 class="mb-0 fw-bold">Visão Geral dos Editores</h6>
            <div class="texto-fraco small" id="textoTotalUsuarios"></div>
          </div>
          <div class="table-responsive tabela-limite" style="max-height:400px">
            <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
              <thead>
                <tr class="texto-fraco small">
                  <th>Editor</th>
                  <th>Status</th>
                  <th>Atividade</th>
                  <th>App em foco</th>
                  <th class="text-end">Trabalhado</th>
                  <th class="text-end">Ocioso</th>
                  <th class="text-end">Apps</th>
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
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <h6 class="mb-0 fw-bold">Detalhe do Editor</h6>
            <select id="filtroGraficosUsuarioDetalhe" class="form-select form-select-sm bg-transparent text-white border-secondary" style="width:260px"></select>
          </div>
          <div id="areaUsuarioSelecionadoGraficos">
            <div class="texto-fraco">Selecione um editor para ver os detalhes.</div>
          </div>
        </div>

        <!-- Tempo declarado -->
        <div class="cartao-grafite p-3 secao-graficos">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <div>
              <h6 class="mb-0 fw-bold">Tempo Declarado</h6>
              <div class="texto-fraco small mt-1">Apenas o tempo que o editor declarou como trabalhado</div>
            </div>
            <span class="badge badge-suave">declarado</span>
          </div>
          <div class="row g-3 mb-3" id="cardsDeclarado">
            <div class="col-6 col-md-3"><div class="card-metrica"><div class="card-metrica__rotulo">Total declarado</div><div class="card-metrica__valor texto-mono" id="declTotalHoras">—</div></div></div>
            <div class="col-6 col-md-3"><div class="card-metrica"><div class="card-metrica__rotulo">Valor estimado</div><div class="card-metrica__valor text-success" id="declTotalValor">—</div></div></div>
            <div class="col-6 col-md-3"><div class="card-metrica"><div class="card-metrica__rotulo">Editores</div><div class="card-metrica__valor" id="declTotalEditores">—</div></div></div>
            <div class="col-6 col-md-3"><div class="card-metrica"><div class="card-metrica__rotulo">Período</div><div class="card-metrica__valor" style="font-size:1rem" id="declPeriodo">—</div></div></div>
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
    if (!ini.value) ini.value = subtrairDiasIso(fim.value, 6);
  }

  function obterFiltros() {
    garantirDatasPadrao();
    const vals = (id) => {
      const el = document.getElementById(id);
      return el ? Array.from(el.selectedOptions).map(o => o.value).filter(Boolean) : [];
    };
    return {
      data_inicio: (document.getElementById("filtroGraficosDataInicio") || {}).value || "",
      data_fim: (document.getElementById("filtroGraficosDataFim") || {}).value || "",
      usuarios: vals("filtroGraficosUsuarios"),
      apps: vals("filtroGraficosApps"),
      usuario_detalhe: (document.getElementById("filtroGraficosUsuarioDetalhe") || {}).value || "",
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

    preencherSelect("filtroGraficosUsuarios", usuarios, "user_id", "texto");

    const apps = (dados.apps || []).map(a => ({ nome: a, texto: a }));
    preencherSelect("filtroGraficosApps", apps, "nome", "texto");

    const sel = document.getElementById("filtroGraficosUsuarioDetalhe");
    if (sel) {
      sel.innerHTML = `<option value="">Selecione um editor…</option>`;
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

  function montarResumo(dados) {
    const r = dados.resumo_geral || {};
    const st = r.status_atual || {};
    setTexto("numeroResumoTrabalhandoAgora", String(st.trabalhando || 0));
    setTexto("numeroResumoOciososAgora", String(st.ocioso || 0));
    setTexto("numeroResumoPausadosAgora", String(st.pausado || 0));
    setTexto("textoResumoTempoTrabalhando", hhmmss(r.segundos_trabalhando_total || 0));
    setTexto("textoResumoTempoOcioso", hhmmss(r.segundos_ocioso_total || 0));
    setTexto("textoResumoTempoPausado", hhmmss(r.segundos_pausado_total || 0));
  }

  // ─── Tabela de editores ───────────────────────────────────
  function montarTabelaUsuarios(dados) {
    const tbody = document.getElementById("tbodyResumoUsuariosGraficos");
    if (!tbody) return;
    const usuarios = dados.usuarios || [];
    setTexto("textoTotalUsuarios", `${usuarios.length} editor${usuarios.length !== 1 ? "es" : ""}`);

    if (!usuarios.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="texto-fraco">Sem dados para este período.</td></tr>`;
      return;
    }

    tbody.innerHTML = usuarios.map(u => {
      const nome = escaparHtml(u.nome_exibicao || u.user_id || "—");
      const uid = escaparHtml(u.user_id || "");
      const status = u.status_atual || "sem_status";
      const ativ = escaparHtml(String(u.atividade_atual || "").trim() || "—");
      const app = escaparHtml(u.app_principal || "—");

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
        <td class="text-end texto-mono text-success" style="font-size:.85rem">${hhmmss(u.segundos_trabalhando_total || 0)}</td>
        <td class="text-end texto-mono text-warning" style="font-size:.85rem">${hhmmss(u.segundos_ocioso_total || 0)}</td>
        <td class="text-end">${Number(u.quantidade_apps_usados || 0)}</td>
      </tr>`;
    }).join("");
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

  function renderizarDonutApps(usuario) {
    const chart = criarOuObterChart("chartDonutApps", 300);
    if (!chart) return;

    const apps = (usuario.apps_resumo || []).slice(0, 12);
    if (!apps.length) { chart.clear(); return; }

    const dados = apps.map((a, i) => ({
      name: a.nome_app || "—",
      value: a.segundos_em_foco || 0,
      itemStyle: { color: PALETA[i % PALETA.length] },
    }));

    chart.setOption({
      tooltip: {
        trigger: "item",
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 13 },
        formatter: (p) => `<strong>${escaparHtml(p.name)}</strong><br/>Foco: ${hhmm(p.value)}<br/>${p.percent?.toFixed(1)}%`,
      },
      legend: {
        type: "scroll",
        orient: "vertical",
        right: 10,
        top: 20,
        bottom: 20,
        textStyle: { color: "rgba(255,255,255,.7)", fontSize: 12 },
        pageTextStyle: { color: "rgba(255,255,255,.5)" },
      },
      series: [{
        type: "pie",
        radius: ["48%", "74%"],
        center: ["35%", "50%"],
        avoidLabelOverlap: true,
        padAngle: 2,
        itemStyle: { borderRadius: 6, borderColor: "rgba(11,18,32,.8)", borderWidth: 2 },
        label: { show: false },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: "bold", color: "#fff" },
          itemStyle: { shadowBlur: 20, shadowColor: "rgba(99,102,241,.4)" },
        },
        data: dados,
      }],
    }, true);
  }

  function renderizarBarrasApps(usuario) {
    const chart = criarOuObterChart("chartBarrasApps", 260);
    if (!chart) return;

    const apps = (usuario.apps_resumo || []).slice(0, 10);
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

  // Estado da navegação dia a dia na timeline
  let _timelineDias = [];
  let _timelineIdxDia = 0;
  let _timelineUsuarioAtual = null;

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

  function _atualizarLabelDia() {
    const label = document.getElementById("timelineDiaLabel");
    if (!label || !_timelineDias.length) return;
    label.textContent = _formatarDiaBr(_timelineDias[_timelineIdxDia]);

    const btnAnt = document.getElementById("btnTimelineDiaAnterior");
    const btnProx = document.getElementById("btnTimelineDiaProximo");
    if (btnAnt) btnAnt.disabled = _timelineIdxDia >= _timelineDias.length - 1;
    if (btnProx) btnProx.disabled = _timelineIdxDia <= 0;
  }

  function renderizarTimelineDoDia() {
    const chart = criarOuObterChart("chartTimelineApps", 200);
    if (!chart || !_timelineUsuarioAtual) return;

    const diaSelecionado = _timelineDias[_timelineIdxDia];
    if (!diaSelecionado) { chart.clear(); return; }

    const periodos = (_timelineUsuarioAtual.periodos_foco || [])
      .filter(p => _extrairDiaIso(p.inicio_em) === diaSelecionado);

    if (!periodos.length) {
      chart.clear();
      chart.setOption({ title: { text: "Sem atividade neste dia", left: "center", top: "center", textStyle: { color: "rgba(255,255,255,.3)", fontSize: 14 } } }, true);
      return;
    }

    const appsUnicos = [...new Set(periodos.map(p => p.nome_app || "—"))];
    const corPorApp = {};
    appsUnicos.forEach((app, i) => { corPorApp[app] = PALETA[i % PALETA.length]; });

    // Limites fixos do dia: 00:00 → 23:59
    const diaInicio = new Date(diaSelecionado + "T00:00:00").getTime();
    const diaFim = new Date(diaSelecionado + "T23:59:59").getTime();

    const dados = periodos
      .filter(p => p.inicio_em)
      .map(p => {
        const app = p.nome_app || "—";
        const inicio = new Date(String(p.inicio_em).replace(" ", "T"));
        const fim = p.fim_em ? new Date(String(p.fim_em).replace(" ", "T")) : new Date();
        return {
          name: app,
          value: [app, inicio.getTime(), fim.getTime(), p.segundos_periodo || 0],
          itemStyle: { color: corPorApp[app] },
        };
      })
      .filter(d => !isNaN(d.value[1]));

    if (!dados.length) { chart.clear(); return; }

    const alturaChart = Math.max(120, Math.min(350, appsUnicos.length * 36 + 60));
    const el = document.getElementById("chartTimelineApps");
    if (el) el.style.height = alturaChart + "px";
    chart.resize();

    chart.setOption({
      tooltip: {
        backgroundColor: "rgba(15,20,35,.92)",
        borderColor: "rgba(255,255,255,.1)",
        textStyle: { color: "#e2e8f0", fontSize: 12 },
        formatter: (p) => {
          const v = p.value;
          const ini = new Date(v[1]).toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit" });
          const f = new Date(v[2]).toLocaleString("pt-BR", { hour: "2-digit", minute: "2-digit" });
          return `<strong>${escaparHtml(v[0])}</strong><br/>${ini} → ${f}<br/>Duração: ${hhmm(v[3])}`;
        },
      },
      grid: { left: 8, right: 16, top: 8, bottom: 32, containLabel: true },
      xAxis: {
        type: "time",
        min: diaInicio,
        max: diaFim,
        axisLabel: { color: "rgba(255,255,255,.4)", fontSize: 11, formatter: (v) => new Date(v).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) },
        splitLine: { lineStyle: { color: "rgba(255,255,255,.04)" } },
      },
      yAxis: { type: "category", data: appsUnicos, axisLabel: { color: "rgba(255,255,255,.7)", fontSize: 11, width: 100, overflow: "truncate" }, axisTick: { show: false }, axisLine: { show: false } },
      series: [{
        type: "custom",
        renderItem: (params, api) => {
          const catIdx = api.value(0);
          const inicio = api.coord([api.value(1), catIdx]);
          const fim = api.coord([api.value(2), catIdx]);
          const bandH = api.size([0, 1])[1] * 0.6;
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

  function renderizarTimelineApps(usuario) {
    _timelineUsuarioAtual = usuario;

    const periodos = usuario.periodos_foco || [];

    // Extrair dias únicos e ordenar (mais recente primeiro)
    const diasSet = new Set();
    periodos.forEach(p => {
      const dia = _extrairDiaIso(p.inicio_em);
      if (dia) diasSet.add(dia);
    });
    _timelineDias = [...diasSet].sort().reverse();
    _timelineIdxDia = 0; // começa no dia mais recente

    _atualizarLabelDia();
    renderizarTimelineDoDia();
  }

  // ─── Detalhe do usuário selecionado ───────────────────────
  function montarDetalheUsuario(dados, userId) {
    const area = document.getElementById("areaUsuarioSelecionadoGraficos");
    if (!area) return;

    const usuarios = dados.usuarios || [];
    let u = userId ? usuarios.find(x => x.user_id === userId) : null;
    if (!u && usuarios.length) {
      u = usuarios[0];
      const sel = document.getElementById("filtroGraficosUsuarioDetalhe");
      if (sel) sel.value = u.user_id || "";
    }

    if (!u) {
      area.innerHTML = `<div class="texto-fraco">Sem dados para o período selecionado.</div>`;
      return;
    }

    const status = u.status_atual || "sem_status";
    const appsAbertos = u.apps_abertos_agora || [];

    area.innerHTML = `
      <!-- Header do perfil -->
      <div class="perfil-usuario-header">
        <div class="perfil-avatar">${iniciais(u.nome_exibicao || u.user_id)}</div>
        <div class="flex-grow-1">
          <div class="d-flex flex-wrap align-items-center gap-2">
            <h5 class="mb-0 fw-bold">${escaparHtml(u.nome_exibicao || u.user_id || "—")}</h5>
            <span class="indicador-status ${classeStatus(status)}">${textoStatus(status)}</span>
          </div>
          <div class="texto-fraco small mt-1">${escaparHtml(u.user_id || "")} · ${escaparHtml(String(u.atividade_atual || "").trim() || "Sem atividade")}</div>
        </div>
        <div class="d-flex gap-3 text-end d-none d-md-flex">
          <div><div class="texto-fraco small">Trabalhado</div><div class="fw-bold texto-mono text-success">${hhmmss(u.segundos_trabalhando_total || 0)}</div></div>
          <div><div class="texto-fraco small">Ocioso</div><div class="fw-bold texto-mono text-warning">${hhmmss(u.segundos_ocioso_total || 0)}</div></div>
          <div><div class="texto-fraco small">Pausado</div><div class="fw-bold texto-mono">${hhmmss(u.segundos_pausado_total || 0)}</div></div>
          <div><div class="texto-fraco small">Foco em apps</div><div class="fw-bold texto-mono">${hhmmss(u.segundos_total_foco || 0)}</div></div>
        </div>
      </div>

      <!-- Apps abertos agora -->
      ${appsAbertos.length ? `
        <div class="mb-3">
          <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Apps abertos agora</div>
          <div class="d-flex flex-wrap gap-2">
            ${appsAbertos.map(a => `<span class="pill-app"><span class="pill-app__dot"></span>${escaparHtml(a.nome_app || "—")}<span class="texto-fraco small ms-1">${dataHoraCurta(a.inicio_em)}</span></span>`).join("")}
          </div>
        </div>
      ` : ""}

      <hr class="separador-sutil">

      <!-- Gráficos lado a lado -->
      <div class="row g-3 mb-3">
        <div class="col-12 col-xl-5">
          <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Distribuição por app (foco)</div>
          <div id="chartDonutApps" class="grafico-container" style="height:300px"></div>
        </div>
        <div class="col-12 col-xl-7">
          <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Ranking de apps — foco vs 2.º plano</div>
          <div id="chartBarrasApps" class="grafico-container" style="height:300px"></div>
        </div>
      </div>

      <!-- Timeline dia a dia -->
      <div class="mb-3">
        <div class="d-flex align-items-center justify-content-between mb-2">
          <div class="texto-fraco small fw-semibold" style="text-transform:uppercase;letter-spacing:.3px">Timeline de uso</div>
          <div class="d-flex align-items-center gap-2">
            <button id="btnTimelineDiaAnterior" class="btn btn-sm btn-outline-light botao-mini" style="padding:2px 10px;font-size:.85rem" title="Dia anterior">&larr;</button>
            <span id="timelineDiaLabel" class="fw-semibold" style="min-width:120px;text-align:center;font-size:.88rem">—</span>
            <button id="btnTimelineDiaProximo" class="btn btn-sm btn-outline-light botao-mini" style="padding:2px 10px;font-size:.85rem" title="Próximo dia">&rarr;</button>
          </div>
        </div>
        <div id="chartTimelineApps" class="grafico-container" style="height:${Math.max(120, Math.min(350, (new Set((u.periodos_foco||[]).map(p=>p.nome_app))).size * 36 + 60))}px"></div>
      </div>

      <hr class="separador-sutil">

      <!-- Tabela detalhada de apps -->
      <div>
        <div class="texto-fraco small fw-semibold mb-2" style="text-transform:uppercase;letter-spacing:.3px">Resumo detalhado por app</div>
        ${montarTabelaApps(u.apps_resumo || [])}
      </div>
    `;

    // Renderizar gráficos após o DOM estar pronto
    setTimeout(() => {
      renderizarDonutApps(u);
      renderizarBarrasApps(u);
      renderizarTimelineApps(u);

      // Responsividade
      window.addEventListener("resize", () => {
        echarts.getInstanceByDom(document.getElementById("chartDonutApps"))?.resize();
        echarts.getInstanceByDom(document.getElementById("chartBarrasApps"))?.resize();
        echarts.getInstanceByDom(document.getElementById("chartTimelineApps"))?.resize();
      }, { once: true });
    }, 50);
  }

  function montarTabelaApps(apps) {
    if (!apps.length) return `<div class="texto-fraco small">Sem apps no período.</div>`;

    return `<div class="table-responsive" style="max-height:320px">
      <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky small">
        <thead><tr class="texto-fraco">
          <th>App</th><th class="text-end">Foco</th><th class="text-end">2.º plano</th><th class="text-end">Total</th><th>Primeiro uso</th><th>Último uso</th>
        </tr></thead>
        <tbody>${apps.map((a,i) => `<tr>
          <td><div class="d-flex align-items-center gap-2"><span style="width:10px;height:10px;border-radius:3px;background:${PALETA[i%PALETA.length]};flex-shrink:0"></span><span class="fw-semibold">${escaparHtml(a.nome_app || "—")}</span></div></td>
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

  async function carregarTempoDeclarado(filtros) {
    const area = document.getElementById("areaDeclaradoPorUsuario");
    if (!area) return;
    area.innerHTML = `<div class="texto-fraco small">Carregando…</div>`;
    try {
      const dados = await requisitarJson("./commands/relatorio/tempo_trabalhado.php", {
        data_inicio: filtros.data_inicio, data_fim: filtros.data_fim, usuarios: filtros.usuarios,
      });
      renderizarTempoDeclarado(dados);
    } catch (e) {
      area.innerHTML = `<div class="texto-fraco small text-danger">Erro: ${escaparHtml(e.message)}</div>`;
    }
  }

  function renderizarTempoDeclarado(dados) {
    const area = document.getElementById("areaDeclaradoPorUsuario");
    if (!area) return;
    const periodo = dados.periodo ?? {};
    setTexto("declTotalHoras", dados.total_geral_horas ?? "—");
    setTexto("declTotalValor", formatarRs(dados.total_geral_valor ?? 0));
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
            ${temValor ? `<div><div class="texto-fraco small">A pagar</div><div class="fw-bold text-success">${formatarRs(tot.valor_estimado)}</div></div>` : ""}
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
        carregarTempoDeclarado(filtros),
      ]);

      setTexto("textoGraficosUltimaAtualizacao", dataHoraCurta(dadosPainel.atualizado_em));
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
    const fim = document.getElementById("filtroGraficosDataFim");
    const ini = document.getElementById("filtroGraficosDataInicio");
    if (fim) fim.value = obterDataHojeIso();
    if (ini) ini.value = subtrairDiasIso(obterDataHojeIso(), 6);
    ["filtroGraficosUsuarios", "filtroGraficosApps"].forEach(id => {
      const el = document.getElementById(id);
      if (el) Array.from(el.options).forEach(o => { o.selected = false; });
    });
    const det = document.getElementById("filtroGraficosUsuarioDetalhe");
    if (det) det.value = "";
  }

  function configurarGatilhos() {
    document.querySelectorAll('#menuAbas a[data-aba]').forEach(link => {
      link.addEventListener("click", () => {
        if (link.getAttribute("data-aba") === "abaGraficos") setTimeout(atualizarGraficos, 80);
      });
    });

    document.addEventListener("click", (ev) => {
      if (ev.target?.id === "botaoAplicarFiltrosGraficos") atualizarGraficos();
      if (ev.target?.id === "botaoLimparFiltrosGraficos") { limparFiltros(); atualizarGraficos(); }
    });

    document.addEventListener("change", (ev) => {
      if (ev.target?.id === "filtroGraficosUsuarioDetalhe") atualizarGraficos();
    });

    // Navegação dia a dia na timeline (event delegation — registra 1 vez)
    document.addEventListener("click", (ev) => {
      if (ev.target?.id === "btnTimelineDiaAnterior") {
        if (_timelineIdxDia < _timelineDias.length - 1) {
          _timelineIdxDia++;
          _atualizarLabelDia();
          renderizarTimelineDoDia();
        }
      }
      if (ev.target?.id === "btnTimelineDiaProximo") {
        if (_timelineIdxDia > 0) {
          _timelineIdxDia--;
          _atualizarLabelDia();
          renderizarTimelineDoDia();
        }
      }
    });
  }

  function iniciarAutoAtualizacao() {
    pararAutoAtualizacao();
    intervaloAutoAtualizacao = setInterval(() => { if (abaGraficosEstaVisivel()) atualizarGraficos(); }, 30000);
  }

  function pararAutoAtualizacao() {
    if (intervaloAutoAtualizacao) { clearInterval(intervaloAutoAtualizacao); intervaloAutoAtualizacao = null; }
  }

  // ─── API pública ──────────────────────────────────────────
  window.PainelAbaGraficos = {
    iniciarGraficos: () => {},
    renderizarAbaGraficos: atualizarGraficos,
    recarregarGraficosNoEstado: () => Promise.resolve(),
  };

  document.addEventListener("DOMContentLoaded", () => {
    garantirEstruturaSimplificada();
    garantirDatasPadrao();
    configurarGatilhos();
    iniciarAutoAtualizacao();
    if (abaGraficosEstaVisivel()) atualizarGraficos();

    document.addEventListener("visibilitychange", () => {
      if (document.hidden) pararAutoAtualizacao();
      else if (abaGraficosEstaVisivel()) iniciarAutoAtualizacao();
    });
  });
})();
