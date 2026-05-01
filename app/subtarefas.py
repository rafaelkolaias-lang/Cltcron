"""Janela "Tarefas da Atividade" / "Declarar Tarefa"."""
from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from datetime import date, datetime
from tkinter import messagebox, ttk

from declaracoes_dia import RepositorioDeclaracoesDia

from app.win32_utils import formatar_hhmmss


class JanelaSubtarefas(tk.Toplevel):
    def __init__(
        self,
        mestre: tk.Misc,
        repositorio: RepositorioDeclaracoesDia,
        usuario: dict[str, str],
        id_atividade: int,
        titulo_atividade: str,
        *,
        segundos_trabalhando: int = 0,
        segundos_pausado: int = 0,
        modo_finalizacao: bool = False,
        ao_finalizar: Callable[[str], None] | None = None,
        opcoes_canal: list[str] | None = None,
    ) -> None:
        super().__init__(mestre)
        self.title("Tarefas da Atividade")
        self.geometry("1220x800")
        self.minsize(980, 700)
        self.transient(mestre)
        self.grab_set()
        self.configure(bg="#111111")

        self._repositorio = repositorio
        self._usuario = usuario
        self._id_atividade = int(id_atividade)
        self._titulo_atividade = (titulo_atividade or "").strip()
        self._opcoes_canal: list[str] = opcoes_canal or []
        self._segundos_trabalhando = int(segundos_trabalhando or 0)
        self._segundos_pausado = int(segundos_pausado or 0)
        self._modo_finalizacao = bool(modo_finalizacao)
        self._ao_finalizar = ao_finalizar
        self._referencia_data = date.today()

        self._subtarefas: list[object] = []
        self._mapa_subtarefas: dict[int, object] = {}
        self._travado_ate_cache: object = None  # date | None — atualizado a cada reload
        self._id_subtarefa_criada_nesta_janela: int | None = None  # evita duplicação ao reter erro

        # Ordenação manual triestada
        self._sort_col: str | None = None
        self._sort_dir: str = "asc"
        self._lista_base_ordenacao: list[tuple] = []

        self._var_resumo = tk.StringVar(value="")
        self._var_trava = tk.StringVar(value="Carregando...")

        self._montar_tela()

        # Bloqueios e abatimentos de pagamento são gravados pelo painel web
        # (painel/commands/pagamentos/_aplicar_pagamento.php) no momento do pagamento.
        # O desktop apenas lê — não precisa sincronizar nada na abertura.

        self._recarregar_dados()

    def _usuario_id(self) -> str:
        return str(self._usuario.get("user_id") or "").strip()

    def _executar_em_background(
        self,
        funcao: Callable[[], object],
        ao_concluir: Callable[[object], None],
        ao_falhar: Callable[[Exception], None] | None = None,
    ) -> None:
        def _em_thread() -> None:
            try:
                resultado = funcao()

                def _despachar(r: object = resultado) -> None:
                    try:
                        if self.winfo_exists():
                            ao_concluir(r)
                    except Exception:
                        pass

                self.after(0, _despachar)
            except Exception as erro:
                def _despachar_erro(e: Exception = erro) -> None:
                    try:
                        if self.winfo_exists():
                            if ao_falhar:
                                ao_falhar(e)
                            else:
                                messagebox.showerror("Erro", str(e), parent=self)
                    except Exception:
                        pass

                self.after(0, _despachar_erro)

        threading.Thread(target=_em_thread, daemon=True).start()

    def _montar_tela(self) -> None:
        quadro = ttk.Frame(self, padding=14)
        quadro.pack(fill="both", expand=True)

        topo = ttk.Frame(quadro)
        topo.pack(fill="x")

        ttk.Label(
            topo,
            text=f"Atividade principal: {self._titulo_atividade}",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            topo,
            text=(
                f"Data: {self._referencia_data.strftime('%d/%m/%Y')}    |    "
                f"Trabalhado: {formatar_hhmmss(self._segundos_trabalhando)}    |    "
                f"Pausado: {formatar_hhmmss(self._segundos_pausado)}"
            ),
            font=("Segoe UI", 10, "bold"),
        ).pack(anchor="w", pady=(4, 0))
        ttk.Label(
            topo,
            textvariable=self._var_trava,
            font=("Segoe UI", 9),
            foreground="#3ecf6e",
            wraplength=1160,
        ).pack(anchor="w", pady=(6, 0))
        ttk.Label(
            topo,
            text=(
                "Cadastre as subtarefas executadas nesta atividade. "
                "Preencha o Tempo gasto no formulário para salvar como Concluída. "
                "Clique nos cabeçalhos para ordenar (↑ crescente / ↓ decrescente / 3º clique restaura ordem). "
                "Depois do pagamento, subtarefas ficam travadas e não podem ser alteradas."
            ),
            wraplength=1160,
        ).pack(anchor="w", pady=(6, 0))

        barra_acoes = ttk.Frame(quadro)
        barra_acoes.pack(fill="x", pady=(14, 10))

        ttk.Button(barra_acoes, text="Declarar Tarefa", style="Primario.TButton", command=self._nova_subtarefa).pack(side="left")
        ttk.Button(barra_acoes, text="Editar", command=self._editar_subtarefa).pack(side="left", padx=(8, 0))
        ttk.Button(barra_acoes, text="Excluir", style="Perigo.TButton", command=self._excluir_subtarefa).pack(side="left", padx=(8, 0))
        ttk.Button(barra_acoes, text="Atualizar", command=self._recarregar_dados).pack(side="right")

        tabela_frame = ttk.Frame(quadro)
        tabela_frame.pack(fill="both", expand=True)

        self._arvore = ttk.Treeview(
            tabela_frame,
            columns=("titulo", "canal", "status", "data", "tempo", "observacao", "bloqueio"),
            show="headings",
            height=18,
        )
        _cols = [
            ("titulo", "Subtarefa"),
            ("canal", "Canal"),
            ("status", "Status"),
            ("data", "Data"),
            ("tempo", "Tempo"),
            ("observacao", "Observação"),
            ("bloqueio", "Pagamento"),
        ]
        for _col_id, _col_label in _cols:
            self._arvore.heading(
                _col_id,
                text=_col_label,
                command=lambda c=_col_id: self._alternar_ordenacao_coluna(c),
            )

        self._arvore.column("titulo", width=290, stretch=True)
        self._arvore.column("canal", width=180, stretch=True)
        self._arvore.column("status", width=100, stretch=False, anchor="center")
        self._arvore.column("data", width=120, stretch=False, anchor="center")
        self._arvore.column("tempo", width=100, stretch=False, anchor="center")
        self._arvore.column("observacao", width=280, stretch=True)
        self._arvore.column("bloqueio", width=130, stretch=False, anchor="center")

        barra_y = ttk.Scrollbar(tabela_frame, orient="vertical", command=self._arvore.yview)
        barra_x = ttk.Scrollbar(tabela_frame, orient="horizontal", command=self._arvore.xview)
        self._arvore.configure(yscrollcommand=barra_y.set, xscrollcommand=barra_x.set)

        self._arvore.grid(row=0, column=0, sticky="nsew")
        barra_y.grid(row=0, column=1, sticky="ns")
        barra_x.grid(row=1, column=0, sticky="ew")
        tabela_frame.grid_rowconfigure(0, weight=1)
        tabela_frame.grid_columnconfigure(0, weight=1)

        self._arvore.bind("<Double-1>", lambda _e: self._editar_subtarefa())

        rodape = ttk.Frame(quadro)
        rodape.pack(fill="x", pady=(10, 0))

        ttk.Label(rodape, textvariable=self._var_resumo, font=("Segoe UI", 10, "bold"), foreground="#3ecf6e").pack(side="left")

        botoes_finais = ttk.Frame(rodape)
        botoes_finais.pack(side="right")

        if self._modo_finalizacao:
            ttk.Button(
                botoes_finais,
                text="Encerrar e Enviar Relatório",
                style="Primario.TButton",
                command=self._enviar_e_finalizar,
            ).pack(side="right")
            ttk.Button(botoes_finais, text="Cancelar", command=self.destroy).pack(side="right", padx=(0, 8))
        else:
            ttk.Button(botoes_finais, text="Fechar", command=self.destroy).pack(side="right")

    def _formatar_data(self, valor: object) -> str:
        if valor is None:
            return ""
        if isinstance(valor, datetime):
            return valor.strftime("%d/%m/%Y %H:%M")
        if isinstance(valor, date):
            return valor.strftime("%d/%m/%Y")
        if isinstance(valor, str) and len(valor) >= 10:
            try:
                return date.fromisoformat(valor[:10]).strftime("%d/%m/%Y")
            except (ValueError, TypeError):
                pass
        return str(valor)

    def _obter_id_subtarefa_selecionada(self) -> int:
        selecionado = self._arvore.focus() or ""
        if not selecionado.startswith("subtarefa_"):
            raise RuntimeError("Selecione uma subtarefa.")
        return int(selecionado.split("_", 1)[1])

    def _data_esta_travada(self) -> bool:
        """Verifica se a data de referência está estritamente antes da trava (dia exato é livre)."""
        travado_ate = self._travado_ate_cache
        if travado_ate is None:
            return False
        return bool(self._referencia_data < travado_ate)

    def _atualizar_texto_trava(self, travado_ate: object) -> None:
        self._travado_ate_cache = travado_ate
        if travado_ate is None:
            self._var_trava.set("Sem bloqueio por pagamento para este usuário.")
            return

        if self._referencia_data < travado_ate:
            self._var_trava.set(
                f"Lançamentos travados até {travado_ate.strftime('%d/%m/%Y')}. Datas anteriores não podem mais ser editadas."
            )
        else:
            self._var_trava.set(
                f"Última trava por pagamento: {travado_ate.strftime('%d/%m/%Y')}. Tarefas após o pagamento ainda podem ser alteradas."
            )

    def _recarregar_dados(self) -> None:
        self._var_resumo.set("Carregando...")

        user_id = self._usuario_id()
        id_atividade = self._id_atividade
        segundos_trabalhando = self._segundos_trabalhando

        def _buscar() -> tuple:
            subtarefas = self._repositorio.listar_subtarefas_do_dia(user_id, id_atividade=id_atividade)
            resumo = self._repositorio.obter_resumo_do_dia(
                user_id,
                id_atividade=id_atividade,
                segundos_monitorados_adicionais=segundos_trabalhando,
            )
            travado_ate = self._repositorio.obter_data_travada_por_pagamento(user_id)
            try:
                pagamentos = self._repositorio.listar_pagamentos_do_usuario(user_id)
            except Exception:
                pagamentos = []
            return subtarefas, resumo, travado_ate, pagamentos

        def _aplicar(resultado: object) -> None:
            try:
                self._arvore.winfo_exists()
            except Exception:
                return
            if not self._arvore.winfo_exists():
                return

            subtarefas, resumo, travado_ate, pagamentos = resultado  # type: ignore[misc]

            self._subtarefas = subtarefas
            self._mapa_subtarefas = {
                int(getattr(s, "id_subtarefa", 0)): s for s in subtarefas
            }

            # Configurar tag visual para linhas de pagamento
            self._arvore.tag_configure("pagamento", foreground="#00cc66", background="#1a2e1a")

            for item in self._arvore.get_children():
                self._arvore.delete(item)

            # Mesclar subtarefas e pagamentos ordenados por datetime desc
            # Cada item: (datetime_ordenacao, iid, valores, tags, sort_keys)
            _DT_MIN = datetime.min
            itens_mesclados: list[tuple] = []

            for subtarefa in subtarefas:
                id_sub = int(getattr(subtarefa, "id_subtarefa", 0))
                ref = getattr(subtarefa, "referencia_data", None)
                criada = getattr(subtarefa, "criada_em", None)
                if isinstance(criada, datetime):
                    dt_ord = criada
                elif isinstance(ref, date):
                    dt_ord = datetime(ref.year, ref.month, ref.day)
                else:
                    dt_ord = _DT_MIN
                _titulo = str(getattr(subtarefa, "titulo", "") or "")
                _canal = str(getattr(subtarefa, "canal_entrega", "") or "")
                _status = "Concluída" if bool(getattr(subtarefa, "concluida", False)) else "Aberta"
                _segundos = int(getattr(subtarefa, "segundos_gastos", 0) or 0)
                _obs = str(getattr(subtarefa, "observacao", "") or "")
                _bloqueio = "Pago" if bool(getattr(subtarefa, "bloqueada_pagamento", False)) else ""
                itens_mesclados.append((
                    dt_ord,
                    f"subtarefa_{id_sub}",
                    (_titulo, _canal, _status, self._formatar_data(ref), formatar_hhmmss(_segundos), _obs, _bloqueio),
                    (),
                    {
                        "titulo": _titulo.lower(),
                        "canal": _canal.lower(),
                        "status": _status.lower(),
                        "data": dt_ord,
                        "tempo": _segundos,
                        "observacao": _obs.lower(),
                        "bloqueio": _bloqueio.lower(),
                    },
                ))

            for pag in pagamentos:
                data_pag = pag.get("data_pagamento")
                if isinstance(data_pag, str):
                    try:
                        data_pag = date.fromisoformat(data_pag)
                    except (ValueError, TypeError):
                        data_pag = None
                criado_em_pag = pag.get("criado_em")
                if isinstance(criado_em_pag, datetime):
                    dt_ord_pag = criado_em_pag
                elif isinstance(criado_em_pag, str):
                    try:
                        dt_ord_pag = datetime.fromisoformat(criado_em_pag)
                    except (ValueError, TypeError):
                        dt_ord_pag = datetime(data_pag.year, data_pag.month, data_pag.day) if isinstance(data_pag, date) else _DT_MIN
                elif isinstance(data_pag, date):
                    dt_ord_pag = datetime(data_pag.year, data_pag.month, data_pag.day)
                else:
                    dt_ord_pag = _DT_MIN
                valor = pag.get("valor", 0)
                valor_fmt = f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                obs = str(pag.get("observacao") or "")
                id_pag = int(pag.get("id_pagamento", 0))
                _titulo_pag = f"💰 Pagamento — {valor_fmt}"
                itens_mesclados.append((
                    dt_ord_pag,
                    f"pagamento_{id_pag}",
                    (_titulo_pag, "", "Pago", self._formatar_data(data_pag), "", obs, ""),
                    ("pagamento",),
                    {
                        "titulo": _titulo_pag.lower(),
                        "canal": "",
                        "status": "pago",
                        "data": dt_ord_pag,
                        "tempo": 0,
                        "observacao": obs.lower(),
                        "bloqueio": "",
                    },
                ))

            # Ordem padrão: mais recente no topo
            itens_mesclados.sort(key=lambda x: x[0], reverse=True)

            # Salva lista-base para restauração ao limpar ordenação manual
            self._lista_base_ordenacao = list(itens_mesclados)

            # Reseta indicadores de cabeçalho ao recarregar
            self._sort_col = None
            self._sort_dir = "asc"
            self._atualizar_indicadores_cabecalhos()

            for _, iid, valores, tags, _sk in itens_mesclados:
                self._arvore.insert("", "end", iid=iid, values=valores, tags=tags)

            self._var_resumo.set(
                f"Cronometradas: {resumo['cronometrado_hhmmss']}    |    "
                f"Declaradas: {resumo['declarado_ciclo_hhmmss']}"
            )
            self._atualizar_texto_trava(travado_ate)

        def _falha(erro: Exception) -> None:
            self._var_resumo.set(f"Falha ao carregar: {erro}")
            messagebox.showerror("Erro", str(erro), parent=self)

        self._executar_em_background(_buscar, _aplicar, _falha)

    # ----------------------------------------------------------
    # Ordenação por cabeçalho (triestado: asc → desc → padrão)
    # ----------------------------------------------------------
    _SORT_COLS_LABEL = {
        "titulo": "Subtarefa",
        "canal": "Canal",
        "status": "Status",
        "data": "Data",
        "tempo": "Tempo",
        "observacao": "Observação",
        "bloqueio": "Pagamento",
    }

    def _chave_ordenacao(self, item: tuple, col: str) -> object:
        """Extrai chave de comparação tipada a partir do item da lista-base."""
        _, _, valores, _, sort_keys = item
        return sort_keys.get(col, "")

    def _atualizar_indicadores_cabecalhos(self) -> None:
        for col, label in self._SORT_COLS_LABEL.items():
            if col == self._sort_col:
                indicador = " ↑" if self._sort_dir == "asc" else " ↓"
            else:
                indicador = ""
            try:
                self._arvore.heading(col, text=label + indicador)
            except Exception:
                pass

    def _alternar_ordenacao_coluna(self, col: str) -> None:
        if not self._lista_base_ordenacao:
            return
        if self._sort_col != col:
            self._sort_col = col
            self._sort_dir = "asc"
        elif self._sort_dir == "asc":
            self._sort_dir = "desc"
        else:
            # Terceiro clique: restaura ordem padrão
            self._sort_col = None
            self._sort_dir = "asc"

        self._atualizar_indicadores_cabecalhos()
        self._aplicar_ordenacao()

    def _aplicar_ordenacao(self) -> None:
        if not self._lista_base_ordenacao:
            return

        if self._sort_col is None:
            itens = list(self._lista_base_ordenacao)
        else:
            col = self._sort_col
            reverso = self._sort_dir == "desc"
            itens = sorted(
                self._lista_base_ordenacao,
                key=lambda x: self._chave_ordenacao(x, col),
                reverse=reverso,
            )

        for item in self._arvore.get_children():
            self._arvore.delete(item)

        for _, iid, valores, tags, _sort_keys in itens:
            self._arvore.insert("", "end", iid=iid, values=valores, tags=tags)

    def _validar_nao_travado(self, id_subtarefa: int | None = None) -> bool:
        """Valida se a operação é permitida. Para subtarefas existentes, verifica a flag individual."""
        if id_subtarefa is not None:
            subtarefa = self._mapa_subtarefas.get(id_subtarefa)
            if subtarefa and bool(getattr(subtarefa, "bloqueada_pagamento", False)):
                messagebox.showwarning(
                    "Atenção",
                    "Esta subtarefa já foi travada por pagamento e não pode mais ser alterada.",
                    parent=self,
                )
                return False
        if self._data_esta_travada():
            messagebox.showwarning(
                "Atenção",
                "Este período já foi travado por pagamento e não pode mais ser editado.",
                parent=self,
            )
            return False
        return True

    def _nova_subtarefa(self) -> None:
        if not self._validar_nao_travado():
            return
        self._var_resumo.set("Carregando...")
        self._abrir_formulario_subtarefa(None)

    def _editar_subtarefa(self) -> None:
        try:
            id_subtarefa = self._obter_id_subtarefa_selecionada()
        except Exception as erro:
            messagebox.showwarning("Atenção", str(erro), parent=self)
            return
        if not self._validar_nao_travado(id_subtarefa):
            return
        self._var_resumo.set("Carregando...")
        self._abrir_formulario_subtarefa(id_subtarefa)

    def _excluir_subtarefa(self) -> None:
        try:
            id_subtarefa = self._obter_id_subtarefa_selecionada()
        except Exception as erro:
            messagebox.showwarning("Atenção", str(erro), parent=self)
            return
        if not self._validar_nao_travado(id_subtarefa):
            return

        if not messagebox.askyesno("Confirmar", "Excluir a subtarefa selecionada?", parent=self):
            return

        self._var_resumo.set("Carregando...")
        user_id = self._usuario_id()
        self._executar_em_background(
            lambda: self._repositorio.excluir_subtarefa(user_id=user_id, id_subtarefa=id_subtarefa),
            lambda _: self._recarregar_dados(),
        )

    def _abrir_formulario_subtarefa(self, id_subtarefa: int | None) -> None:
        """Dispatcher: busca config MEGA do canal (com timeout curto) e decide
        entre o formulário com upload obrigatório ou o legado.

        Se MEGA não estiver configurado/disponível, abre o legado direto — sem
        nenhuma penalidade de UX além do tempo do fetch (~5s timeout).
        """
        subtarefa = self._mapa_subtarefas.get(int(id_subtarefa)) if id_subtarefa else None
        chave = str(self._usuario.get("chave") or "").strip()
        user_id = self._usuario_id()

        # Sem chave do usuário ou sem chave fixa do cliente: pula o fetch direto.
        try:
            from app.config import APP_CLIENT_DECRYPT_KEY, URL_PAINEL
        except Exception:
            APP_CLIENT_DECRYPT_KEY = ""
            URL_PAINEL = ""

        if not chave or not user_id or not APP_CLIENT_DECRYPT_KEY or not URL_PAINEL:
            self._abrir_formulario_subtarefa_legado(subtarefa)
            return

        def _buscar_config() -> dict | None:
            try:
                from app.mega_uploader import PainelMegaApi
                api = PainelMegaApi(URL_PAINEL, user_id, chave)
                return api.obter_config_canal(self._id_atividade, timeout=5.0)
            except Exception:
                return None

        def _despachar(config: object) -> None:
            cfg = config if isinstance(config, dict) else None
            if cfg and cfg.get("upload_ativo"):
                self._abrir_formulario_subtarefa_mega(subtarefa, cfg)
            else:
                aviso = (
                    "Este canal ainda não tem upload obrigatório no MEGA configurado."
                    if cfg is not None else None
                )
                self._abrir_formulario_subtarefa_legado(subtarefa, aviso_mega=aviso)

        self._executar_em_background(_buscar_config, _despachar)

    def _abrir_formulario_subtarefa_legado(
        self,
        subtarefa: object | None,
        *,
        aviso_mega: str | None = None,
    ) -> None:
        """Formulário tradicional (pré-MEGA): número + título + checkbox de drive.

        Mantido para canais sem `mega_canal_config` (ou com `upload_ativo=0`).
        Quando `aviso_mega` é passado, exibe um label suave informando que o
        canal ainda não tem upload obrigatório configurado — útil pra admin
        identificar onde falta configurar.
        """
        janela = tk.Toplevel(self)
        janela.title("Declarar Tarefa")
        janela.geometry("700x460" if not aviso_mega else "700x490")
        janela.resizable(False, False)
        janela.transient(self)
        janela.grab_set()
        janela.configure(bg="#111111")

        canal_inicial = (str(getattr(subtarefa, "canal_entrega", "") or "") if subtarefa else self._titulo_atividade)

        # Separa número e nome da tarefa ao editar (formato esperado: "NUMERO - NOME")
        _titulo_completo = str(getattr(subtarefa, "titulo", "") or "") if subtarefa else ""
        if subtarefa and " - " in _titulo_completo:
            _partes = _titulo_completo.split(" - ", 1)
            _numero_inicial = _partes[0]
            _titulo_inicial = _partes[1]
        else:
            _numero_inicial = ""
            _titulo_inicial = _titulo_completo

        var_numero = tk.StringVar(value=_numero_inicial)
        var_titulo = tk.StringVar(value=_titulo_inicial)
        var_canal = tk.StringVar(value=canal_inicial)
        var_observacao = tk.StringVar(value=(str(getattr(subtarefa, "observacao", "") or "") if subtarefa else ""))
        referencia_atual = getattr(subtarefa, "referencia_data", None) if subtarefa else self._referencia_data
        var_referencia = tk.StringVar(
            value=(referencia_atual.strftime("%d/%m/%Y") if isinstance(referencia_atual, date) else self._referencia_data.strftime("%d/%m/%Y"))
        )
        subtarefa_concluida = bool(getattr(subtarefa, "concluida", False)) if subtarefa else False
        var_tempo = tk.StringVar(
            value=(formatar_hhmmss(int(getattr(subtarefa, "segundos_gastos", 0) or 0)) if subtarefa_concluida else "00:00:00")
        )

        # ── paleta local ─────────────────────────────────────
        _C = "#1a1a1a"   # card bg
        _D = "#6a6a6a"   # rótulos dimm
        _A = "#1b6ef3"   # accent azul

        # ── tooltip simples ───────────────────────────────────
        def _tooltip(widget: tk.Widget, texto: str) -> None:
            tip: list[tk.Toplevel | None] = [None]

            def _mostrar(event: tk.Event) -> None:  # type: ignore[type-arg]
                if tip[0]:
                    return
                tw = tk.Toplevel(widget)
                tw.wm_overrideredirect(True)
                tw.wm_geometry(f"+{event.x_root + 12}+{event.y_root + 6}")
                tk.Label(tw, text=texto, bg="#2a2a2a", fg="#e2e8f0",
                         font=("Segoe UI", 9), padx=8, pady=5,
                         wraplength=240, justify="left").pack()
                tip[0] = tw

            def _esconder(_event: tk.Event) -> None:  # type: ignore[type-arg]
                if tip[0]:
                    tip[0].destroy()
                    tip[0] = None

            widget.bind("<Enter>", _mostrar)
            widget.bind("<Leave>", _esconder)

        def _label_com_ajuda(parent: tk.Frame, texto_label: str, texto_ajuda: str) -> None:
            """Renderiza label + ícone ? com tooltip lado a lado."""
            row = tk.Frame(parent, bg=_C)
            row.pack(anchor="w")
            tk.Label(row, text=texto_label, bg=_C, fg=_D,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            btn_q = tk.Label(row, text=" ?", bg=_C, fg=_A,
                             font=("Segoe UI", 8, "bold"), cursor="question_arrow")
            btn_q.pack(side="left")
            _tooltip(btn_q, texto_ajuda)

        # barra de acento no topo
        tk.Frame(janela, bg=_A, height=3).pack(fill="x")

        # área principal
        inner = tk.Frame(janela, bg=_C, padx=26, pady=18)
        inner.pack(fill="both", expand=True)

        titulo_janela = "Editar Tarefa" if subtarefa else "Nova Tarefa"
        tk.Label(inner, text=titulo_janela, bg=_C, fg="#ffffff",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 16))

        if aviso_mega:
            tk.Label(
                inner, text=f"⚠ {aviso_mega}", bg=_C, fg="#f0a500",
                font=("Segoe UI", 9), wraplength=600, justify="left",
            ).pack(anchor="w", pady=(0, 10))

        # Nº do vídeo + Tarefa (lado a lado)
        linha_tarefa = tk.Frame(inner, bg=_C)
        linha_tarefa.pack(fill="x")
        col_numero = tk.Frame(linha_tarefa, bg=_C)
        col_numero.pack(side="left")
        col_titulo = tk.Frame(linha_tarefa, bg=_C)
        col_titulo.pack(side="left", fill="x", expand=True, padx=(12, 0))

        _label_com_ajuda(col_numero, "Nº DO VÍDEO",
                         "Número da pasta do Drive.")
        entry_numero = ttk.Entry(col_numero, textvariable=var_numero, width=10)
        entry_numero.pack(fill="x", pady=(3, 12))

        def _on_key_numero(event: tk.Event) -> str:  # type: ignore[type-arg]
            if event.keysym in ("BackSpace", "Delete", "Left", "Right", "Tab", "ISO_Left_Tab"):
                return ""
            if not event.char.isdigit():
                return "break"
            return ""

        def _normalizar_numero(*_args: object) -> None:
            val = var_numero.get().lstrip("0") or ""
            if val != var_numero.get():
                var_numero.set(val)

        entry_numero.bind("<Key>", _on_key_numero)
        var_numero.trace_add("write", _normalizar_numero)

        _label_com_ajuda(col_titulo, "TAREFA",
                         "Nome/Tema do vídeo ou tarefa.")
        ttk.Entry(col_titulo, textvariable=var_titulo, width=60).pack(fill="x", pady=(3, 12))

        # Canal + Data (lado a lado)
        linha_superior = tk.Frame(inner, bg=_C)
        linha_superior.pack(fill="x")
        coluna_esquerda = tk.Frame(linha_superior, bg=_C)
        coluna_esquerda.pack(side="left", fill="x", expand=True)
        coluna_direita = tk.Frame(linha_superior, bg=_C)
        coluna_direita.pack(side="left", fill="x", expand=True, padx=(12, 0))

        _label_com_ajuda(coluna_esquerda, "CANAL",
                         "Escolha o canal correspondente ao trabalho declarado.")
        combo_canal = ttk.Combobox(coluna_esquerda, textvariable=var_canal, values=self._opcoes_canal, width=34, state="readonly")
        combo_canal.pack(fill="x", pady=(3, 10))

        tk.Label(coluna_direita, text="DATA DE REFERÊNCIA", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(coluna_direita, textvariable=var_referencia, width=18).pack(fill="x", pady=(3, 10))

        # Observação
        tk.Label(inner, text="OBSERVAÇÃO", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(inner, textvariable=var_observacao, width=82).pack(fill="x", pady=(3, 12))

        if subtarefa_concluida:
            tk.Label(
                inner,
                text="Tarefa concluída — ajustes em todos os campos são permitidos.",
                bg=_C, fg="#3ecf6e", font=("Segoe UI", 9),
            ).pack(anchor="w", pady=(0, 8))

        # Tempo
        tk.Label(inner, text="TEMPO GASTO  (HH:MM:SS)", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        entry_tempo = ttk.Entry(inner, textvariable=var_tempo, width=18)
        entry_tempo.pack(anchor="w", pady=(3, 4))

        def _on_key_tempo(event: tk.Event) -> str:  # type: ignore[type-arg]
            if event.keysym == "BackSpace":
                digits = var_tempo.get().replace(":", "")
                digits = ("0" + digits[:-1])[-6:]
                var_tempo.set(f"{digits[0:2]}:{digits[2:4]}:{digits[4:6]}")
                return "break"
            if event.char.isdigit():
                digits = var_tempo.get().replace(":", "")
                digits = (digits[1:] + event.char)[-6:]
                var_tempo.set(f"{digits[0:2]}:{digits[2:4]}:{digits[4:6]}")
                return "break"
            if event.keysym in ("Tab", "ISO_Left_Tab", "Return"):
                return ""
            return "break"

        entry_tempo.bind("<Key>", _on_key_tempo)

        # Confirmação de upload no Drive (sempre desmarcada ao abrir)
        var_drive = tk.BooleanVar(value=False)
        chk_drive = tk.Checkbutton(
            inner, text="Declaro que já subi os arquivos no drive",
            variable=var_drive, bg=_C, fg="#e55555", selectcolor="#111111",
            activebackground=_C, activeforeground="#ffffff",
            font=("Segoe UI", 9),
        )
        chk_drive.pack(anchor="w", pady=(8, 0))

        def _atualizar_cor_drive(*_args: object) -> None:
            chk_drive.configure(fg="#4ade80" if var_drive.get() else "#e55555")

        var_drive.trace_add("write", _atualizar_cor_drive)

        # separador + rodapé
        tk.Frame(janela, bg="#282828", height=1).pack(fill="x")
        rodape = tk.Frame(janela, bg="#1a1a1a", padx=26, pady=12)
        rodape.pack(fill="x")

        var_texto_botao = tk.StringVar()

        def _atualizar_texto_botao(*_args: object) -> None:
            tempo = (var_tempo.get() or "").strip()
            if not subtarefa_concluida and tempo:
                var_texto_botao.set("Salvar e Concluir")
            else:
                var_texto_botao.set("Salvar")

        _atualizar_texto_botao()
        var_tempo.trace_add("write", _atualizar_texto_botao)

        btn_cancelar = ttk.Button(rodape, text="Cancelar", command=janela.destroy)
        btn_cancelar.pack(side="right")
        btn_salvar = ttk.Button(rodape, textvariable=var_texto_botao, style="Primario.TButton")
        btn_salvar.pack(side="right", padx=(0, 8))

        def salvar() -> None:
            # Captura intenção ANTES de alterar o texto do botão
            deve_concluir = var_texto_botao.get() == "Salvar e Concluir"

            # Desabilita imediatamente — antes de qualquer validação — para ignorar cliques em fila
            btn_salvar.configure(state="disabled")
            btn_cancelar.configure(state="disabled")
            var_texto_botao.set("Salvando...")
            janela.update_idletasks()

            try:
                referencia_data = self._converter_texto_para_data(var_referencia.get())
                tempo_texto = (var_tempo.get() or "").strip()
                segundos_tempo = self._converter_texto_tempo_para_segundos(tempo_texto) if tempo_texto else 0
            except Exception as erro:
                _atualizar_texto_botao()
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                messagebox.showerror("Erro", str(erro), parent=janela)
                return

            user_id = self._usuario_id()
            id_atividade = self._id_atividade
            if not var_drive.get():
                _atualizar_texto_botao()
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                messagebox.showwarning(
                    "Atenção",
                    "Confirme que já subiu os arquivos no Drive antes de salvar.",
                    parent=janela,
                )
                return

            numero_video = var_numero.get().strip()
            titulo_nome = var_titulo.get().strip()

            if not numero_video:
                _atualizar_texto_botao()
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                messagebox.showwarning("Atenção", "Informe o número do vídeo.", parent=janela)
                return

            if not titulo_nome:
                _atualizar_texto_botao()
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                messagebox.showwarning("Atenção", "Informe o nome da tarefa.", parent=janela)
                return

            titulo = f"{numero_video} - {titulo_nome}"
            canal = var_canal.get()
            observacao = var_observacao.get()
            segundos_trabalhando = self._segundos_trabalhando
            id_sub = int(getattr(subtarefa, "id_subtarefa", 0)) if subtarefa else 0

            # Validação de nome duplicado
            titulo_normalizado = titulo.strip().lower()
            for sub_existente in self._subtarefas:
                sub_id_check = int(getattr(sub_existente, "id_subtarefa", 0))
                if id_sub and sub_id_check == id_sub:
                    continue  # mesma tarefa sendo editada — não conta como duplicata
                if str(getattr(sub_existente, "titulo", "") or "").strip().lower() == titulo_normalizado:
                    _atualizar_texto_botao()
                    btn_salvar.configure(state="normal")
                    btn_cancelar.configure(state="normal")
                    messagebox.showwarning("Atenção", "Já existe uma tarefa com esse nome.", parent=janela)
                    return

            def _operacao() -> None:
                if subtarefa is None:
                    # Reutiliza ID já criado se houve falha na tentativa anterior
                    if self._id_subtarefa_criada_nesta_janela is None:
                        self._id_subtarefa_criada_nesta_janela = self._repositorio.criar_subtarefa(
                            user_id=user_id,
                            referencia_data=referencia_data,
                            id_atividade=id_atividade,
                            titulo=titulo,
                            canal_entrega=canal,
                            observacao=observacao,
                        )
                    novo_id = self._id_subtarefa_criada_nesta_janela
                    if deve_concluir:
                        self._repositorio.concluir_subtarefa(
                            user_id=user_id,
                            id_subtarefa=novo_id,
                            segundos_gastos=segundos_tempo,
                            referencia_data=referencia_data,
                            canal_entrega=canal,
                            observacao=observacao,
                            segundos_monitorados_adicionais=segundos_trabalhando,
                        )
                elif subtarefa_concluida:
                    self._repositorio.atualizar_subtarefa(
                        user_id=user_id,
                        id_subtarefa=id_sub,
                        titulo=titulo,
                        canal_entrega=canal,
                        observacao=observacao,
                        referencia_data=referencia_data,
                        segundos_gastos=segundos_tempo if tempo_texto else None,
                        segundos_monitorados_adicionais=segundos_trabalhando,
                    )
                else:
                    self._repositorio.atualizar_subtarefa(
                        user_id=user_id,
                        id_subtarefa=id_sub,
                        titulo=titulo,
                        canal_entrega=canal,
                        observacao=observacao,
                        referencia_data=referencia_data,
                    )
                    if deve_concluir:
                        self._repositorio.concluir_subtarefa(
                            user_id=user_id,
                            id_subtarefa=id_sub,
                            segundos_gastos=segundos_tempo,
                            referencia_data=referencia_data,
                            canal_entrega=canal,
                            observacao=observacao,
                            segundos_monitorados_adicionais=segundos_trabalhando,
                        )

            def _ok(_: object) -> None:
                self._id_subtarefa_criada_nesta_janela = None  # reset — libera ID para próxima declaração
                try:
                    janela.destroy()
                except Exception:
                    pass
                self._recarregar_dados()

            def _falha(erro: Exception) -> None:
                _atualizar_texto_botao()
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                messagebox.showerror("Erro", str(erro), parent=janela)

            self._executar_em_background(_operacao, _ok, _falha)

        btn_salvar.configure(command=salvar)

    # ============================================================
    # Formulário com upload obrigatório no MEGA (Fase 3)
    # ============================================================
    def _abrir_formulario_subtarefa_mega(self, subtarefa: object | None, config: dict) -> None:
        """Formulário com upload obrigatório no MEGA.

        config (vindo de `desktop_obter_config.php`):
          - upload_ativo (bool)
          - pasta_raiz_mega (str)
          - campos_exigidos (list[dict]: label_campo, extensoes_permitidas, quantidade_maxima, obrigatorio, ordem)
          - pastas_logicas (list[dict]: id_pasta_logica, nome_pasta, numero_video, titulo_video)

        Diferenças vs. legado:
          - Substitui número+título soltos por seção "Pasta lógica do vídeo"
            com modo "Criar nova" / "Selecionar existente". Título da subtarefa
            passa a ser exatamente `nome_pasta` (canônico "NN - Titulo").
          - Adiciona seção "Arquivos para upload" — uma linha por campo
            exigido. Conclusão bloqueada enquanto algum obrigatório não
            estiver `concluido`.
          - Sem checkbox "Declaro que subi…" — substituído pelo upload real.
        """
        from tkinter import filedialog as _filedialog

        from app.config import APP_CLIENT_DECRYPT_KEY, URL_PAINEL
        from app.mega_uploader import MegaUploader, PainelMegaApi

        chave = str(self._usuario.get("chave") or "").strip()
        user_id = self._usuario_id()
        api = PainelMegaApi(URL_PAINEL, user_id, chave)

        # Uploader é criado on-demand e cacheado por janela. Login só rola
        # quando o primeiro upload começa (não ao abrir o form).
        uploader_holder: dict[str, MegaUploader | None] = {"u": None}

        def _obter_uploader() -> MegaUploader:
            if uploader_holder["u"] is None:
                uploader_holder["u"] = MegaUploader(URL_PAINEL, user_id, chave, APP_CLIENT_DECRYPT_KEY)
            return uploader_holder["u"]

        campos_exigidos: list[dict] = list(config.get("campos_exigidos") or [])
        pastas_existentes: list[dict] = list(config.get("pastas_logicas") or [])
        pasta_raiz_mega: str = str(config.get("pasta_raiz_mega") or "").strip()

        # Estado mutável compartilhado pelos closures internos.
        pasta_logica = {"id_pasta_logica": 0, "nome_pasta": ""}
        # Por nome_campo: {"state", "id_upload", "arquivo_local", "label_status", "pbar"}
        estado_campos: dict[str, dict] = {}

        # Edição: tenta lookup por título (nome_pasta é único por canal).
        if subtarefa is not None:
            titulo_sub = str(getattr(subtarefa, "titulo", "") or "")
            for p in pastas_existentes:
                if str(p.get("nome_pasta") or "") == titulo_sub:
                    pasta_logica["id_pasta_logica"] = int(p.get("id_pasta_logica") or 0)
                    pasta_logica["nome_pasta"] = titulo_sub
                    break

        # ---------------- Janela ----------------
        janela = tk.Toplevel(self)
        janela.title("Declarar Tarefa — Upload MEGA")
        janela.geometry("760x720")
        janela.minsize(720, 640)
        janela.transient(self)
        janela.grab_set()
        janela.configure(bg="#111111")

        _C = "#1a1a1a"
        _D = "#6a6a6a"
        _A = "#1b6ef3"
        _OK = "#3ecf6e"
        _ERRO = "#e55555"
        _PEND = "#f0a500"

        tk.Frame(janela, bg=_A, height=3).pack(fill="x")

        # Container scrollable porque o form pode crescer com muitos campos.
        outer = tk.Frame(janela, bg=_C)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=_C, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        inner = tk.Frame(canvas, bg=_C, padx=26, pady=18)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_config(_e: object) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfigure(inner_id, width=canvas.winfo_width())

        inner.bind("<Configure>", _on_inner_config)
        canvas.bind("<Configure>", _on_inner_config)

        titulo_janela = "Editar Tarefa" if subtarefa else "Nova Tarefa (com upload obrigatório)"
        tk.Label(inner, text=titulo_janela, bg=_C, fg="#ffffff",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 4))
        tk.Label(inner, text=f"Pasta raiz no MEGA: /{pasta_raiz_mega}", bg=_C, fg=_D,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 14))

        # ====================================================
        # Seção 1: Pasta lógica do vídeo
        # ====================================================
        sec_pasta = tk.Frame(inner, bg=_C)
        sec_pasta.pack(fill="x", pady=(0, 12))
        tk.Label(sec_pasta, text="PASTA LÓGICA DO VÍDEO", bg=_C, fg=_D,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        # Modo: criar nova vs selecionar existente. Se já tem pasta vinculada
        # (edição), começa em "selecionar" travado nessa pasta.
        modo_pasta = tk.StringVar(value="selecionar" if pasta_logica["id_pasta_logica"] else "criar")

        rad_frame = tk.Frame(sec_pasta, bg=_C)
        rad_frame.pack(anchor="w", pady=(4, 6))
        tk.Radiobutton(rad_frame, text="Criar nova", variable=modo_pasta, value="criar",
                       bg=_C, fg="#ffffff", selectcolor="#222", activebackground=_C,
                       font=("Segoe UI", 9)).pack(side="left", padx=(0, 12))
        tk.Radiobutton(rad_frame, text="Selecionar existente", variable=modo_pasta, value="selecionar",
                       bg=_C, fg="#ffffff", selectcolor="#222", activebackground=_C,
                       font=("Segoe UI", 9)).pack(side="left")

        # --- Modo "Criar nova" ---
        bloco_criar = tk.Frame(sec_pasta, bg=_C)

        var_numero = tk.StringVar(value="")
        var_titulo_pasta = tk.StringVar(value="")

        linha_num = tk.Frame(bloco_criar, bg=_C)
        linha_num.pack(fill="x", pady=(2, 2))
        tk.Label(linha_num, text="Nº", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(side="left")
        ent_num = ttk.Entry(linha_num, textvariable=var_numero, width=8)
        ent_num.pack(side="left", padx=(6, 12))
        tk.Label(linha_num, text="Título", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(side="left")
        ent_tit = ttk.Entry(linha_num, textvariable=var_titulo_pasta)
        ent_tit.pack(side="left", fill="x", expand=True, padx=(6, 0))

        var_preview = tk.StringVar(value="(preencha número e título)")
        tk.Label(bloco_criar, textvariable=var_preview, bg=_C, fg=_PEND,
                 font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(4, 4))

        def _atualizar_preview(*_a: object) -> None:
            n = var_numero.get().strip()
            t = " ".join((var_titulo_pasta.get() or "").split())
            if n.isdigit() and t:
                num_padded = n.zfill(2) if len(n) < 2 else n
                t_cap = (t[0].upper() + t[1:]) if t else t
                var_preview.set(f"Será salvo como: \"{num_padded} - {t_cap}\"")
            else:
                var_preview.set("(preencha número e título)")

        var_numero.trace_add("write", _atualizar_preview)
        var_titulo_pasta.trace_add("write", _atualizar_preview)

        var_status_pasta = tk.StringVar(value="")
        lbl_status_pasta = tk.Label(bloco_criar, textvariable=var_status_pasta, bg=_C,
                                    fg=_D, font=("Segoe UI", 9))
        lbl_status_pasta.pack(anchor="w")

        btn_criar_pasta = ttk.Button(bloco_criar, text="Criar pasta lógica")
        btn_criar_pasta.pack(anchor="w", pady=(6, 0))

        def _criar_pasta() -> None:
            n = var_numero.get().strip()
            t = (var_titulo_pasta.get() or "").strip()
            if not n.isdigit() or not t:
                messagebox.showwarning("Atenção", "Informe número (dígitos) e título.", parent=janela)
                return
            btn_criar_pasta.configure(state="disabled")
            var_status_pasta.set("Criando pasta…")
            lbl_status_pasta.configure(fg=_PEND)

            def _op() -> dict:
                return api.criar_pasta_logica(self._id_atividade, n, t)

            def _ok(r: object) -> None:
                btn_criar_pasta.configure(state="normal")
                d = r if isinstance(r, dict) else {}
                pasta_logica["id_pasta_logica"] = int(d.get("id_pasta_logica") or 0)
                pasta_logica["nome_pasta"] = str(d.get("nome_pasta") or "")
                var_status_pasta.set(f"✓ pasta criada: {pasta_logica['nome_pasta']}")
                lbl_status_pasta.configure(fg=_OK)
                _atualizar_botao_salvar()

            def _falha(e: Exception) -> None:
                btn_criar_pasta.configure(state="normal")
                var_status_pasta.set(f"✗ {e}")
                lbl_status_pasta.configure(fg=_ERRO)

            self._executar_em_background(_op, _ok, _falha)

        btn_criar_pasta.configure(command=_criar_pasta)

        # --- Modo "Selecionar existente" ---
        bloco_selecionar = tk.Frame(sec_pasta, bg=_C)
        opcoes_combo = [str(p.get("nome_pasta") or "") for p in pastas_existentes]
        var_pasta_existente = tk.StringVar(value=pasta_logica["nome_pasta"] or "")
        cmb_pasta = ttk.Combobox(bloco_selecionar, textvariable=var_pasta_existente,
                                 values=opcoes_combo, state="readonly")
        cmb_pasta.pack(fill="x", pady=(4, 0))
        if not opcoes_combo:
            tk.Label(bloco_selecionar, text="(nenhuma pasta cadastrada para este canal ainda)",
                     bg=_C, fg=_D, font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(2, 0))

        def _ao_selecionar_pasta(*_a: object) -> None:
            nome = var_pasta_existente.get()
            for p in pastas_existentes:
                if str(p.get("nome_pasta") or "") == nome:
                    pasta_logica["id_pasta_logica"] = int(p.get("id_pasta_logica") or 0)
                    pasta_logica["nome_pasta"] = nome
                    break
            _atualizar_botao_salvar()

        cmb_pasta.bind("<<ComboboxSelected>>", _ao_selecionar_pasta)

        def _alternar_modo_pasta(*_a: object) -> None:
            if modo_pasta.get() == "criar":
                bloco_selecionar.pack_forget()
                bloco_criar.pack(fill="x", pady=(2, 0))
            else:
                bloco_criar.pack_forget()
                bloco_selecionar.pack(fill="x", pady=(2, 0))

        modo_pasta.trace_add("write", _alternar_modo_pasta)
        _alternar_modo_pasta()

        # ====================================================
        # Seção 2: Uploads dinâmicos
        # ====================================================
        tk.Frame(inner, bg="#222", height=1).pack(fill="x", pady=(8, 8))
        tk.Label(inner, text="ARQUIVOS PARA UPLOAD", bg=_C, fg=_D,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        if not campos_exigidos:
            tk.Label(inner, text="(nenhum arquivo configurado pra você neste canal — só "
                                 "pasta lógica obrigatória)",
                     bg=_C, fg=_D, font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(4, 0))

        for campo in campos_exigidos:
            label = str(campo.get("label_campo") or "")
            ext_csv = str(campo.get("extensoes_permitidas") or "").strip()
            obrig = bool(campo.get("obrigatorio"))
            estado_campos[label] = {
                "state": "pendente",
                "id_upload": 0,
                "arquivo_local": "",
                "obrigatorio": obrig,
            }

            row = tk.Frame(inner, bg=_C)
            row.pack(fill="x", pady=(6, 0))

            txt_label = label + (" *" if obrig else "")
            ext_hint = f" ({ext_csv})" if ext_csv else ""
            tk.Label(row, text=txt_label + ext_hint, bg=_C, fg="#ffffff",
                     font=("Segoe UI", 9, "bold"), width=28, anchor="w").pack(side="left")

            var_status_campo = tk.StringVar(value="pendente")
            lbl_status_campo = tk.Label(row, textvariable=var_status_campo, bg=_C, fg=_PEND,
                                        font=("Segoe UI", 9), width=24, anchor="w")
            lbl_status_campo.pack(side="left", padx=(8, 8))

            pbar = ttk.Progressbar(row, mode="indeterminate", length=120)

            btn_sel = ttk.Button(row, text="Selecionar arquivo")
            btn_sel.pack(side="right")

            estado_campos[label]["label_status"] = lbl_status_campo
            estado_campos[label]["var_status"] = var_status_campo
            estado_campos[label]["pbar"] = pbar
            estado_campos[label]["botao"] = btn_sel

            def _fazer_handler(label_local: str, ext_local: str,
                                pbar_local: ttk.Progressbar, btn_local: ttk.Button) -> Callable[[], None]:
                def _handler() -> None:
                    self._iniciar_upload_mega(
                        janela=janela,
                        api=api,
                        obter_uploader=_obter_uploader,
                        pasta_logica=pasta_logica,
                        pasta_raiz_mega=pasta_raiz_mega,
                        nome_campo=label_local,
                        extensoes_csv=ext_local,
                        estado_entry=estado_campos[label_local],
                        pbar=pbar_local,
                        botao=btn_local,
                        atualizar_botao_salvar=_atualizar_botao_salvar,
                        filedialog=_filedialog,
                        cores=(_OK, _ERRO, _PEND),
                    )
                return _handler

            btn_sel.configure(command=_fazer_handler(label, ext_csv, pbar, btn_sel))

        # ====================================================
        # Seção 3: Canal + Data + Observação + Tempo
        # ====================================================
        tk.Frame(inner, bg="#222", height=1).pack(fill="x", pady=(12, 8))

        canal_inicial = (str(getattr(subtarefa, "canal_entrega", "") or "") if subtarefa else self._titulo_atividade)
        var_canal = tk.StringVar(value=canal_inicial)
        var_observacao = tk.StringVar(value=(str(getattr(subtarefa, "observacao", "") or "") if subtarefa else ""))
        referencia_atual = getattr(subtarefa, "referencia_data", None) if subtarefa else self._referencia_data
        var_referencia = tk.StringVar(
            value=(referencia_atual.strftime("%d/%m/%Y") if isinstance(referencia_atual, date) else self._referencia_data.strftime("%d/%m/%Y"))
        )
        subtarefa_concluida = bool(getattr(subtarefa, "concluida", False)) if subtarefa else False
        var_tempo = tk.StringVar(
            value=(formatar_hhmmss(int(getattr(subtarefa, "segundos_gastos", 0) or 0)) if subtarefa_concluida else "00:00:00")
        )

        linha = tk.Frame(inner, bg=_C)
        linha.pack(fill="x")
        col_e = tk.Frame(linha, bg=_C)
        col_e.pack(side="left", fill="x", expand=True)
        col_d = tk.Frame(linha, bg=_C)
        col_d.pack(side="left", fill="x", expand=True, padx=(12, 0))

        tk.Label(col_e, text="CANAL", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Combobox(col_e, textvariable=var_canal, values=self._opcoes_canal,
                     state="readonly").pack(fill="x", pady=(3, 8))

        tk.Label(col_d, text="DATA DE REFERÊNCIA", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(col_d, textvariable=var_referencia).pack(fill="x", pady=(3, 8))

        tk.Label(inner, text="OBSERVAÇÃO", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(inner, textvariable=var_observacao).pack(fill="x", pady=(3, 8))

        tk.Label(inner, text="TEMPO GASTO  (HH:MM:SS)", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ent_tempo = ttk.Entry(inner, textvariable=var_tempo, width=18)
        ent_tempo.pack(anchor="w", pady=(3, 4))

        def _on_key_tempo(event: tk.Event) -> str:  # type: ignore[type-arg]
            if event.keysym == "BackSpace":
                digits = var_tempo.get().replace(":", "")
                digits = ("0" + digits[:-1])[-6:]
                var_tempo.set(f"{digits[0:2]}:{digits[2:4]}:{digits[4:6]}")
                return "break"
            if event.char.isdigit():
                digits = var_tempo.get().replace(":", "")
                digits = (digits[1:] + event.char)[-6:]
                var_tempo.set(f"{digits[0:2]}:{digits[2:4]}:{digits[4:6]}")
                return "break"
            if event.keysym in ("Tab", "ISO_Left_Tab", "Return"):
                return ""
            return "break"

        ent_tempo.bind("<Key>", _on_key_tempo)

        # ====================================================
        # Rodapé: Cancelar / Salvar (Concluir)
        # ====================================================
        tk.Frame(janela, bg="#282828", height=1).pack(fill="x")
        rodape = tk.Frame(janela, bg="#1a1a1a", padx=26, pady=12)
        rodape.pack(fill="x")

        var_aviso_bloqueio = tk.StringVar(value="")
        tk.Label(rodape, textvariable=var_aviso_bloqueio, bg="#1a1a1a", fg=_PEND,
                 font=("Segoe UI", 9), wraplength=460, justify="left").pack(side="left", fill="x", expand=True)

        var_texto_botao = tk.StringVar(value="Salvar")

        btn_cancelar = ttk.Button(rodape, text="Cancelar", command=janela.destroy)
        btn_cancelar.pack(side="right")
        btn_salvar = ttk.Button(rodape, textvariable=var_texto_botao, style="Primario.TButton")
        btn_salvar.pack(side="right", padx=(0, 8))

        def _atualizar_botao_salvar(*_a: object) -> None:
            tempo = (var_tempo.get() or "").strip()
            obrig_pendente: list[str] = []
            for nome, st in estado_campos.items():
                if st["obrigatorio"] and st["state"] != "concluido":
                    obrig_pendente.append(nome)

            if not pasta_logica["id_pasta_logica"]:
                var_aviso_bloqueio.set("Defina a pasta lógica antes de salvar.")
                btn_salvar.configure(state="disabled")
                var_texto_botao.set("Salvar e Concluir" if (tempo and not subtarefa_concluida) else "Salvar")
                return
            if obrig_pendente:
                var_aviso_bloqueio.set("Aguardando uploads obrigatórios: " + ", ".join(obrig_pendente))
                btn_salvar.configure(state="disabled")
                var_texto_botao.set("Salvar e Concluir" if (tempo and not subtarefa_concluida) else "Salvar")
                return
            var_aviso_bloqueio.set("")
            btn_salvar.configure(state="normal")
            if tempo and not subtarefa_concluida:
                var_texto_botao.set("Salvar e Concluir")
            else:
                var_texto_botao.set("Salvar")

        var_tempo.trace_add("write", _atualizar_botao_salvar)
        _atualizar_botao_salvar()

        def salvar() -> None:
            deve_concluir = var_texto_botao.get() == "Salvar e Concluir"
            btn_salvar.configure(state="disabled")
            btn_cancelar.configure(state="disabled")
            var_texto_botao.set("Salvando…")
            janela.update_idletasks()

            try:
                referencia_data = self._converter_texto_para_data(var_referencia.get())
                tempo_texto = (var_tempo.get() or "").strip()
                segundos_tempo = self._converter_texto_tempo_para_segundos(tempo_texto) if tempo_texto else 0
            except Exception as erro:
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                _atualizar_botao_salvar()
                messagebox.showerror("Erro", str(erro), parent=janela)
                return

            uid = self._usuario_id()
            id_atividade = self._id_atividade
            titulo = pasta_logica["nome_pasta"]
            canal = var_canal.get()
            observacao = var_observacao.get()
            segundos_trabalhando = self._segundos_trabalhando
            id_sub = int(getattr(subtarefa, "id_subtarefa", 0)) if subtarefa else 0

            # Duplicidade só se trocou de pasta lógica.
            tit_norm = titulo.strip().lower()
            for sub_existente in self._subtarefas:
                sub_id_check = int(getattr(sub_existente, "id_subtarefa", 0))
                if id_sub and sub_id_check == id_sub:
                    continue
                if str(getattr(sub_existente, "titulo", "") or "").strip().lower() == tit_norm:
                    btn_salvar.configure(state="normal")
                    btn_cancelar.configure(state="normal")
                    _atualizar_botao_salvar()
                    messagebox.showwarning("Atenção", "Já existe uma tarefa com esse nome.", parent=janela)
                    return

            def _operacao() -> int:
                if subtarefa is None:
                    if self._id_subtarefa_criada_nesta_janela is None:
                        self._id_subtarefa_criada_nesta_janela = self._repositorio.criar_subtarefa(
                            user_id=uid,
                            referencia_data=referencia_data,
                            id_atividade=id_atividade,
                            titulo=titulo,
                            canal_entrega=canal,
                            observacao=observacao,
                        )
                    novo_id = self._id_subtarefa_criada_nesta_janela
                    if deve_concluir:
                        self._repositorio.concluir_subtarefa(
                            user_id=uid,
                            id_subtarefa=novo_id,
                            segundos_gastos=segundos_tempo,
                            referencia_data=referencia_data,
                            canal_entrega=canal,
                            observacao=observacao,
                            segundos_monitorados_adicionais=segundos_trabalhando,
                        )
                    return int(novo_id or 0)

                if subtarefa_concluida:
                    self._repositorio.atualizar_subtarefa(
                        user_id=uid, id_subtarefa=id_sub,
                        titulo=titulo, canal_entrega=canal, observacao=observacao,
                        referencia_data=referencia_data,
                        segundos_gastos=segundos_tempo if tempo_texto else None,
                        segundos_monitorados_adicionais=segundos_trabalhando,
                    )
                else:
                    self._repositorio.atualizar_subtarefa(
                        user_id=uid, id_subtarefa=id_sub,
                        titulo=titulo, canal_entrega=canal, observacao=observacao,
                        referencia_data=referencia_data,
                    )
                    if deve_concluir:
                        self._repositorio.concluir_subtarefa(
                            user_id=uid, id_subtarefa=id_sub,
                            segundos_gastos=segundos_tempo,
                            referencia_data=referencia_data,
                            canal_entrega=canal, observacao=observacao,
                            segundos_monitorados_adicionais=segundos_trabalhando,
                        )
                return id_sub

            def _ok(id_subtarefa_final: object) -> None:
                # Vincula uploads à subtarefa (post-hoc): mesmo que tenham sido
                # criados antes da subtarefa existir, agora atualizamos com o id.
                id_final = int(id_subtarefa_final or 0)
                for nome_c, st in estado_campos.items():
                    id_up = int(st.get("id_upload") or 0)
                    if id_up and id_final:
                        try:
                            api.registrar_upload(
                                id_upload=id_up,
                                id_pasta_logica=int(pasta_logica["id_pasta_logica"]),
                                nome_campo=nome_c,
                                nome_arquivo=str(st.get("arquivo_local") or ""),
                                status_upload=str(st.get("state") or "concluido"),
                                id_subtarefa=id_final,
                            )
                        except Exception:
                            pass  # vinculação é nice-to-have

                self._id_subtarefa_criada_nesta_janela = None
                try:
                    janela.destroy()
                except Exception:
                    pass
                self._recarregar_dados()

            def _falha(erro: Exception) -> None:
                btn_salvar.configure(state="normal")
                btn_cancelar.configure(state="normal")
                _atualizar_botao_salvar()
                messagebox.showerror("Erro", str(erro), parent=janela)

            self._executar_em_background(_operacao, _ok, _falha)

        btn_salvar.configure(command=salvar)

    def _iniciar_upload_mega(
        self,
        *,
        janela: tk.Toplevel,
        api: object,
        obter_uploader: Callable[[], object],
        pasta_logica: dict,
        pasta_raiz_mega: str,
        nome_campo: str,
        extensoes_csv: str,
        estado_entry: dict,
        pbar: ttk.Progressbar,
        botao: ttk.Button,
        atualizar_botao_salvar: Callable[[], None],
        filedialog: object,
        cores: tuple[str, str, str],
    ) -> None:
        """Pipeline de upload de UM arquivo:
        1. Filedialog → caminho local (filtrado por extensões).
        2. Pasta lógica precisa estar definida.
        3. POST `desktop_registrar_upload.php` (status=enviando) → id_upload.
        4. `MegaUploader.upload_arquivo()` em background.
        5. POST `desktop_registrar_upload.php` (status=concluido|erro).
        6. Atualiza UI (cor do label, progressbar, botão).
        """
        from app.mega_uploader import ErroCredencialFaltando, ErroMega
        cor_ok, cor_erro, cor_pend = cores
        var_status = estado_entry["var_status"]
        lbl_status = estado_entry["label_status"]

        if not pasta_logica["id_pasta_logica"]:
            messagebox.showwarning(
                "Atenção",
                "Defina a pasta lógica do vídeo antes de selecionar arquivos.",
                parent=janela,
            )
            return

        # Filtra extensões pro filedialog
        if extensoes_csv:
            partes = [e.strip().lstrip(".") for e in extensoes_csv.split(",") if e.strip()]
            filetypes = [(f"Arquivos {extensoes_csv}", " ".join(f"*.{e}" for e in partes)), ("Todos", "*.*")]
        else:
            filetypes = [("Todos", "*.*")]

        caminho = filedialog.askopenfilename(parent=janela, title=f"Selecionar arquivo — {nome_campo}",
                                              filetypes=filetypes)
        if not caminho:
            return

        # Valida extensão se restrita
        if extensoes_csv:
            ext_arq = caminho.rsplit(".", 1)[-1].lower() if "." in caminho else ""
            permitidas = [e.strip().lower().lstrip(".") for e in extensoes_csv.split(",")]
            if ext_arq not in permitidas:
                messagebox.showwarning("Atenção",
                    f"Extensão .{ext_arq} não permitida. Aceitas: {extensoes_csv}",
                    parent=janela)
                return

        from pathlib import Path as _Path
        arquivo = _Path(caminho)
        tamanho = arquivo.stat().st_size if arquivo.exists() else None
        nome_arq = arquivo.name

        estado_entry["arquivo_local"] = str(arquivo)
        estado_entry["state"] = "enviando"
        var_status.set("enviando…")
        lbl_status.configure(fg=cor_pend)
        pbar.pack(side="left", padx=(0, 8))
        pbar.start(10)
        botao.configure(state="disabled")
        atualizar_botao_salvar()

        # Etapa 1: registra upload no painel (status=enviando)
        pasta_remota = f"/{pasta_raiz_mega.strip('/')}/{pasta_logica['nome_pasta']}/"

        def _op() -> bool:
            api_local = api  # type: PainelMegaApi  # type: ignore[name-defined]
            r = api_local.registrar_upload(  # type: ignore[attr-defined]
                id_pasta_logica=int(pasta_logica["id_pasta_logica"]),
                nome_campo=nome_campo,
                nome_arquivo=nome_arq,
                status_upload="enviando",
                tamanho_bytes=tamanho,
            )
            estado_entry["id_upload"] = int(r.get("id_upload") or 0)

            # Etapa 2: upload real
            uploader = obter_uploader()
            uploader.upload_arquivo(arquivo, pasta_remota)  # type: ignore[attr-defined]

            # Etapa 3: marca como concluido
            if estado_entry["id_upload"]:
                api_local.registrar_upload(  # type: ignore[attr-defined]
                    id_upload=int(estado_entry["id_upload"]),
                    id_pasta_logica=int(pasta_logica["id_pasta_logica"]),
                    nome_campo=nome_campo,
                    nome_arquivo=nome_arq,
                    status_upload="concluido",
                    tamanho_bytes=tamanho,
                )
            return True

        def _ok(_: object) -> None:
            pbar.stop()
            pbar.pack_forget()
            estado_entry["state"] = "concluido"
            var_status.set("✓ enviado")
            lbl_status.configure(fg=cor_ok)
            botao.configure(state="normal", text="Trocar arquivo")
            atualizar_botao_salvar()

        def _falha(erro: Exception) -> None:
            pbar.stop()
            pbar.pack_forget()
            estado_entry["state"] = "erro"
            msg_curta = str(erro)[:60]
            var_status.set(f"✗ {msg_curta}")
            lbl_status.configure(fg=cor_erro)
            botao.configure(state="normal", text="Tentar de novo")
            atualizar_botao_salvar()
            # Reporta no painel também, melhor effort
            id_up = int(estado_entry.get("id_upload") or 0)
            if id_up:
                try:
                    api.registrar_upload(  # type: ignore[attr-defined]
                        id_upload=id_up,
                        id_pasta_logica=int(pasta_logica["id_pasta_logica"]),
                        nome_campo=nome_campo,
                        nome_arquivo=nome_arq,
                        status_upload="erro",
                        mensagem_erro=str(erro)[:500],
                    )
                except Exception:
                    pass
            # Erros críticos: aviso explícito
            if isinstance(erro, ErroCredencialFaltando):
                messagebox.showerror(
                    "MEGA",
                    "Credenciais MEGA (mega_email / mega_password) não configuradas no painel. "
                    "Peça ao admin pra cadastrar na aba Credenciais (modo global).",
                    parent=janela,
                )
            elif isinstance(erro, ErroMega):
                messagebox.showerror("MEGA", str(erro), parent=janela)

        self._executar_em_background(_op, _ok, _falha)

    def _converter_texto_para_data(self, texto: str) -> date:
        texto = (texto or "").strip()
        for formato in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, formato).date()
            except Exception:
                pass
        raise RuntimeError("Data inválida. Use DD/MM/AAAA.")

    def _converter_texto_tempo_para_segundos(self, texto: str) -> int:
        texto = (texto or "").strip()
        partes = texto.split(":")
        if len(partes) == 2:
            horas = int(partes[0] or "0")
            minutos = int(partes[1] or "0")
            segundos = 0
        elif len(partes) == 3:
            horas = int(partes[0] or "0")
            minutos = int(partes[1] or "0")
            segundos = int(partes[2] or "0")
        else:
            raise RuntimeError("Use o tempo em HH:MM:SS ou HH:MM.")

        if horas < 0 or minutos < 0 or segundos < 0 or minutos > 59 or segundos > 59:
            raise RuntimeError("Tempo inválido. Use HH:MM:SS.")

        total = int(horas * 3600 + minutos * 60 + segundos)
        if total <= 0:
            raise RuntimeError("Informe um tempo maior que zero.")
        return total

    def _montar_relatorio_final(self) -> str:
        subtarefas = self._repositorio.listar_subtarefas_do_dia(
            self._usuario_id(),
            self._referencia_data,
            self._id_atividade,
        )
        concluidas = [sub for sub in subtarefas if bool(getattr(sub, "concluida", False))]
        if not concluidas:
            raise RuntimeError("Conclua pelo menos uma subtarefa antes de finalizar.")

        linhas: list[str] = []
        concluidas_ordenadas = sorted(
            concluidas,
            key=lambda item: (
                getattr(item, "concluida_em", None) or datetime.min,
                int(getattr(item, "id_subtarefa", 0) or 0),
            ),
        )

        for subtarefa in concluidas_ordenadas:
            tempo = formatar_hhmmss(int(getattr(subtarefa, "segundos_gastos", 0) or 0))
            titulo = str(getattr(subtarefa, "titulo", "") or "")
            canal = str(getattr(subtarefa, "canal_entrega", "") or "")
            observacao = str(getattr(subtarefa, "observacao", "") or "")
            partes = [tempo, titulo]
            if canal:
                partes.append(f"Canal: {canal}")
            if observacao:
                partes.append(observacao)
            linhas.append("- " + " | ".join(partes))

        return (
            f"Relatório do dia ({self._referencia_data.strftime('%Y-%m-%d')}), atividade #{self._id_atividade}\n"
            + "\n".join(linhas)
        )

    def _enviar_e_finalizar(self) -> None:
        from app.config import TOLERANCIA_VALIDACAO_SEGUNDOS

        if not callable(self._ao_finalizar):
            self.destroy()
            return

        try:
            resumo = self._repositorio.obter_resumo_do_dia(
                self._usuario_id(),
                self._referencia_data,
                self._id_atividade,
                segundos_monitorados_adicionais=self._segundos_trabalhando,
            )
        except Exception as erro:
            messagebox.showerror("Erro", str(erro), parent=self)
            return

        total_concluidas = int(resumo.get("total_concluidas") or 0)
        monitorado = int(resumo.get("monitorado_segundos") or 0)
        declarado = int(resumo.get("declarado_segundos") or 0)

        if total_concluidas <= 0 or declarado <= 0:
            messagebox.showwarning(
                "Atenção",
                "Conclua pelo menos uma subtarefa com tempo antes de enviar para o servidor.",
                parent=self,
            )
            return

        if declarado > (monitorado + int(TOLERANCIA_VALIDACAO_SEGUNDOS)):
            messagebox.showwarning(
                "Atenção",
                "O total declarado ultrapassa o tempo monitorado pelo cronômetro.",
                parent=self,
            )
            return

        try:
            relatorio = self._montar_relatorio_final()
            self._ao_finalizar(relatorio)
        except Exception as erro:
            messagebox.showerror("Erro", str(erro), parent=self)
            return

        self.destroy()
