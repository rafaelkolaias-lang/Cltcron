(function () {
  "use strict";

  const urlApiGraficos = "./commands/graficos/graficos.php";
  const seletorAbaGraficos = "#abaGraficos";
  const seletorAreaAlertas = "#areaAlertas";

  let intervaloAutoAtualizacao = null;
  let requisicaoEmAndamento = false;
  let metaCarregada = false;

  function obterElemento(seletor) {
    return document.querySelector(seletor);
  }

  function abaGraficosEstaVisivel() {
    const aba = obterElemento(seletorAbaGraficos);
    return !!aba && !aba.classList.contains("d-none");
  }

  function definirTexto(id, texto) {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = texto;
    }
  }

  function formatarHorasMinutosSegundos(segundos) {
    const total = Math.max(0, Number(segundos || 0));
    const horas = Math.floor(total / 3600);
    const resto = total % 3600;
    const min = Math.floor(resto / 60);
    const seg = Math.floor(resto % 60);
    return `${String(horas).padStart(2, "0")}:${String(min).padStart(2, "0")}:${String(seg).padStart(2, "0")}`;
  }

  function escaparHtml(texto) {
    return String(texto ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function formatarDataHoraBanco(valor) {
    const texto = String(valor || "").trim();
    if (!texto) return "—";

    const partes = texto.split(" ");
    if (partes.length !== 2) return texto;

    const data = partes[0].split("-");
    const hora = partes[1].split(":");

    if (data.length !== 3 || hora.length < 2) {
      return texto;
    }

    return `${data[2]}/${data[1]} ${hora[0]}:${hora[1]}`;
  }

  function formatarStatusAtual(status) {
    const texto = String(status || "").trim().toLowerCase();
    if (texto === "trabalhando") return "Trabalhando";
    if (texto === "ocioso") return "Ocioso";
    if (texto === "pausado") return "Pausado";
    return "Sem status";
  }

  function classeBadgeStatusAtual(status) {
    const texto = String(status || "").trim().toLowerCase();
    if (texto === "trabalhando") return "bg-success";
    if (texto === "ocioso") return "bg-warning text-dark";
    if (texto === "pausado") return "bg-secondary";
    return "bg-dark";
  }

  function mostrarAlerta(tipo, titulo, mensagem) {
    const area = obterElemento(seletorAreaAlertas);
    if (!area) return;

    const classe =
      tipo === "sucesso"
        ? "alert-success"
        : tipo === "aviso"
          ? "alert-warning"
          : "alert-danger";

    const html = `
      <div class="alert ${classe} alert-dismissible fade show" role="alert">
        <strong>${escaparHtml(titulo)}</strong> ${escaparHtml(mensagem)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Fechar"></button>
      </div>
    `;
    area.insertAdjacentHTML("afterbegin", html);
  }

  function obterDataHojeIso() {
    const agora = new Date();
    const ano = agora.getFullYear();
    const mes = String(agora.getMonth() + 1).padStart(2, "0");
    const dia = String(agora.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  }

  function subtrairDiasIso(dataIso, quantidadeDias) {
    const partes = String(dataIso).split("-");
    if (partes.length !== 3) return dataIso;

    const data = new Date(Number(partes[0]), Number(partes[1]) - 1, Number(partes[2]));
    data.setDate(data.getDate() - Number(quantidadeDias || 0));

    const ano = data.getFullYear();
    const mes = String(data.getMonth() + 1).padStart(2, "0");
    const dia = String(data.getDate()).padStart(2, "0");
    return `${ano}-${mes}-${dia}`;
  }

  async function requisitarJson(url, corpoObjeto) {
    const resposta = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify(corpoObjeto || {}),
      cache: "no-store",
    });

    const texto = await resposta.text();

    let json = null;
    try {
      json = JSON.parse(texto);
    } catch (erroConversao) {
      throw new Error("Resposta inválida do servidor.");
    }

    if (!resposta.ok || !json || json.ok !== true) {
      const mensagem = json && json.mensagem ? json.mensagem : "Falha ao buscar dados.";
      throw new Error(mensagem);
    }

    return json.dados;
  }

  function obterValoresSelectMultiple(idSelect) {
    const el = document.getElementById(idSelect);
    if (!el) return [];

    return Array.from(el.selectedOptions)
      .map((opcao) => String(opcao.value || ""))
      .filter((valor) => valor !== "");
  }

  function preencherSelectMultiple(idSelect, itens, valorCampo, textoCampo) {
    const el = document.getElementById(idSelect);
    if (!el) return;

    el.innerHTML = "";
    (itens || []).forEach((item) => {
      const valor = String(item[valorCampo] ?? "");
      const texto = String(item[textoCampo] ?? valor);
      if (!valor) return;

      const opt = document.createElement("option");
      opt.value = valor;
      opt.textContent = texto;
      el.appendChild(opt);
    });
  }

  function preencherSelectApps(idSelect, apps) {
    const el = document.getElementById(idSelect);
    if (!el) return;

    el.innerHTML = "";
    (apps || []).forEach((nome) => {
      const valor = String(nome || "");
      if (!valor) return;

      const opt = document.createElement("option");
      opt.value = valor;
      opt.textContent = valor;
      el.appendChild(opt);
    });
  }

  function garantirDatasPadrao() {
    const dataFimEl = document.getElementById("filtroGraficosDataFim");
    const dataInicioEl = document.getElementById("filtroGraficosDataInicio");

    if (!dataFimEl || !dataInicioEl) return;

    if (!dataFimEl.value) {
      dataFimEl.value = obterDataHojeIso();
    }

    if (!dataInicioEl.value) {
      dataInicioEl.value = subtrairDiasIso(dataFimEl.value, 6);
    }
  }

  function obterFiltrosDaTela() {
    garantirDatasPadrao();

    return {
      data_inicio: (document.getElementById("filtroGraficosDataInicio") || {}).value || "",
      data_fim: (document.getElementById("filtroGraficosDataFim") || {}).value || "",
      usuarios: obterValoresSelectMultiple("filtroGraficosUsuarios"),
      apps: obterValoresSelectMultiple("filtroGraficosApps"),
      usuario_detalhe: (document.getElementById("filtroGraficosUsuarioDetalhe") || {}).value || "",
    };
  }

  function garantirEstruturaSimplificada() {
    const aba = document.querySelector(seletorAbaGraficos);
    if (!aba) return;
    if (document.getElementById("painelGraficosSimplificado")) return;

    aba.innerHTML = `
      <div id="painelGraficosSimplificado" class="container-fluid px-0">
        <div class="row g-3 mb-3">
          <div class="col-12">
            <div class="cartao-grafite p-3">
              <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <div>
                  <h5 class="mb-1">Uso de apps por usuário</h5>
                  <div class="texto-fraco small">
                    Visão do dono: status atual, atividade atual, apps abertos agora, resumo por app e períodos exatos.
                  </div>
                </div>
                <div class="small texto-fraco">
                  Atualizado em: <span id="textoGraficosUltimaAtualizacao">—</span>
                </div>
              </div>

              <div class="row g-3">
                <div class="col-12 col-lg-3">
                  <label class="form-label small fw-semibold">Data início</label>
                  <input type="date" id="filtroGraficosDataInicio" class="form-control bg-transparent text-white border-secondary">
                </div>

                <div class="col-12 col-lg-3">
                  <label class="form-label small fw-semibold">Data fim</label>
                  <input type="date" id="filtroGraficosDataFim" class="form-control bg-transparent text-white border-secondary">
                </div>

                <div class="col-12 col-lg-3">
                  <label class="form-label small fw-semibold">Filtrar usuários</label>
                  <select id="filtroGraficosUsuarios" class="form-select bg-transparent text-white border-secondary" multiple size="4"></select>
                </div>

                <div class="col-12 col-lg-3">
                  <label class="form-label small fw-semibold">Filtrar apps</label>
                  <select id="filtroGraficosApps" class="form-select bg-transparent text-white border-secondary" multiple size="4"></select>
                </div>

                <div class="col-12 col-lg-4">
                  <label class="form-label small fw-semibold">Ver detalhe de qual usuário</label>
                  <select id="filtroGraficosUsuarioDetalhe" class="form-select bg-transparent text-white border-secondary"></select>
                </div>
              </div>

              <div class="mt-3 d-flex flex-wrap gap-2">
                <button type="button" id="botaoAplicarFiltrosGraficos" class="btn btn-light botao-mini">
                  Aplicar filtros
                </button>
                <button type="button" id="botaoLimparFiltrosGraficos" class="btn btn-outline-light botao-mini">
                  Limpar filtros
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-6 col-lg-2">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Usuários com dados</div>
              <div class="fs-4 fw-bold" id="numeroResumoUsuarios">0</div>
            </div>
          </div>

          <div class="col-6 col-lg-2">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Apps abertos agora</div>
              <div class="fs-4 fw-bold" id="numeroResumoAppsAbertosAgora">0</div>
            </div>
          </div>

          <div class="col-6 col-lg-2">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Tempo total em apps</div>
              <div class="fs-6 fw-bold texto-mono" id="textoResumoTempoApps">00:00:00</div>
            </div>
          </div>

          <div class="col-6 col-lg-2">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Tempo em foco</div>
              <div class="fs-6 fw-bold texto-mono" id="textoResumoTempoFoco">00:00:00</div>
            </div>
          </div>

          <div class="col-6 col-lg-2">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">2º plano</div>
              <div class="fs-6 fw-bold texto-mono" id="textoResumoTempoSegundoPlano">00:00:00</div>
            </div>
          </div>

          <div class="col-6 col-lg-2">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Tempo pausado</div>
              <div class="fs-6 fw-bold texto-mono" id="textoResumoTempoPausado">00:00:00</div>
            </div>
          </div>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-6 col-lg-3">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Trabalhando agora</div>
              <div class="fs-4 fw-bold text-success" id="numeroResumoTrabalhandoAgora">0</div>
            </div>
          </div>

          <div class="col-6 col-lg-3">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Ociosos agora</div>
              <div class="fs-4 fw-bold text-warning" id="numeroResumoOciososAgora">0</div>
            </div>
          </div>

          <div class="col-6 col-lg-3">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Pausados agora</div>
              <div class="fs-4 fw-bold" id="numeroResumoPausadosAgora">0</div>
            </div>
          </div>

          <div class="col-6 col-lg-3">
            <div class="cartao-grafite p-3 h-100">
              <div class="texto-fraco small">Sem status</div>
              <div class="fs-4 fw-bold texto-fraco" id="numeroResumoSemStatusAgora">0</div>
            </div>
          </div>
        </div>

        <div class="row g-3 mb-3">
          <div class="col-12">
            <div class="cartao-grafite p-3">
              <div class="d-flex justify-content-between align-items-center mb-3">
                <h6 class="mb-0">Resumo de todos os usuários</h6>
                <div class="texto-fraco small">Veja quem está fazendo o quê agora.</div>
              </div>

              <div class="table-responsive tabela-limite" style="max-height: 420px;">
                <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
                  <thead>
                    <tr class="texto-fraco small">
                      <th>Usuário</th>
                      <th>Status atual</th>
                      <th>Atividade atual</th>
                      <th class="text-end">Apps agora</th>
                      <th class="text-end">Apps usados</th>
                      <th class="text-end">Tempo em apps</th>
                      <th class="text-end">Tempo foco</th>
                      <th>App principal</th>
                    </tr>
                  </thead>
                  <tbody id="tbodyResumoUsuariosGraficos">
                    <tr>
                      <td colspan="8" class="texto-fraco">Carregando…</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <div id="areaUsuarioSelecionadoGraficos" class="row g-3">
          <div class="col-12">
            <div class="cartao-grafite p-3">
              <div class="texto-fraco">Selecione um usuário para ver os detalhes.</div>
            </div>
          </div>
        </div>

        <div class="row g-3 mt-1">
          <div class="col-12">
            <div class="cartao-grafite p-3">
              <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
                <div>
                  <h6 class="mb-1">Tempo Declarado pelos Editores</h6>
                  <div class="texto-fraco small">Apenas o tempo que o editor declarou como trabalhado — sem ocioso, sem pausa.</div>
                </div>
                <span class="badge badge-suave">declarado</span>
              </div>

              <div class="row g-2 mb-3" id="cardsDeclarado">
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;" class="p-3">
                    <div class="texto-fraco small">Total declarado (período)</div>
                    <div class="fs-5 fw-bold texto-mono" id="declTotalHoras">—</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;" class="p-3">
                    <div class="texto-fraco small">Valor estimado total</div>
                    <div class="fs-5 fw-bold text-success" id="declTotalValor">—</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;" class="p-3">
                    <div class="texto-fraco small">Editores com declarações</div>
                    <div class="fs-5 fw-bold" id="declTotalEditores">—</div>
                  </div>
                </div>
                <div class="col-6 col-md-3">
                  <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;" class="p-3">
                    <div class="texto-fraco small">Período</div>
                    <div class="fw-bold small" id="declPeriodo">—</div>
                  </div>
                </div>
              </div>

              <div id="areaDeclaradoPorUsuario">
                <div class="texto-fraco small">Carregando declarações…</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  async function carregarMetaFiltros() {
    if (metaCarregada) return;

    const dadosMeta = await requisitarJson(urlApiGraficos, { acao: "meta" });

    const usuarios = Array.isArray(dadosMeta.usuarios) ? dadosMeta.usuarios : [];
    const apps = Array.isArray(dadosMeta.apps) ? dadosMeta.apps : [];

    const usuariosFormatados = usuarios
      .map((u) => ({
        user_id: String(u.user_id || ""),
        texto: `${String(u.nome_exibicao || u.user_id || "—")} (${String(u.status_conta || "—")})`
      }))
      .filter((u) => u.user_id !== "");

    preencherSelectMultiple("filtroGraficosUsuarios", usuariosFormatados, "user_id", "texto");
    preencherSelectApps("filtroGraficosApps", apps);

    const selectDetalhe = document.getElementById("filtroGraficosUsuarioDetalhe");
    if (selectDetalhe) {
      selectDetalhe.innerHTML = `<option value="">Selecione...</option>`;
      usuariosFormatados.forEach((usuario) => {
        const opt = document.createElement("option");
        opt.value = usuario.user_id;
        opt.textContent = usuario.texto;
        selectDetalhe.appendChild(opt);
      });
    }

    metaCarregada = true;
  }

  function montarResumoGeral(dadosPainel) {
    const resumo = dadosPainel.resumo_geral || {};
    const statusAtual = resumo.status_atual || {};

    definirTexto("numeroResumoUsuarios", String(resumo.usuarios_com_dados || 0));
    definirTexto("numeroResumoAppsAbertosAgora", String(resumo.apps_abertos_agora_total || 0));
    definirTexto("textoResumoTempoApps", formatarHorasMinutosSegundos(resumo.segundos_total_apps || 0));
    definirTexto("textoResumoTempoFoco", formatarHorasMinutosSegundos(resumo.segundos_total_foco || 0));
    definirTexto("textoResumoTempoSegundoPlano", formatarHorasMinutosSegundos(resumo.segundos_total_segundo_plano || 0));
    definirTexto("textoResumoTempoPausado", formatarHorasMinutosSegundos(resumo.segundos_pausado_total || 0));

    definirTexto("numeroResumoTrabalhandoAgora", String(statusAtual.trabalhando || 0));
    definirTexto("numeroResumoOciososAgora", String(statusAtual.ocioso || 0));
    definirTexto("numeroResumoPausadosAgora", String(statusAtual.pausado || 0));
    definirTexto("numeroResumoSemStatusAgora", String(statusAtual.sem_status || 0));
  }

  function montarTabelaResumoUsuarios(dadosPainel) {
    const tbody = document.getElementById("tbodyResumoUsuariosGraficos");
    if (!tbody) return;

    const usuarios = Array.isArray(dadosPainel.usuarios) ? dadosPainel.usuarios : [];

    if (!usuarios.length) {
      tbody.innerHTML = `<tr><td colspan="8" class="texto-fraco">Sem dados para os filtros selecionados.</td></tr>`;
      return;
    }

    tbody.innerHTML = usuarios.map((usuario) => {
      const statusAtual = formatarStatusAtual(usuario.status_atual || "");
      const classeStatus = classeBadgeStatusAtual(usuario.status_atual || "");
      const atividadeAtual = String(usuario.atividade_atual || "").trim() || "—";
      const appPrincipal = String(usuario.app_principal || "").trim() || "—";

      return `
        <tr>
          <td>
            <div class="fw-semibold">${escaparHtml(usuario.nome_exibicao || usuario.user_id || "—")}</div>
            <div class="text-muted small">${escaparHtml(usuario.user_id || "—")}</div>
          </td>
          <td>
            <span class="badge ${classeStatus}">${escaparHtml(statusAtual)}</span>
          </td>
          <td>${escaparHtml(atividadeAtual)}</td>
          <td class="text-end">${Number(usuario.quantidade_apps_abertos_agora || 0)}</td>
          <td class="text-end">${Number(usuario.quantidade_apps_usados || 0)}</td>
          <td class="text-end text-nowrap">${escaparHtml(formatarHorasMinutosSegundos(usuario.segundos_total_apps || 0))}</td>
          <td class="text-end text-nowrap">${escaparHtml(formatarHorasMinutosSegundos(usuario.segundos_total_foco || 0))}</td>
          <td>${escaparHtml(appPrincipal)}</td>
        </tr>
      `;
    }).join("");
  }

  function montarHtmlAppsAbertosAgora(appsAbertosAgora) {
    if (!Array.isArray(appsAbertosAgora) || appsAbertosAgora.length === 0) {
      return `<div class="text-muted small">Nenhum app aberto agora.</div>`;
    }

    return `
      <div class="d-flex flex-column gap-2">
        ${appsAbertosAgora.map((app) => `
          <div style="background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.10);border-radius:8px;" class="p-2">
            <div class="fw-semibold">${escaparHtml(app.nome_app || "—")}</div>
            <div class="small texto-fraco">${escaparHtml(app.titulo_janela || "Sem título")}</div>
            <div class="small texto-fraco">Aberto desde ${escaparHtml(formatarDataHoraBanco(app.inicio_em))}</div>
          </div>
        `).join("")}
      </div>
    `;
  }

  function montarHtmlTabelaResumoApps(appsResumo) {
    if (!Array.isArray(appsResumo) || appsResumo.length === 0) {
      return `<div class="text-muted small">Sem apps usados no período para este usuário.</div>`;
    }

    return `
      <div class="table-responsive">
        <table class="table table-dark table-borderless align-middle tabela-suave mb-0">
          <thead>
            <tr class="texto-fraco small">
              <th>App</th>
              <th class="text-end">Aberto</th>
              <th class="text-end">Foco</th>
              <th class="text-end">2º plano</th>
              <th>Primeiro uso</th>
              <th>Último uso</th>
            </tr>
          </thead>
          <tbody>
            ${appsResumo.map((app) => `
              <tr>
                <td class="fw-semibold">${escaparHtml(app.nome_app || "—")}</td>
                <td class="text-end text-nowrap texto-mono">${escaparHtml(formatarHorasMinutosSegundos(app.segundos_total_aberto || 0))}</td>
                <td class="text-end text-nowrap texto-mono">${escaparHtml(formatarHorasMinutosSegundos(app.segundos_em_foco || 0))}</td>
                <td class="text-end text-nowrap texto-mono">${escaparHtml(formatarHorasMinutosSegundos(app.segundos_segundo_plano || 0))}</td>
                <td class="text-nowrap texto-fraco small">${escaparHtml(formatarDataHoraBanco(app.primeiro_uso_em))}</td>
                <td class="text-nowrap texto-fraco small">${escaparHtml(formatarDataHoraBanco(app.ultimo_uso_em))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function montarHtmlTabelaPeriodos(periodos) {
    if (!Array.isArray(periodos) || periodos.length === 0) {
      return `<div class="text-muted small">Sem períodos de foco no período.</div>`;
    }

    return `
      <div class="table-responsive" style="max-height: 360px;">
        <table class="table table-dark table-borderless align-middle tabela-suave mb-0 cabecalho-tabela-sticky">
          <thead>
            <tr class="texto-fraco small">
              <th>App</th>
              <th>Janela</th>
              <th>Início</th>
              <th>Fim</th>
              <th class="text-end">Duração</th>
            </tr>
          </thead>
          <tbody>
            ${periodos.map((periodo) => `
              <tr>
                <td class="fw-semibold">${escaparHtml(periodo.nome_app || "—")}</td>
                <td class="texto-fraco small">${escaparHtml(periodo.titulo_janela || "—")}</td>
                <td class="text-nowrap texto-fraco small">${escaparHtml(formatarDataHoraBanco(periodo.inicio_em))}</td>
                <td class="text-nowrap">${periodo.aberto_agora ? '<span class="badge bg-success">Aberto agora</span>' : '<span class="texto-fraco small">' + escaparHtml(formatarDataHoraBanco(periodo.fim_em)) + '</span>'}</td>
                <td class="text-end text-nowrap texto-mono">${escaparHtml(formatarHorasMinutosSegundos(periodo.segundos_periodo || 0))}</td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function montarUsuarioSelecionado(dadosPainel, userIdSelecionado) {
    const area = document.getElementById("areaUsuarioSelecionadoGraficos");
    if (!area) return;

    const usuarios = Array.isArray(dadosPainel.usuarios) ? dadosPainel.usuarios : [];

    let usuario = null;
    if (userIdSelecionado) {
      usuario = usuarios.find((item) => String(item.user_id || "") === String(userIdSelecionado));
    }

    if (!usuario && usuarios.length > 0) {
      usuario = usuarios[0];
      const select = document.getElementById("filtroGraficosUsuarioDetalhe");
      if (select) {
        select.value = String(usuario.user_id || "");
      }
    }

    if (!usuario) {
      area.innerHTML = `
        <div class="col-12">
          <div class="cartao-grafite p-3">
            <div class="texto-fraco">Sem dados para os filtros selecionados.</div>
          </div>
        </div>
      `;
      return;
    }

    const statusAtual = formatarStatusAtual(usuario.status_atual || "");
    const classeStatus = classeBadgeStatusAtual(usuario.status_atual || "");
    const atividadeAtual = String(usuario.atividade_atual || "").trim() || "—";
    const statusDesde = formatarDataHoraBanco(usuario.status_desde_em || "");
    const statusUltimo = formatarDataHoraBanco(usuario.status_ultimo_em || "");

    area.innerHTML = `
      <div class="col-12">
        <div class="cartao-grafite p-3">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-3 mb-3">
            <div>
              <h5 class="mb-1">${escaparHtml(usuario.nome_exibicao || usuario.user_id || "—")}</h5>
              <div class="texto-fraco small">Usuário: ${escaparHtml(usuario.user_id || "—")}</div>
              <div class="mt-2">
                <span class="badge ${classeStatus}">${escaparHtml(statusAtual)}</span>
              </div>
            </div>

            <div class="d-flex flex-wrap gap-3">
              <div class="linha-detalhe">
                <div class="texto-fraco small">Atividade atual</div>
                <div class="fw-semibold">${escaparHtml(atividadeAtual)}</div>
              </div>
              <div class="linha-detalhe">
                <div class="texto-fraco small">Desde</div>
                <div class="fw-semibold texto-mono small">${escaparHtml(statusDesde)}</div>
              </div>
              <div class="linha-detalhe">
                <div class="texto-fraco small">Última atualização</div>
                <div class="fw-semibold texto-mono small">${escaparHtml(statusUltimo)}</div>
              </div>
              <div class="linha-detalhe">
                <div class="texto-fraco small">Pausado</div>
                <div class="fw-semibold texto-mono">${escaparHtml(formatarHorasMinutosSegundos(usuario.segundos_pausado_total || 0))}</div>
              </div>
              <div class="linha-detalhe">
                <div class="texto-fraco small">Total em apps</div>
                <div class="fw-semibold texto-mono">${escaparHtml(formatarHorasMinutosSegundos(usuario.segundos_total_apps || 0))}</div>
              </div>
              <div class="linha-detalhe">
                <div class="texto-fraco small">Tempo em foco</div>
                <div class="fw-semibold texto-mono">${escaparHtml(formatarHorasMinutosSegundos(usuario.segundos_total_foco || 0))}</div>
              </div>
              <div class="linha-detalhe">
                <div class="texto-fraco small">Apps abertos agora</div>
                <div class="fw-semibold">${Number(usuario.quantidade_apps_abertos_agora || 0)}</div>
              </div>
            </div>
          </div>

          <div class="row g-3">
            <div class="col-12 col-xl-4">
              <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;" class="p-3 h-100">
                <div class="fw-semibold mb-2">Apps abertos agora</div>
                ${montarHtmlAppsAbertosAgora(usuario.apps_abertos_agora || [])}
              </div>
            </div>

            <div class="col-12 col-xl-8">
              <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;" class="p-3 h-100">
                <div class="fw-semibold mb-2">Resumo por app</div>
                ${montarHtmlTabelaResumoApps(usuario.apps_resumo || [])}
              </div>
            </div>

            <div class="col-12">
              <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;" class="p-3">
                <div class="fw-semibold mb-2">Períodos exatos de uso</div>
                ${montarHtmlTabelaPeriodos(usuario.periodos_foco || [])}
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ─── Tempo Declarado ──────────────────────────────────────────────────────

  function formatarRs(valor) {
    return Number(valor ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

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
    area.innerHTML = `<div class="texto-fraco small">Carregando declarações…</div>`;

    try {
      const dados = await requisitarJson("./commands/relatorio/tempo_trabalhado.php", {
        data_inicio: filtros.data_inicio,
        data_fim: filtros.data_fim,
        usuarios: filtros.usuarios,
      });
      renderizarTempoDeclarado(dados);
    } catch (e) {
      area.innerHTML = `<div class="texto-fraco small text-danger">Erro ao carregar declarações: ${escaparHtml(e.message)}</div>`;
    }
  }

  function renderizarTempoDeclarado(dados) {
    const area = document.getElementById("areaDeclaradoPorUsuario");
    if (!area) return;

    // cards de resumo
    const periodo = dados.periodo ?? {};
    definirTexto("declTotalHoras", dados.total_geral_horas ?? "—");
    definirTexto("declTotalValor", formatarRs(dados.total_geral_valor ?? 0));
    definirTexto("declTotalEditores", String((dados.totais_por_usuario ?? []).length));
    const elP = document.getElementById("declPeriodo");
    if (elP) {
      const di = String(periodo.data_inicio ?? "").slice(8, 10) + "/" + String(periodo.data_inicio ?? "").slice(5, 7);
      const df = String(periodo.data_fim ?? "").slice(8, 10) + "/" + String(periodo.data_fim ?? "").slice(5, 7);
      elP.textContent = di && df ? `${di} → ${df}` : "—";
    }

    const totais    = dados.totais_por_usuario ?? [];
    const linhasRaw = dados.linhas ?? [];

    if (!totais.length) {
      area.innerHTML = `<div class="texto-fraco small">Nenhuma declaração encontrada para o período.</div>`;
      return;
    }

    // mapear linhas por user_id
    const porUser = {};
    for (const ln of linhasRaw) {
      if (!porUser[ln.user_id]) porUser[ln.user_id] = [];
      porUser[ln.user_id].push(ln);
    }

    let html = `<div class="d-flex flex-column gap-3">`;

    for (const tot of totais) {
      const linhas = (porUser[tot.user_id] ?? []).slice()
        .sort((a, b) => b.referencia_data.localeCompare(a.referencia_data));

      const temValor = tot.valor_hora > 0;
      const barraMax = totais[0].segundos_total || 1;
      const pct = Math.round((tot.segundos_total / barraMax) * 100);

      html += `
        <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:10px;" class="p-3">
          <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-2">
            <div>
              <div class="fw-semibold">${escaparHtml(tot.nome_exibicao || tot.user_id)}</div>
              <div class="texto-fraco small">${escaparHtml(tot.user_id)}${temValor ? ` · ${formatarRs(tot.valor_hora)}/h` : ""}</div>
            </div>
            <div class="d-flex gap-3 text-end">
              <div>
                <div class="texto-fraco small">Dias</div>
                <div class="fw-bold">${tot.dias_trabalhados}</div>
              </div>
              <div>
                <div class="texto-fraco small">Total declarado</div>
                <div class="fw-bold fs-6 texto-mono">${escaparHtml(tot.horas_formatado)}</div>
              </div>
              ${temValor ? `<div>
                <div class="texto-fraco small">A pagar</div>
                <div class="fw-bold text-success">${formatarRs(tot.valor_estimado)}</div>
              </div>` : ""}
            </div>
          </div>

          <div style="height:4px;background:rgba(255,255,255,.08);border-radius:2px;" class="mb-3">
            <div style="height:4px;width:${pct}%;background:#4ade80;border-radius:2px;"></div>
          </div>

          <div class="table-responsive">
            <table class="table table-dark table-borderless align-middle mb-0 small" style="font-size:.82rem;">
              <thead>
                <tr class="texto-fraco" style="border-bottom:1px solid rgba(255,255,255,.06);">
                  <th style="min-width:110px;">Data</th>
                  <th class="text-center">Tempo</th>
                  <th class="text-center">Registros</th>
                  ${temValor ? '<th class="text-end">Valor</th>' : ""}
                </tr>
              </thead>
              <tbody>
                ${linhas.map((ln) => `
                  <tr>
                    <td>${dataIsoBrCurta(ln.referencia_data)}</td>
                    <td class="text-center fw-semibold texto-mono">${escaparHtml(ln.horas_formatado)}</td>
                    <td class="text-center texto-fraco">${ln.total_declaracoes}</td>
                    ${temValor ? `<td class="text-end">${formatarRs(ln.valor_estimado)}</td>` : ""}
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }

    html += `</div>`;
    area.innerHTML = html;
  }

  // ──────────────────────────────────────────────────────────────────────────

  async function atualizarGraficosSimplificados() {
    if (!abaGraficosEstaVisivel()) return;
    if (requisicaoEmAndamento) return;

    requisicaoEmAndamento = true;

    try {
      garantirEstruturaSimplificada();
      await carregarMetaFiltros();

      const filtros = obterFiltrosDaTela();

      const [dadosPainel] = await Promise.all([
        requisitarJson(urlApiGraficos, {
          acao: "painel",
          data_inicio: filtros.data_inicio,
          data_fim: filtros.data_fim,
          usuarios: filtros.usuarios,
          apps: filtros.apps,
        }),
        carregarTempoDeclarado(filtros),
      ]);

      definirTexto("textoGraficosUltimaAtualizacao", formatarDataHoraBanco(dadosPainel.atualizado_em));
      montarResumoGeral(dadosPainel);
      montarTabelaResumoUsuarios(dadosPainel);
      montarUsuarioSelecionado(dadosPainel, filtros.usuario_detalhe);
    } catch (erro) {
      mostrarAlerta("erro", "Gráficos:", String(erro && erro.message ? erro.message : erro));
    } finally {
      requisicaoEmAndamento = false;
    }
  }

  function limparFiltros() {
    const dataFim = document.getElementById("filtroGraficosDataFim");
    const dataInicio = document.getElementById("filtroGraficosDataInicio");
    const usuarios = document.getElementById("filtroGraficosUsuarios");
    const apps = document.getElementById("filtroGraficosApps");
    const usuarioDetalhe = document.getElementById("filtroGraficosUsuarioDetalhe");

    if (dataFim) dataFim.value = obterDataHojeIso();
    if (dataInicio) dataInicio.value = subtrairDiasIso(obterDataHojeIso(), 6);

    if (usuarios) {
      Array.from(usuarios.options).forEach((opcao) => {
        opcao.selected = false;
      });
    }

    if (apps) {
      Array.from(apps.options).forEach((opcao) => {
        opcao.selected = false;
      });
    }

    if (usuarioDetalhe) {
      usuarioDetalhe.value = "";
    }
  }

  function configurarGatilhos() {
    const links = document.querySelectorAll('#menuAbas a[data-aba]');
    links.forEach((link) => {
      link.addEventListener("click", function () {
        const aba = link.getAttribute("data-aba");
        if (aba === "abaGraficos") {
          setTimeout(atualizarGraficosSimplificados, 80);
        }
      });
    });

    document.addEventListener("click", function (evento) {
      const alvo = evento.target;

      if (alvo && alvo.id === "botaoAplicarFiltrosGraficos") {
        atualizarGraficosSimplificados();
      }

      if (alvo && alvo.id === "botaoLimparFiltrosGraficos") {
        limparFiltros();
        atualizarGraficosSimplificados();
      }
    });

    document.addEventListener("change", function (evento) {
      const alvo = evento.target;
      if (alvo && alvo.id === "filtroGraficosUsuarioDetalhe") {
        atualizarGraficosSimplificados();
      }
    });
  }

  function iniciarAutoAtualizacao() {
    pararAutoAtualizacao();
    intervaloAutoAtualizacao = setInterval(function () {
      if (abaGraficosEstaVisivel()) {
        atualizarGraficosSimplificados();
      }
    }, 30000);
  }

  function pararAutoAtualizacao() {
    if (intervaloAutoAtualizacao) {
      clearInterval(intervaloAutoAtualizacao);
      intervaloAutoAtualizacao = null;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    garantirEstruturaSimplificada();
    garantirDatasPadrao();
    configurarGatilhos();
    iniciarAutoAtualizacao();

    if (abaGraficosEstaVisivel()) {
      atualizarGraficosSimplificados();
    }
  });
})();