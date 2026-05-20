(function () {
  "use strict";

  const URL_API = "./commands/relatorio/tempo_trabalhado.php";
  const URL_USUARIOS = "./commands/usuarios/listar_ativos.php";

  // ─── utilidades ───────────────────────────────────────────────────────────
  function esc(v) {
    return String(v ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function dataIsoBr(iso) {
    const m = String(iso ?? "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : (iso ?? "—");
  }

  function diaSemana(iso) {
    if (!iso) return "";
    const d = new Date(iso + "T12:00:00");
    return d.toLocaleDateString("pt-BR", { weekday: "short" }).replace(".", "").toUpperCase();
  }

  function rs(valor) {
    return Number(valor ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function dataHojeIso() {
    const d = new Date();
    return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, "0"), String(d.getDate()).padStart(2, "0")].join("-");
  }

  function dataAddDias(iso, dias) {
    const d = new Date(iso + "T12:00:00");
    d.setDate(d.getDate() + dias);
    return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, "0"), String(d.getDate()).padStart(2, "0")].join("-");
  }

  function formatarHHMMSS(seg) {
    seg = Math.max(0, Math.floor(seg));
    const h = Math.floor(seg / 3600);
    const m = Math.floor((seg % 3600) / 60);
    const s = seg % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  // ─── estado ───────────────────────────────────────────────────────────────
  let carregando = false;
  let modoAgrupamento = "usuario";
  let ultimosDados = null;

  function el(id) { return document.getElementById(id); }

  // ─── inicialização ────────────────────────────────────────────────────────
  function inicializar() {
    const hoje = dataHojeIso();
    const inicio = dataAddDias(hoje, -29);

    const entradaInicio = el("relatorioDataInicio");
    const entradaFim = el("relatorioDataFim");
    if (entradaInicio) entradaInicio.value = inicio;
    if (entradaFim) entradaFim.value = hoje;

    el("relatorioBtnCarregar")?.addEventListener("click", carregarDados);

    el("relatorioBtnAlternarAgrupamento")?.addEventListener("click", () => {
      modoAgrupamento = modoAgrupamento === "usuario" ? "dia" : "usuario";
      el("relatorioBtnAlternarAgrupamento").textContent =
        modoAgrupamento === "usuario" ? "Agrupar por dia" : "Agrupar por usuário";
      if (ultimosDados) renderizar(ultimosDados);
    });

    el("relatorioBtnCSV")?.addEventListener("click", exportarCSV);

    carregarMembros();
    carregarDados();
  }

  // ─── carregar select de membros ───────────────────────────────────────────
  async function carregarMembros() {
    try {
      const r = await fetch(URL_USUARIOS).then(r => r.json());
      const sel = el("relatorioFiltroMembro");
      if (!sel || !r.ok) return;
      (r.dados || []).forEach(u => {
        const opt = document.createElement("option");
        opt.value = u.user_id;
        opt.textContent = u.nome_exibicao || u.user_id;
        sel.appendChild(opt);
      });
    } catch (_) {}
  }

  // ─── carregar dados ───────────────────────────────────────────────────────
  function carregarDados() {
    if (carregando) return;
    carregando = true;

    const corpo = {
      data_inicio: (el("relatorioDataInicio")?.value ?? "").trim() || undefined,
      data_fim: (el("relatorioDataFim")?.value ?? "").trim() || undefined,
      user_id: (el("relatorioFiltroMembro")?.value ?? "").trim() || undefined,
    };

    definirEstadoCarregando(true);

    fetch(URL_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    })
      .then(r => r.json())
      .then(resp => {
        if (!resp.ok) { mostrarErro(resp.mensagem ?? "Erro desconhecido."); return; }
        ultimosDados = resp.dados;
        renderizar(resp.dados);
      })
      .catch(err => mostrarErro("Falha na requisição: " + err.message))
      .finally(() => { carregando = false; definirEstadoCarregando(false); });
  }

  function definirEstadoCarregando(ativo) {
    const btn = el("relatorioBtnCarregar");
    if (btn) { btn.disabled = ativo; btn.textContent = ativo ? "Carregando…" : "Carregar"; }
  }

  function mostrarErro(msg) {
    const area = el("relatorioAreaConteudo");
    if (area) area.innerHTML = `<div class="alert alert-danger">${esc(msg)}</div>`;
  }

  // ─── renderização ─────────────────────────────────────────────────────────
  function renderizar(dados) {
    renderizarCards(dados);
    if (modoAgrupamento === "usuario") renderizarPorUsuario(dados);
    else renderizarPorDia(dados);
  }

  function renderizarCards(dados) {
    const periodo = dados.periodo ?? {};
    const elP = el("relatorioTextoPeriodo");
    if (elP) elP.textContent = `${dataIsoBr(periodo.data_inicio)} a ${dataIsoBr(periodo.data_fim)}`;

    const totH = el("relatorioTotalHoras");
    if (totH) totH.textContent = dados.total_geral_horas ?? "—";

    const totV = el("relatorioTotalValor");
    if (totV) totV.textContent = rs(dados.total_geral_valor ?? 0);

    const totE = el("relatorioTotalEditores");
    if (totE) totE.textContent = String((dados.totais_por_usuario ?? []).length);

    const atu = el("relatorioAtualizado");
    if (atu) atu.textContent = periodo.atualizado_em
      ? new Date(periodo.atualizado_em.replace(" ", "T")).toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
      : "—";
  }

  // ─── badge helpers ────────────────────────────────────────────────────────
  function badgeStatusPagamento(status, pagoLegado) {
    // Aceita o campo novo `status_pagamento` ("pago" | "parcial" | "pendente")
    // e cai no `pago` booleano para compatibilidade com payloads antigos.
    const valor = typeof status === "string" && status
      ? status
      : (pagoLegado ? "pago" : "pendente");
    if (valor === "pago") {
      return '<span class="badge text-bg-success">Pago</span>';
    }
    if (valor === "parcial") {
      return '<span class="badge text-bg-info text-dark" title="Parte das tarefas do dia já está paga; ainda há horas pendentes">Parcial</span>';
    }
    return '<span class="badge text-bg-warning text-dark">Pendente</span>';
  }

  function badgeDivergencia(divergente) {
    return divergente ? ' <span class="badge text-bg-danger" title="Declarado excede trabalhado em mais de 10%">⚠</span>' : "";
  }

  // ─── por usuário ──────────────────────────────────────────────────────────
  function renderizarPorUsuario(dados) {
    const area = el("relatorioAreaConteudo");
    if (!area) return;

    const totais = dados.totais_por_usuario ?? [];
    const linhasBrut = dados.linhas ?? [];

    if (!totais.length) {
      area.innerHTML = `<div class="texto-fraco text-center py-4">Nenhuma declaração encontrada para o período.</div>`;
      return;
    }

    const porUser = {};
    for (const ln of linhasBrut) { (porUser[ln.user_id] = porUser[ln.user_id] || []).push(ln); }

    let html = "";
    for (const tot of totais) {
      const uid = tot.user_id;
      const linhas = (porUser[uid] ?? []).slice().sort((a, b) => b.referencia_data.localeCompare(a.referencia_data));

      const valorHoraStr = tot.valor_hora > 0
        ? `<span class="texto-fraco small">${rs(tot.valor_hora)}/h</span>`
        : `<span class="texto-fraco small">R$/h não definido</span>`;

      // Divergência global do membro
      const divGlobal = tot.segundos_trab_total > 0 && tot.segundos_total > (tot.segundos_trab_total * 1.1);

      html += `
        <article class="cartao-grafite p-3 mb-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <div>
              <div class="fw-bold">${esc(tot.nome_exibicao || tot.user_id)}${divGlobal ? badgeDivergencia(true) : ""}</div>
              <div class="d-flex gap-2 align-items-center mt-1">
                <span class="badge badge-suave">${esc(tot.user_id)}</span>
                ${valorHoraStr}
              </div>
            </div>
            <div class="d-flex gap-3 text-end flex-wrap">
              <div>
                <div class="texto-fraco small">Dias</div>
                <div class="fw-bold">${tot.dias_trabalhados}</div>
              </div>
              <div>
                <div class="texto-fraco small">Trabalhado</div>
                <div class="fw-bold text-success">${esc(tot.trabalhado_formatado || "—")}</div>
              </div>
              <div>
                <div class="texto-fraco small">Declarado</div>
                <div class="fw-bold fs-5">${esc(tot.horas_formatado)}</div>
              </div>
              ${tot.valor_hora > 0 ? `<div>
                <div class="texto-fraco small">Valor</div>
                <div class="fw-bold text-success fs-5">${rs(tot.valor_estimado)}</div>
              </div>` : ""}
            </div>
          </div>
          <div class="table-responsive">
            <table class="table table-dark table-borderless align-middle tabela-suave mb-0 small">
              <thead><tr class="texto-fraco">
                <th style="min-width:110px;">Data</th>
                <th class="text-center">Trabalhado</th>
                <th class="text-center">Declarado</th>
                <th class="text-center">Declarações</th>
                <th class="text-center">Status</th>
                ${tot.valor_hora > 0 ? '<th class="text-end">Valor (R$)</th>' : ""}
              </tr></thead>
              <tbody>`;

      for (const ln of linhas) {
        const ds = diaSemana(ln.referencia_data);
        html += `<tr${ln.divergente ? ' style="background:rgba(220,38,38,.08)"' : ""}>
          <td><span class="badge badge-suave me-1">${esc(ds)}</span>${esc(dataIsoBr(ln.referencia_data))}</td>
          <td class="text-center text-success">${esc(ln.trabalhado_formatado)}</td>
          <td class="text-center fw-semibold">${esc(ln.horas_formatado)}${badgeDivergencia(ln.divergente)}</td>
          <td class="text-center texto-fraco">${ln.total_declaracoes}</td>
          <td class="text-center">${badgeStatusPagamento(ln.status_pagamento, ln.pago)}</td>
          ${tot.valor_hora > 0 ? `<td class="text-end">${rs(ln.valor_estimado)}</td>` : ""}
        </tr>`;
      }

      html += `</tbody></table></div></article>`;
    }

    area.innerHTML = html;
  }

  // ─── por dia ──────────────────────────────────────────────────────────────
  function renderizarPorDia(dados) {
    const area = el("relatorioAreaConteudo");
    if (!area) return;

    const linhas = (dados.linhas ?? []).slice().sort((a, b) => {
      const dc = b.referencia_data.localeCompare(a.referencia_data);
      return dc !== 0 ? dc : a.nome_exibicao.localeCompare(b.nome_exibicao);
    });

    if (!linhas.length) {
      area.innerHTML = `<div class="texto-fraco text-center py-4">Nenhuma declaração encontrada para o período.</div>`;
      return;
    }

    const porData = {};
    for (const ln of linhas) { (porData[ln.referencia_data] = porData[ln.referencia_data] || []).push(ln); }
    const datas = Object.keys(porData).sort((a, b) => b.localeCompare(a));

    const temValor = linhas.some(ln => ln.valor_hora > 0);

    let html = `<article class="cartao-grafite p-3">
      <div class="table-responsive">
        <table class="table table-dark table-borderless align-middle tabela-suave mb-0 small">
          <thead><tr class="texto-fraco">
            <th style="min-width:110px;">Data</th>
            <th style="min-width:180px;">Membro</th>
            <th class="text-center">Trabalhado</th>
            <th class="text-center">Declarado</th>
            <th class="text-center">Declarações</th>
            <th class="text-center">Status</th>
            ${temValor ? '<th class="text-end">Valor (R$)</th>' : ""}
          </tr></thead><tbody>`;

    for (const data of datas) {
      const grupo = porData[data];
      const ds = diaSemana(data);
      const subtotalDecl = grupo.reduce((s, ln) => s + ln.segundos_declarados, 0);
      const subtotalTrab = grupo.reduce((s, ln) => s + (ln.segundos_trabalhados || 0), 0);
      const subtotalVal = grupo.reduce((s, ln) => s + (ln.valor_estimado ?? 0), 0);

      html += `<tr class="border-top border-secondary">
        <td colspan="${temValor ? 7 : 6}" class="py-2">
          <span class="badge badge-suave me-1">${esc(ds)}</span>
          <span class="fw-semibold">${esc(dataIsoBr(data))}</span>
          <span class="texto-fraco ms-2">${grupo.length} membro${grupo.length !== 1 ? "s" : ""} · Trab: ${formatarHHMMSS(subtotalTrab)} · Decl: ${formatarHHMMSS(subtotalDecl)}${temValor ? " · " + rs(subtotalVal) : ""}</span>
        </td>
      </tr>`;

      for (const ln of grupo) {
        html += `<tr${ln.divergente ? ' style="background:rgba(220,38,38,.08)"' : ""}>
          <td class="texto-fraco ps-3">└</td>
          <td>${esc(ln.nome_exibicao || ln.user_id)}</td>
          <td class="text-center text-success">${esc(ln.trabalhado_formatado)}</td>
          <td class="text-center fw-semibold">${esc(ln.horas_formatado)}${badgeDivergencia(ln.divergente)}</td>
          <td class="text-center texto-fraco">${ln.total_declaracoes}</td>
          <td class="text-center">${badgeStatusPagamento(ln.status_pagamento, ln.pago)}</td>
          ${temValor ? `<td class="text-end">${ln.valor_hora > 0 ? rs(ln.valor_estimado) : "—"}</td>` : ""}
        </tr>`;
      }
    }

    html += `</tbody></table></div></article>`;
    area.innerHTML = html;
  }

  // ─── export CSV ───────────────────────────────────────────────────────────
  function exportarCSV() {
    if (!ultimosDados || !(ultimosDados.linhas ?? []).length) {
      window.PainelNucleo?.utilidades?.mostrarAlerta?.("aviso", "Sem dados", "Carregue o relatório antes de exportar.");
      return;
    }

    const linhas = ultimosDados.linhas;
    const header = ["Data", "Membro", "user_id", "Trabalhado", "Declarado", "Declarações", "Pago", "Divergente", "R$/hora", "Valor (R$)"];
    const rows = linhas.map(ln => [
      ln.referencia_data,
      ln.nome_exibicao,
      ln.user_id,
      ln.trabalhado_formatado,
      ln.horas_formatado,
      ln.total_declaracoes,
      (ln.status_pagamento === "pago") ? "Sim" : (ln.status_pagamento === "parcial" ? "Parcial" : "Não"),
      ln.divergente ? "Sim" : "Não",
      String(ln.valor_hora).replace(".", ","),
      String(ln.valor_estimado).replace(".", ","),
    ]);

    const bom = "\uFEFF";
    const csv = bom + [header, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g, '""')}"`).join(";")).join("\n");

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `relatorio_${(el("relatorioDataInicio")?.value || "").replace(/-/g, "")}_${(el("relatorioDataFim")?.value || "").replace(/-/g, "")}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // ─── boot ─────────────────────────────────────────────────────────────────
  let jaInicializado = false;

  function renderizarAbaRelatorio() {
    if (!jaInicializado) { jaInicializado = true; inicializar(); }
    else carregarDados();
  }

  window.PainelAbaRelatorio = { renderizarAbaRelatorio };
})();
