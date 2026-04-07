(function () {
  "use strict";

  const URL_API = "./commands/relatorio/tempo_trabalhado.php";

  // ─── utilidades ───────────────────────────────────────────────────────────
  function esc(v) {
    return String(v ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function dataIsoBr(iso) {
    const m = String(iso ?? "").match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? `${m[3]}/${m[2]}/${m[1]}` : (iso ?? "—");
  }

  function diaSemana(iso) {
    if (!iso) return "";
    const d = new Date(iso + "T12:00:00");
    return d.toLocaleDateString("pt-BR", { weekday: "short" })
      .replace(".", "")
      .toUpperCase();
  }

  function rs(valor) {
    return Number(valor ?? 0).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  }

  function dataHojeIso() {
    const d = new Date();
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
  }

  function dataAddDias(iso, dias) {
    const d = new Date(iso + "T12:00:00");
    d.setDate(d.getDate() + dias);
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, "0"),
      String(d.getDate()).padStart(2, "0"),
    ].join("-");
  }

  // ─── estado ───────────────────────────────────────────────────────────────
  let carregando = false;
  let modoAgrupamento = "usuario"; // "usuario" | "dia"
  let ultimosDados = null;

  // ─── elementos ────────────────────────────────────────────────────────────
  function el(id) { return document.getElementById(id); }

  // ─── inicialização ────────────────────────────────────────────────────────
  function inicializar() {
    const hoje = dataHojeIso();
    const inicio = dataAddDias(hoje, -29);

    const entradaInicio = el("relatorioDataInicio");
    const entradaFim    = el("relatorioDataFim");
    if (entradaInicio) entradaInicio.value = inicio;
    if (entradaFim)    entradaFim.value    = hoje;

    const btnCarregar = el("relatorioBtnCarregar");
    if (btnCarregar) btnCarregar.addEventListener("click", carregarDados);

    const btnAgrupamento = el("relatorioBtnAlternarAgrupamento");
    if (btnAgrupamento) btnAgrupamento.addEventListener("click", () => {
      modoAgrupamento = modoAgrupamento === "usuario" ? "dia" : "usuario";
      btnAgrupamento.textContent =
        modoAgrupamento === "usuario" ? "Agrupar por dia" : "Agrupar por usuário";
      if (ultimosDados) renderizar(ultimosDados);
    });

    carregarDados();
  }

  // ─── carregar dados ───────────────────────────────────────────────────────
  function carregarDados() {
    if (carregando) return;
    carregando = true;

    const dataInicio = (el("relatorioDataInicio")?.value ?? "").trim();
    const dataFim    = (el("relatorioDataFim")?.value    ?? "").trim();

    const corpo = {
      data_inicio: dataInicio || undefined,
      data_fim:    dataFim    || undefined,
    };

    definirEstadoCarregando(true);

    fetch(URL_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    })
      .then((r) => r.json())
      .then((resp) => {
        if (!resp.ok) {
          mostrarErro(resp.mensagem ?? "Erro desconhecido.");
          return;
        }
        ultimosDados = resp.dados;
        renderizar(resp.dados);
      })
      .catch((err) => {
        mostrarErro("Falha na requisição: " + err.message);
      })
      .finally(() => {
        carregando = false;
        definirEstadoCarregando(false);
      });
  }

  function definirEstadoCarregando(ativo) {
    const btn = el("relatorioBtnCarregar");
    if (!btn) return;
    btn.disabled = ativo;
    btn.textContent = ativo ? "Carregando…" : "Carregar";
  }

  function mostrarErro(msg) {
    const area = el("relatorioAreaConteudo");
    if (!area) return;
    area.innerHTML = `<div class="alert alert-danger">${esc(msg)}</div>`;
  }

  // ─── renderização principal ───────────────────────────────────────────────
  function renderizar(dados) {
    renderizarCards(dados);
    if (modoAgrupamento === "usuario") {
      renderizarPorUsuario(dados);
    } else {
      renderizarPorDia(dados);
    }
  }

  // ─── cards de resumo ──────────────────────────────────────────────────────
  function renderizarCards(dados) {
    const periodo = dados.periodo ?? {};
    const textoP  = el("relatorioTextoPeriodo");
    if (textoP) {
      textoP.textContent =
        `${dataIsoBr(periodo.data_inicio)} a ${dataIsoBr(periodo.data_fim)}`;
    }

    const totHoras = el("relatorioTotalHoras");
    if (totHoras) totHoras.textContent = dados.total_geral_horas ?? "—";

    const totValor = el("relatorioTotalValor");
    if (totValor) totValor.textContent = rs(dados.total_geral_valor ?? 0);

    const totEdit  = el("relatorioTotalEditores");
    if (totEdit)  totEdit.textContent  = String((dados.totais_por_usuario ?? []).length);

    const atuEl = el("relatorioAtualizado");
    if (atuEl) atuEl.textContent = periodo.atualizado_em
      ? new Date(periodo.atualizado_em.replace(" ", "T"))
          .toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })
      : "—";
  }

  // ─── por usuário: um bloco por editor ─────────────────────────────────────
  function renderizarPorUsuario(dados) {
    const area = el("relatorioAreaConteudo");
    if (!area) return;

    const totais    = dados.totais_por_usuario ?? [];
    const linhasBrut = dados.linhas           ?? [];

    if (totais.length === 0) {
      area.innerHTML = `<div class="texto-fraco text-center py-4">Nenhuma declaração encontrada para o período.</div>`;
      return;
    }

    // mapear linhas por user_id
    const porUser = {};
    for (const ln of linhasBrut) {
      const uid = ln.user_id;
      if (!porUser[uid]) porUser[uid] = [];
      porUser[uid].push(ln);
    }

    let html = "";

    for (const tot of totais) {
      const uid   = tot.user_id;
      const linhas = (porUser[uid] ?? []).slice().sort((a, b) =>
        b.referencia_data.localeCompare(a.referencia_data)
      );

      const valorHoraStr = tot.valor_hora > 0
        ? `<span class="texto-fraco small">${rs(tot.valor_hora)}/h</span>`
        : `<span class="texto-fraco small">R$/h não definido</span>`;

      html += `
        <article class="cartao-grafite p-3 mb-3">
          <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
            <div>
              <div class="fw-bold">${esc(tot.nome_exibicao || tot.user_id)}</div>
              <div class="d-flex gap-2 align-items-center mt-1">
                <span class="badge badge-suave">${esc(tot.user_id)}</span>
                ${valorHoraStr}
              </div>
            </div>
            <div class="d-flex gap-3 text-end flex-wrap">
              <div>
                <div class="texto-fraco small">Dias trabalhados</div>
                <div class="fw-bold">${tot.dias_trabalhados}</div>
              </div>
              <div>
                <div class="texto-fraco small">Total declarado</div>
                <div class="fw-bold fs-5">${esc(tot.horas_formatado)}</div>
              </div>
              ${tot.valor_hora > 0 ? `
              <div>
                <div class="texto-fraco small">Valor estimado</div>
                <div class="fw-bold text-success fs-5">${rs(tot.valor_estimado)}</div>
              </div>` : ""}
            </div>
          </div>

          <div class="table-responsive">
            <table class="table table-dark table-borderless align-middle tabela-suave mb-0 small">
              <thead>
                <tr class="texto-fraco">
                  <th style="min-width:110px;">Data</th>
                  <th class="text-center" style="min-width:90px;">Tempo</th>
                  <th class="text-center" style="min-width:70px;">Declarações</th>
                  ${tot.valor_hora > 0 ? '<th class="text-end" style="min-width:100px;">Valor (R$)</th>' : ""}
                </tr>
              </thead>
              <tbody>
      `;

      for (const ln of linhas) {
        const ds = diaSemana(ln.referencia_data);
        html += `
                <tr>
                  <td>
                    <span class="badge badge-suave me-1">${esc(ds)}</span>
                    ${esc(dataIsoBr(ln.referencia_data))}
                  </td>
                  <td class="text-center fw-semibold">${esc(ln.horas_formatado)}</td>
                  <td class="text-center texto-fraco">${ln.total_declaracoes}</td>
                  ${tot.valor_hora > 0 ? `<td class="text-end">${rs(ln.valor_estimado)}</td>` : ""}
                </tr>
        `;
      }

      html += `
              </tbody>
            </table>
          </div>
        </article>
      `;
    }

    area.innerHTML = html;
  }

  // ─── por dia: tabela cronológica unificada ────────────────────────────────
  function renderizarPorDia(dados) {
    const area = el("relatorioAreaConteudo");
    if (!area) return;

    const linhas = (dados.linhas ?? []).slice().sort((a, b) => {
      const dc = b.referencia_data.localeCompare(a.referencia_data);
      if (dc !== 0) return dc;
      return a.nome_exibicao.localeCompare(b.nome_exibicao);
    });

    if (linhas.length === 0) {
      area.innerHTML = `<div class="texto-fraco text-center py-4">Nenhuma declaração encontrada para o período.</div>`;
      return;
    }

    // agrupar por data para exibir subtotais
    const porData = {};
    for (const ln of linhas) {
      if (!porData[ln.referencia_data]) porData[ln.referencia_data] = [];
      porData[ln.referencia_data].push(ln);
    }
    const datas = Object.keys(porData).sort((a, b) => b.localeCompare(a));

    // verifica se tem valor_hora para mostrar coluna de R$
    const temValor = linhas.some((ln) => ln.valor_hora > 0);

    let html = `
      <article class="cartao-grafite p-3">
        <div class="table-responsive">
          <table class="table table-dark table-borderless align-middle tabela-suave mb-0 small">
            <thead>
              <tr class="texto-fraco">
                <th style="min-width:110px;">Data</th>
                <th style="min-width:180px;">Membro</th>
                <th class="text-center" style="min-width:90px;">Tempo</th>
                <th class="text-center" style="min-width:70px;">Declarações</th>
                ${temValor ? '<th class="text-end" style="min-width:100px;">Valor (R$)</th>' : ""}
              </tr>
            </thead>
            <tbody>
    `;

    for (const data of datas) {
      const grupo = porData[data];
      const ds = diaSemana(data);
      const subtotalSeg = grupo.reduce((s, ln) => s + ln.segundos_declarados, 0);
      const subtotalVal = grupo.reduce((s, ln) => s + (ln.valor_estimado ?? 0), 0);
      const subtotalH   = formatarHHMMSS(subtotalSeg);

      // separador de data
      html += `
              <tr class="border-top border-secondary">
                <td colspan="${temValor ? 5 : 4}" class="py-2">
                  <span class="badge badge-suave me-1">${esc(ds)}</span>
                  <span class="fw-semibold">${esc(dataIsoBr(data))}</span>
                  <span class="texto-fraco ms-2">${grupo.length} membro${grupo.length !== 1 ? "s" : ""} · ${esc(subtotalH)} total${temValor ? " · " + rs(subtotalVal) : ""}</span>
                </td>
              </tr>
      `;

      for (const ln of grupo) {
        html += `
              <tr>
                <td class="texto-fraco ps-3">└</td>
                <td>${esc(ln.nome_exibicao || ln.user_id)}</td>
                <td class="text-center fw-semibold">${esc(ln.horas_formatado)}</td>
                <td class="text-center texto-fraco">${ln.total_declaracoes}</td>
                ${temValor ? `<td class="text-end">${ln.valor_hora > 0 ? rs(ln.valor_estimado) : "—"}</td>` : ""}
              </tr>
        `;
      }
    }

    html += `
            </tbody>
          </table>
        </div>
      </article>
    `;

    area.innerHTML = html;
  }

  function formatarHHMMSS(seg) {
    seg = Math.max(0, Math.floor(seg));
    const h = Math.floor(seg / 3600);
    const m = Math.floor((seg % 3600) / 60);
    const s = seg % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  // ─── boot ─────────────────────────────────────────────────────────────────
  let jaInicializado = false;

  function renderizarAbaRelatorio() {
    if (!jaInicializado) {
      jaInicializado = true;
      inicializar();
    } else {
      carregarDados();
    }
  }

  // expõe para painel.js (mesmo padrão de PainelAbaGraficos)
  window.PainelAbaRelatorio = { renderizarAbaRelatorio };
})();
