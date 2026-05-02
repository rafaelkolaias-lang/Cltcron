"""Janela "Tarefas da Atividade" / "Declarar Tarefa"."""
from __future__ import annotations

import json as _json
import threading
import tkinter as tk
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import date, datetime
from tkinter import messagebox, ttk

from app.win32_utils import formatar_hhmmss
from declaracoes_dia import RepositorioDeclaracoesDia


def _headers_auth_pix(user_id: str, chave: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {user_id}:{chave}",
        "X-User-Id": user_id,
        "X-User-Chave": chave,
        "Accept": "application/json",
    }


def _http_pix_obter(url_painel: str, user_id: str, chave: str, timeout: float = 8.0) -> dict:
    url = f"{url_painel.rstrip('/')}/commands/usuarios/api/obter_pix.php"
    req = urllib.request.Request(url, headers=_headers_auth_pix(user_id, chave), method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL controlada por config)
        corpo = resp.read().decode("utf-8", errors="replace")
    try:
        payload = _json.loads(corpo)
    except _json.JSONDecodeError as e:
        raise RuntimeError(f"resposta inválida do servidor: {corpo[:120]}") from e
    if not payload.get("ok"):
        raise RuntimeError(str(payload.get("mensagem") or "erro desconhecido"))
    return dict(payload.get("dados") or {})


def _http_pix_salvar(url_painel: str, user_id: str, chave: str, valor: str, timeout: float = 8.0) -> dict:
    url = f"{url_painel.rstrip('/')}/commands/usuarios/api/salvar_pix.php"
    corpo_req = _json.dumps({"chave_pix": valor}).encode("utf-8")
    headers = _headers_auth_pix(user_id, chave)
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=corpo_req, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            corpo = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        # Lê corpo do erro pra extrair a mensagem (ex: 400 "CNPJ inválido…")
        try:
            corpo_err = e.read().decode("utf-8", errors="replace")
            payload_err = _json.loads(corpo_err)
            raise RuntimeError(str(payload_err.get("mensagem") or e.reason)) from e
        except (_json.JSONDecodeError, AttributeError):
            raise RuntimeError(str(e.reason)) from e
    try:
        payload = _json.loads(corpo)
    except _json.JSONDecodeError as e:
        raise RuntimeError(f"resposta inválida do servidor: {corpo[:120]}") from e
    if not payload.get("ok"):
        raise RuntimeError(str(payload.get("mensagem") or "erro desconhecido"))
    return dict(payload.get("dados") or {})


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
        mapa_canal_para_id: dict[str, int] | None = None,
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
        self._mapa_canal_para_id: dict[str, int] = dict(mapa_canal_para_id or {})
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

        # Tarefa 2: status da sincronização MEGA. Atualizado por listener
        # registrado em mega_sync; controla habilitar/desabilitar do botão
        # "Declarar Tarefa".
        self._var_status_sync_mega = tk.StringVar(value="")
        self._btn_declarar: ttk.Button | None = None
        self._listener_mega_sync = self._ao_mudar_estado_mega_sync

        self._montar_tela()

        # Aplica estado inicial de sync MEGA + se inscreve nas mudanças.
        try:
            from app import mega_sync
            mega_sync.registrar_listener(self._listener_mega_sync)
            estado_inicial = mega_sync.obter_estado_atual_mega_sync(self._usuario_id())
            self._aplicar_estado_mega_sync_na_ui(estado_inicial)
        except Exception:
            pass

        # Garante remoção do listener quando a janela fechar (Fechar/Cancelar
        # ou WM_DELETE_WINDOW). bind WM_DELETE pra cobrir o "X" também.
        self.protocol("WM_DELETE_WINDOW", self._ao_fechar_janela_subs)

        # Bloqueios e abatimentos de pagamento são gravados pelo painel web
        # (painel/commands/pagamentos/_aplicar_pagamento.php) no momento do pagamento.
        # O desktop apenas lê — não precisa sincronizar nada na abertura.

        self._recarregar_dados()

    def _usuario_id(self) -> str:
        return str(self._usuario.get("user_id") or "").strip()

    # ---------------------------------------------------------------
    # Tarefa 2 — UI da sincronização MEGA
    # ---------------------------------------------------------------
    def _ao_mudar_estado_mega_sync(self, user_id: str, estado: dict) -> None:
        """Callback registrado em mega_sync — chamado em thread arbitrária.
        Marshall pra UI thread via after()."""
        if str(user_id) != self._usuario_id():
            return
        try:
            self.after(0, lambda: self._aplicar_estado_mega_sync_na_ui(estado))
        except Exception:
            pass

    def _aplicar_estado_mega_sync_na_ui(self, estado: dict) -> None:
        """Aplica o estado de sync MEGA: habilita/desabilita botão Declarar
        Tarefa e ajusta seu texto + status do rodapé."""
        if not self.winfo_exists():
            return
        status = str(estado.get("status") or "nao_sincronizado").lower()
        msg_erro = str(estado.get("mensagem_erro") or "").strip()
        ultima_ok = str(estado.get("ultima_sync_ok") or "").strip()

        btn = self._btn_declarar
        if btn is None:
            return

        if status == "sincronizando":
            try: btn.configure(text="SINCRONIZANDO", state="disabled")
            except Exception: pass
            self._var_status_sync_mega.set("Sincronizando pastas MEGA…")
        elif status == "erro":
            try: btn.configure(text="Declarar Tarefa", state="disabled")
            except Exception: pass
            resumo_erro = msg_erro[:80] + ("…" if len(msg_erro) > 80 else "")
            self._var_status_sync_mega.set(f"Pastas MEGA não sincronizadas: {resumo_erro}")
        elif status == "sincronizado":
            try: btn.configure(text="Declarar Tarefa", state="normal")
            except Exception: pass
            self._var_status_sync_mega.set(
                f"Pastas MEGA sincronizadas em {ultima_ok}" if ultima_ok else ""
            )
        else:  # "nao_sincronizado"
            try: btn.configure(text="Declarar Tarefa", state="disabled")
            except Exception: pass
            self._var_status_sync_mega.set("Aguardando sincronização MEGA…")

    def _ao_fechar_janela_subs(self) -> None:
        """Cleanup ao fechar a janela: desregistra listener da sync MEGA."""
        try:
            from app import mega_sync
            mega_sync.remover_listener(self._listener_mega_sync)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _forcar_sync_mega_debug(self) -> None:
        """Botão de debug: dispara `mega_sync.executar_sincronizacao_async`
        ignorando o controle "1× ao dia" (limpa `data_sync_ok` antes).
        """
        user_id = str(self._usuario.get("user_id") or "").strip()
        chave = str(self._usuario.get("chave") or "").strip()
        if not user_id or not chave:
            messagebox.showerror("Atualizar MEGA", "Login não disponível.", parent=self)
            return

        try:
            from app import mega_sync
            from app.config import (
                APP_CLIENT_DECRYPT_KEY,
                URL_PAINEL,
                carregar_estado_mega_sync,
                salvar_estado_mega_sync,
            )
            from app.mega_uploader import MegaUploader, PainelMegaApi
        except Exception as e:
            messagebox.showerror("Atualizar MEGA", f"Falha ao importar dependências:\n{e}", parent=self)
            return

        if not URL_PAINEL or not APP_CLIENT_DECRYPT_KEY:
            messagebox.showerror(
                "Atualizar MEGA",
                "URL do painel ou chave de cliente ausente — sync indisponível neste ambiente.",
                parent=self,
            )
            return

        # Reseta o flag "1× ao dia" pra forçar a execução agora.
        try:
            estado = carregar_estado_mega_sync(user_id)
            estado["data_sync_ok"] = None
            salvar_estado_mega_sync(user_id, estado)
        except Exception:
            pass

        try:
            api = PainelMegaApi(URL_PAINEL, user_id, chave)
            uploader = MegaUploader(URL_PAINEL, user_id, chave, APP_CLIENT_DECRYPT_KEY)
            iniciado = mega_sync.executar_sincronizacao_async(user_id, uploader, api)
        except Exception as e:
            messagebox.showerror("Atualizar MEGA", f"Falha ao disparar sync:\n{e}", parent=self)
            return

        if not iniciado:
            messagebox.showinfo(
                "Atualizar MEGA",
                "Já existe uma sincronização em andamento. Aguarde terminar.",
                parent=self,
            )

    def _abrir_modal_configurar_pix(self) -> None:
        """Abre modal "Configurar Pix" — só puxa a chave atual do servidor ao abrir.

        Fluxo: vazio → campo vazio. Já cadastrada → mostra em texto aberto pra editar.
        Validação local antes de enviar (CNPJ, celular, e-mail; recusa CPF/aleatória).
        """
        try:
            from app.config import URL_PAINEL
        except Exception:
            URL_PAINEL = ""
        user_id = str(self._usuario.get("user_id") or "").strip()
        chave_user = str(self._usuario.get("chave") or "").strip()
        if not URL_PAINEL or not user_id or not chave_user:
            messagebox.showerror("Configurar Pix", "Login não disponível para acessar o servidor.", parent=self)
            return

        modal = tk.Toplevel(self)
        modal.title("Configurar chave Pix")
        modal.configure(bg="#111111")
        modal.transient(self)
        modal.grab_set()
        modal.resizable(False, False)
        modal.geometry("520x280")

        ttk.Label(modal, text="Chave Pix do usuário", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(
            modal,
            text="Tipos aceitos: CNPJ, celular ou e-mail. CPF e chave aleatória não são aceitos.",
            wraplength=480,
        ).pack(anchor="w", padx=16, pady=(0, 8))

        var_chave = tk.StringVar()
        entrada = ttk.Entry(modal, textvariable=var_chave, width=58)
        entrada.pack(padx=16, pady=(0, 6), fill="x")

        var_status = tk.StringVar(value="Carregando chave atual…")
        lbl_status = ttk.Label(modal, textvariable=var_status, foreground="#9ca3af")
        lbl_status.pack(anchor="w", padx=16, pady=(0, 8))

        rodape = ttk.Frame(modal)
        rodape.pack(side="bottom", fill="x", padx=16, pady=(0, 16))

        btn_salvar = ttk.Button(rodape, text="Salvar", style="Primario.TButton")
        btn_cancelar = ttk.Button(rodape, text="Cancelar", command=modal.destroy)
        btn_cancelar.pack(side="right")
        btn_salvar.pack(side="right", padx=(0, 8))

        def _aplicar_status(texto: str, cor: str = "#9ca3af") -> None:
            try:
                var_status.set(texto)
                lbl_status.configure(foreground=cor)
            except Exception:
                pass

        def _carregar_atual() -> None:
            try:
                resultado = _http_pix_obter(URL_PAINEL, user_id, chave_user)
                def aplicar() -> None:
                    valor = (resultado.get("chave_pix") or "") if isinstance(resultado, dict) else ""
                    var_chave.set(valor)
                    if valor:
                        tipo = (resultado.get("tipo") or "").strip()
                        rotulo = {"cnpj": "CNPJ", "celular": "Celular", "email": "E-mail"}.get(tipo, "")
                        _aplicar_status(f"Chave atual ({rotulo}). Edite e clique Salvar." if rotulo else "Chave atual carregada. Edite e clique Salvar.", "#9ca3af")
                    else:
                        _aplicar_status("Nenhuma chave cadastrada. Digite sua chave Pix.", "#9ca3af")
                    try:
                        entrada.focus_set()
                    except Exception:
                        pass
                modal.after(0, aplicar)
            except Exception as e:
                msg_err = str(e)
                modal.after(0, lambda: _aplicar_status(f"Falha ao carregar: {msg_err}", "#ef4444"))

        threading.Thread(target=_carregar_atual, daemon=True).start()

        def _salvar() -> None:
            from app.validador_pix import ErroPixInvalido, validar_pix
            valor_bruto = var_chave.get()
            try:
                tipo, valor_norm = validar_pix(valor_bruto)
            except ErroPixInvalido as e:
                _aplicar_status(str(e), "#ef4444")
                return
            btn_salvar.configure(state="disabled")
            btn_cancelar.configure(state="disabled")
            _aplicar_status("Salvando…", "#9ca3af")

            def worker() -> None:
                try:
                    _http_pix_salvar(URL_PAINEL, user_id, chave_user, valor_norm)
                    def ok() -> None:
                        try:
                            modal.destroy()
                        except Exception:
                            pass
                        messagebox.showinfo("Configurar Pix", "Chave Pix salva com sucesso.", parent=self)
                    modal.after(0, ok)
                except Exception as e:
                    msg_err = str(e)
                    def fail() -> None:
                        try:
                            btn_salvar.configure(state="normal")
                            btn_cancelar.configure(state="normal")
                        except Exception:
                            pass
                        _aplicar_status(f"Falha ao salvar: {msg_err}", "#ef4444")
                    modal.after(0, fail)

            threading.Thread(target=worker, daemon=True).start()

        btn_salvar.configure(command=_salvar)

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
            text="Tarefas declaradas — todos os canais",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            topo,
            text=(
                f"Data: {self._referencia_data.strftime('%d/%m/%Y')}    |    "
                f"Trabalhado (sessão): {formatar_hhmmss(self._segundos_trabalhando)}    |    "
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
            textvariable=self._var_status_sync_mega,
            font=("Segoe UI", 9),
            foreground="#f0c075",
            wraplength=1160,
        ).pack(anchor="w", pady=(6, 0))

        barra_acoes = ttk.Frame(quadro)
        barra_acoes.pack(fill="x", pady=(14, 10))

        self._btn_declarar = ttk.Button(barra_acoes, text="Declarar Tarefa", style="Primario.TButton", command=self._nova_subtarefa)
        self._btn_declarar.pack(side="left")
        ttk.Button(barra_acoes, text="Editar", command=self._editar_subtarefa).pack(side="left", padx=(8, 0))
        ttk.Button(barra_acoes, text="Excluir", style="Perigo.TButton", command=self._excluir_subtarefa).pack(side="left", padx=(8, 0))
        ttk.Button(barra_acoes, text="Atualizar", command=self._recarregar_dados).pack(side="right")
        ttk.Button(barra_acoes, text="Atualizar MEGA", command=self._forcar_sync_mega_debug).pack(side="right", padx=(0, 8))

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
            ttk.Button(botoes_finais, text="Cancelar", command=self._ao_fechar_janela_subs).pack(side="right", padx=(0, 8))
            ttk.Button(botoes_finais, text="Configurar Pix", command=self._abrir_modal_configurar_pix).pack(side="right", padx=(0, 8))
        else:
            ttk.Button(botoes_finais, text="Fechar", command=self._ao_fechar_janela_subs).pack(side="right")
            ttk.Button(botoes_finais, text="Configurar Pix", command=self._abrir_modal_configurar_pix).pack(side="right", padx=(0, 8))

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
            self._var_trava.set("Sem pagamento registrado para este usuário.")
            return

        if self._referencia_data < travado_ate:
            self._var_trava.set(
                f"Pago em {travado_ate.strftime('%d/%m/%Y')}. Datas anteriores não podem mais ser editadas."
            )
        else:
            self._var_trava.set(
                f"Pago em {travado_ate.strftime('%d/%m/%Y')}. Tarefas após o pagamento ainda podem ser alteradas."
            )

    def _recarregar_dados(self) -> None:
        self._var_resumo.set("Carregando...")

        user_id = self._usuario_id()
        # Janela "Tarefas da Atividade" agora é overview do user inteiro:
        # mostra tarefas/horas de TODOS os canais (não filtra por self._id_atividade).
        # A precisão por canal acontece no form "Declarar Tarefa" — onde o canal
        # selecionado define a pasta MEGA, os campos e o id_atividade da sub.
        segundos_trabalhando = self._segundos_trabalhando

        def _buscar() -> tuple:
            subtarefas = self._repositorio.listar_subtarefas_do_dia(user_id, id_atividade=0)
            resumo = self._repositorio.obter_resumo_do_dia(
                user_id,
                id_atividade=0,
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

            # Configurar tag visual para linhas de pagamento e tarefas Abertas.
            # "Aberta" = sub criada automaticamente após primeiro upload mas
            # ainda sem tempo declarado (concluida=0). Visual chamativo pra
            # lembrar o usuário de finalizar (preencher tempo + Salvar).
            self._arvore.tag_configure("pagamento", foreground="#00cc66", background="#1a2e1a")
            self._arvore.tag_configure("aberta", foreground="#ff6b6b", background="#3a1a1a")

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
                # Tag "aberta" deixa a linha em vermelho discreto — só aplica
                # a subs com concluida=0 (sem tempo informado ainda).
                _tags: tuple = ("aberta",) if not bool(getattr(subtarefa, "concluida", False)) else ()
                itens_mesclados.append((
                    dt_ord,
                    f"subtarefa_{id_sub}",
                    (_titulo, _canal, _status, self._formatar_data(ref), formatar_hhmmss(_segundos), _obs, _bloqueio),
                    _tags,
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
        chave = str(self._usuario.get("chave") or "").strip()

        try:
            from app.config import APP_CLIENT_DECRYPT_KEY, URL_PAINEL
        except Exception:
            APP_CLIENT_DECRYPT_KEY = ""
            URL_PAINEL = ""

        def _excluir_op() -> dict:
            # Resultado: {"removidos", "falhas", "pasta_removida", "mega_aplicado"}.
            # `mega_aplicado=False` significa que pulou o MEGA (sem auth ou sem
            # config). Banco é fonte da verdade — sempre apaga, mesmo se MEGA falhar.
            resultado: dict = {
                "removidos": 0,
                "falhas": [],
                "pasta_removida": False,
                "mega_aplicado": False,
            }

            if chave and APP_CLIENT_DECRYPT_KEY and URL_PAINEL:
                from app.mega_uploader import MegaUploader, PainelMegaApi
                api = PainelMegaApi(URL_PAINEL, user_id, chave)
                try:
                    dados = api.obter_dados_subtarefa(id_subtarefa)
                except Exception as e:
                    resultado["falhas"].append(f"falha ao buscar dados MEGA: {e}")
                    dados = None

                if dados and dados.get("upload_ativo") and dados.get("pasta_logica"):
                    resultado["mega_aplicado"] = True
                    pasta_raiz = str(dados.get("pasta_raiz_mega") or "").strip("/")
                    pasta_logica_d = dados["pasta_logica"]
                    nome_pasta = str(pasta_logica_d.get("nome_pasta") or "")
                    arquivos = dados.get("arquivos") or []
                    outras_subs = int(dados.get("outras_subtarefas_na_pasta") or 0)

                    try:
                        uploader = MegaUploader(URL_PAINEL, user_id, chave, APP_CLIENT_DECRYPT_KEY)
                    except Exception as e:
                        resultado["falhas"].append(f"erro ao iniciar MEGA: {e}")
                        uploader = None

                    if uploader is not None:
                        if outras_subs == 0:
                            # Sem outras subtarefas reusando: remove pasta inteira
                            # (cobre arquivos órfãos também).
                            caminho_pasta = f"/{pasta_raiz}/{nome_pasta}"
                            try:
                                if uploader.remover_pasta_recursiva(caminho_pasta):
                                    resultado["pasta_removida"] = True
                                    resultado["removidos"] = sum(
                                        1 for a in arquivos
                                        if a.get("status_upload") == "concluido"
                                    )
                                try:
                                    api.marcar_pasta_logica_inativa(
                                        int(pasta_logica_d.get("id_pasta_logica") or 0)
                                    )
                                except Exception as e:
                                    resultado["falhas"].append(
                                        f"pasta apagada no MEGA mas banco não foi atualizado: {e}"
                                    )
                            except Exception as e:
                                resultado["falhas"].append(f"falha ao remover pasta MEGA: {e}")
                        else:
                            # Outra subtarefa reusa a pasta — apaga só os arquivos desta sub.
                            for arq in arquivos:
                                if arq.get("status_upload") != "concluido":
                                    continue
                                nome_arq = str(arq.get("nome_arquivo") or "")
                                caminho = f"/{pasta_raiz}/{nome_pasta}/{nome_arq}"
                                try:
                                    if uploader.remover_arquivo(caminho):
                                        resultado["removidos"] += 1
                                except Exception as e:
                                    resultado["falhas"].append(
                                        f"falha ao remover {nome_arq}: {e}"
                                    )

            # Apaga do banco — sempre (banco é fonte da verdade).
            self._repositorio.excluir_subtarefa(user_id=user_id, id_subtarefa=id_subtarefa)
            return resultado

        def _ok(r: object) -> None:
            d = r if isinstance(r, dict) else {}
            falhas = d.get("falhas") or []
            if falhas:
                resumo = falhas[:5]
                extra = f"\n…e mais {len(falhas) - 5}" if len(falhas) > 5 else ""
                messagebox.showwarning(
                    "Subtarefa excluída — atenção MEGA",
                    "Subtarefa apagada, mas houve problemas no MEGA:\n\n• "
                    + "\n• ".join(resumo)
                    + extra
                    + "\n\nLimpe manualmente no MEGA, se necessário.",
                    parent=self,
                )
            self._recarregar_dados()

        self._executar_em_background(_excluir_op, _ok)

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

        # Em modo edição, busca a config do canal DA SUB (que pode ser
        # diferente do canal da janela — agora a JanelaSubtarefas mostra
        # subs de todos os canais do user). Em modo "nova", usa o canal
        # ativo da janela.
        id_ativ_lookup = self._id_atividade
        if subtarefa is not None:
            id_ativ_lookup = int(getattr(subtarefa, "id_atividade", 0) or self._id_atividade)

        def _buscar_config() -> dict | None:
            try:
                from app.mega_uploader import PainelMegaApi
                api = PainelMegaApi(URL_PAINEL, user_id, chave)
                return api.obter_config_canal(id_ativ_lookup, timeout=5.0)
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

        # Edição: prioriza titulo_atividade (canal real da sub) sobre
        # canal_entrega (texto livre legado).
        if subtarefa is not None:
            canal_inicial = (
                str(getattr(subtarefa, "titulo_atividade", "") or "")
                or str(getattr(subtarefa, "canal_entrega", "") or "")
                or self._titulo_atividade
            )
        else:
            canal_inicial = self._titulo_atividade

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
            # Em edição, usa o id_atividade da SUB (que pode ser diferente do
            # canal da janela — JanelaSubtarefas mostra subs de todos os canais).
            # Em modo "nova", usa o canal ativo da janela.
            id_atividade = self._id_atividade
            if subtarefa is not None:
                id_sub_ativ = int(getattr(subtarefa, "id_atividade", 0) or 0)
                if id_sub_ativ > 0:
                    id_atividade = id_sub_ativ
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
        # Permite trocar o canal em runtime (tarefa 7.4): id_atividade efetiva
        # e pasta raiz são mutáveis. Em edição de sub de outro canal, inicia
        # com o canal da SUB (não da janela) — porque a JanelaSubtarefas
        # agora mostra subs de todos os canais.
        id_inicial = self._id_atividade
        if subtarefa is not None:
            id_sub_ativ = int(getattr(subtarefa, "id_atividade", 0) or 0)
            if id_sub_ativ > 0:
                id_inicial = id_sub_ativ
        id_atividade_efetiva = {"id": id_inicial}
        pasta_raiz_holder = {"valor": pasta_raiz_mega}

        def _criar_sub_aberta_se_necessario() -> int:
            """Garante que existe uma subtarefa criada (concluida=0) pra
            vincular o upload. Chamado do `_op` do `_iniciar_upload_mega`
            depois que o upload concluiu com sucesso.

            Retorna o id_subtarefa final (0 se algo falhar).

            Em modo edição (subtarefa is not None) reusa a sub existente.
            Em modo "nova" cria a sub Aberta na primeira chamada e cacheia
            em `self._id_subtarefa_criada_nesta_janela` pra uploads
            subsequentes reusarem.
            """
            if subtarefa is not None:
                return int(getattr(subtarefa, "id_subtarefa", 0) or 0)
            if self._id_subtarefa_criada_nesta_janela is not None:
                return int(self._id_subtarefa_criada_nesta_janela)

            # Coleta dados do form pra criar a sub
            try:
                referencia = self._converter_texto_para_data(var_referencia.get())
            except Exception:
                referencia = self._referencia_data
            titulo = pasta_logica.get("nome_pasta") or ""
            canal = (var_canal.get() or "").strip()
            observacao = (var_observacao.get() or "").strip()

            try:
                novo_id = self._repositorio.criar_subtarefa(
                    user_id=self._usuario_id(),
                    referencia_data=referencia,
                    id_atividade=id_atividade_efetiva["id"],
                    titulo=titulo,
                    canal_entrega=canal,
                    observacao=observacao,
                )
                self._id_subtarefa_criada_nesta_janela = int(novo_id)
                return int(novo_id)
            except Exception:
                return 0
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
        var_pasta_raiz = tk.StringVar(value=f"Pasta raiz no MEGA: /{pasta_raiz_mega}")
        tk.Label(inner, textvariable=var_pasta_raiz, bg=_C, fg=_D,
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
        rad_criar = tk.Radiobutton(rad_frame, text="Criar nova", variable=modo_pasta, value="criar",
                                   bg=_C, fg="#ffffff", selectcolor="#222", activebackground=_C,
                                   font=("Segoe UI", 9))
        rad_criar.pack(side="left", padx=(0, 12))
        rad_selecionar = tk.Radiobutton(rad_frame, text="Selecionar existente", variable=modo_pasta,
                                         value="selecionar",
                                         bg=_C, fg="#ffffff", selectcolor="#222", activebackground=_C,
                                         font=("Segoe UI", 9))
        rad_selecionar.pack(side="left")

        # --- Modo "Criar nova" ---
        bloco_criar = tk.Frame(sec_pasta, bg=_C)

        var_numero = tk.StringVar(value="")
        var_titulo_pasta = tk.StringVar(value="")

        def _calcular_proximo_numero() -> str:
            # Calcula a partir das pastas já cadastradas no canal: max(numero_video)+1.
            maior = 0
            for p in pastas_existentes:
                try:
                    n = int(str(p.get("numero_video") or "0").strip().lstrip("0") or "0")
                except (TypeError, ValueError):
                    continue
                if n > maior:
                    maior = n
            return str(maior + 1).zfill(2)

        var_numero.set(_calcular_proximo_numero())

        linha_num = tk.Frame(bloco_criar, bg=_C)
        linha_num.pack(fill="x", pady=(2, 2))
        tk.Label(linha_num, text="Nº", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(side="left")
        # Read-only: número é autoritativo do banco para evitar colisão de
        # numeração quando dois usuários abrem o form ao mesmo tempo.
        tk.Label(linha_num, textvariable=var_numero, bg="#222", fg="#ffffff",
                 font=("Segoe UI", 9, "bold"), padx=10, pady=2).pack(side="left", padx=(6, 12))
        tk.Label(linha_num, text="Título", bg=_C, fg=_D, font=("Segoe UI", 8, "bold")).pack(side="left")
        ent_tit = ttk.Entry(linha_num, textvariable=var_titulo_pasta)
        ent_tit.pack(side="left", fill="x", expand=True, padx=(6, 0))

        var_preview = tk.StringVar(value="(digite o título)")
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
                var_preview.set("(digite o título)")

        var_numero.trace_add("write", _atualizar_preview)
        var_titulo_pasta.trace_add("write", _atualizar_preview)

        var_status_pasta = tk.StringVar(value="")
        lbl_status_pasta = tk.Label(bloco_criar, textvariable=var_status_pasta, bg=_C,
                                    fg=_D, font=("Segoe UI", 9))
        lbl_status_pasta.pack(anchor="w")

        btn_criar_pasta = ttk.Button(bloco_criar, text="Criar pasta lógica")
        btn_criar_pasta.pack(anchor="w", pady=(6, 0))

        def _criar_pasta(tentativa: int = 0) -> None:
            n = var_numero.get().strip()
            t = (var_titulo_pasta.get() or "").strip()
            if not t:
                messagebox.showwarning("Atenção", "Digite o título.", parent=janela)
                return
            if not n.isdigit():
                # Não deveria acontecer (número é setado pelo programa), mas
                # defensivo: força recálculo e tenta de novo.
                var_numero.set(_calcular_proximo_numero())
                n = var_numero.get().strip()

            btn_criar_pasta.configure(state="disabled")
            var_status_pasta.set("Criando pasta…")
            lbl_status_pasta.configure(fg=_PEND)

            def _op() -> dict:
                return api.criar_pasta_logica(id_atividade_efetiva["id"], n, t)

            def _ok(r: object) -> None:
                btn_criar_pasta.configure(state="normal")
                d = r if isinstance(r, dict) else {}
                pasta_logica["id_pasta_logica"] = int(d.get("id_pasta_logica") or 0)
                pasta_logica["nome_pasta"] = str(d.get("nome_pasta") or "")
                var_status_pasta.set(f"✓ pasta criada: {pasta_logica['nome_pasta']}")
                lbl_status_pasta.configure(fg=_OK)

                # Anexa a pasta criada no cache local e atualiza o combobox.
                pastas_existentes.append({
                    "id_pasta_logica": pasta_logica["id_pasta_logica"],
                    "nome_pasta": pasta_logica["nome_pasta"],
                    "numero_video": n,
                    "titulo_video": t,
                })
                cmb_pasta["values"] = [
                    str(p.get("nome_pasta") or "") for p in pastas_existentes
                ]
                var_pasta_existente.set(pasta_logica["nome_pasta"])

                # Switch pra "Selecionar existente" e bloqueia "Criar nova"
                # — evita o usuário criar acidentalmente outra pasta nesta
                # mesma janela.
                modo_pasta.set("selecionar")
                rad_criar.configure(state="disabled")

                _atualizar_botao_salvar()

            def _falha(e: Exception) -> None:
                from app.mega_uploader import ErroPainelHTTP
                eh_409 = (
                    isinstance(e, ErroPainelHTTP)
                    and getattr(e, "codigo_http", None) == 409
                )
                if eh_409 and tentativa == 0:
                    # Outro usuário criou uma pasta com esse número entre
                    # nosso cálculo e o INSERT — refetch silencioso e tenta
                    # de novo com o próximo número.
                    var_status_pasta.set("Outro usuário criou no mesmo número — recalculando…")
                    lbl_status_pasta.configure(fg=_PEND)

                    def _refetch() -> list:
                        cfg = api.obter_config_canal(id_atividade_efetiva["id"])
                        return list(cfg.get("pastas_logicas") or [])

                    def _ok_refetch(novas: object) -> None:
                        if isinstance(novas, list):
                            pastas_existentes.clear()
                            pastas_existentes.extend(novas)
                            cmb_pasta["values"] = [
                                str(p.get("nome_pasta") or "") for p in pastas_existentes
                            ]
                            var_numero.set(_calcular_proximo_numero())
                            _criar_pasta(tentativa=1)
                        else:
                            btn_criar_pasta.configure(state="normal")
                            var_status_pasta.set(f"✗ {e}")
                            lbl_status_pasta.configure(fg=_ERRO)

                    def _falha_refetch(_e2: Exception) -> None:
                        btn_criar_pasta.configure(state="normal")
                        var_status_pasta.set(f"✗ {e}")
                        lbl_status_pasta.configure(fg=_ERRO)

                    self._executar_em_background(_refetch, _ok_refetch, _falha_refetch)
                    return

                btn_criar_pasta.configure(state="normal")
                var_status_pasta.set(f"✗ {e}")
                lbl_status_pasta.configure(fg=_ERRO)

            self._executar_em_background(_op, _ok, _falha)

        btn_criar_pasta.configure(command=lambda: _criar_pasta(0))

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
                # Recalcula o próximo número toda vez que entra no modo —
                # cobre o caso de outro usuário ter criado uma pasta entre
                # o fetch inicial e a alternância.
                var_numero.set(_calcular_proximo_numero())
                bloco_selecionar.pack_forget()
                bloco_criar.pack(fill="x", pady=(2, 0))
            else:
                bloco_criar.pack_forget()
                bloco_selecionar.pack(fill="x", pady=(2, 0))

        modo_pasta.trace_add("write", _alternar_modo_pasta)
        _alternar_modo_pasta()

        def _atualizar_lock_pasta() -> None:
            # Trava a seleção da pasta lógica enquanto houver upload em
            # andamento ou concluído nesta janela. Sem isso, o usuário
            # poderia trocar a pasta no meio do upload e o arquivo subiria
            # pra pasta antiga, dessincronizando UI e MEGA.
            bloquear = any(
                st.get("state") in ("enviando", "concluido")
                for st in estado_campos.values()
            )
            try:
                cmb_pasta.configure(state=("disabled" if bloquear else "readonly"))
                rad_selecionar.configure(state=("disabled" if bloquear else "normal"))
                if bloquear:
                    rad_criar.configure(state="disabled")
                    btn_criar_pasta.configure(state="disabled")
            except Exception:
                pass

        # ====================================================
        # Seção 2: Uploads dinâmicos
        # ====================================================
        # Container reconstruível: ao trocar canal, os campos exigidos do novo
        # canal podem ser diferentes — `_construir_widgets_campos` destrói os
        # widgets antigos e recria a partir da nova lista.
        frame_uploads = tk.Frame(inner, bg=_C)
        frame_uploads.pack(fill="x")

        def _construir_widgets_campos(campos_lista: list) -> None:
            for child in list(frame_uploads.winfo_children()):
                try:
                    child.destroy()
                except Exception:
                    pass
            estado_campos.clear()

            tk.Frame(frame_uploads, bg="#222", height=1).pack(fill="x", pady=(8, 8))
            tk.Label(frame_uploads, text="ARQUIVOS PARA UPLOAD", bg=_C, fg=_D,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w")

            if not campos_lista:
                tk.Label(frame_uploads, text="(nenhum arquivo configurado pra você neste canal — só "
                                             "pasta lógica obrigatória)",
                         bg=_C, fg=_D, font=("Segoe UI", 9, "italic")).pack(anchor="w", pady=(4, 0))
                return

            for campo in campos_lista:
                label = str(campo.get("label_campo") or "")
                ext_csv = str(campo.get("extensoes_permitidas") or "").strip()
                obrig = bool(campo.get("obrigatorio"))
                estado_campos[label] = {
                    "state": "pendente",
                    "id_upload": 0,
                    "arquivo_local": "",
                    "obrigatorio": obrig,
                    "cancel_event": None,
                }

                row = tk.Frame(frame_uploads, bg=_C)
                row.pack(fill="x", pady=(6, 0))

                txt_label = label + (" *" if obrig else "")
                ext_hint = f" ({ext_csv})" if ext_csv else ""
                tk.Label(row, text=txt_label + ext_hint, bg=_C, fg="#ffffff",
                         font=("Segoe UI", 9, "bold"), width=28, anchor="w").pack(side="left")

                var_status_campo = tk.StringVar(value="pendente")
                lbl_status_campo = tk.Label(row, textvariable=var_status_campo, bg=_C, fg=_PEND,
                                            font=("Segoe UI", 9), width=24, anchor="w")
                lbl_status_campo.pack(side="left", padx=(8, 8))

                pbar = ttk.Progressbar(row, mode="determinate", length=140, maximum=100)

                btn_sel = ttk.Button(row, text="Selecionar arquivo")
                btn_sel.pack(side="right")

                btn_pasta = ttk.Button(row, text="📁 Pasta", width=10)
                btn_pasta.pack(side="right", padx=(0, 6))

                btn_cancelar = ttk.Button(row, text="Cancelar", style="Perigo.TButton")

                estado_campos[label]["label_status"] = lbl_status_campo
                estado_campos[label]["var_status"] = var_status_campo
                estado_campos[label]["pbar"] = pbar
                estado_campos[label]["botao"] = btn_sel
                estado_campos[label]["botao_pasta"] = btn_pasta
                estado_campos[label]["botao_cancelar"] = btn_cancelar

                def _fazer_handler(label_local: str, ext_local: str,
                                    pbar_local: ttk.Progressbar, btn_arq: ttk.Button,
                                    btn_pasta_local: ttk.Button,
                                    btn_cancel_local: ttk.Button,
                                    eh_pasta: bool) -> Callable[[], None]:
                    def _handler() -> None:
                        self._iniciar_upload_mega(
                            janela=janela,
                            api=api,
                            obter_uploader=_obter_uploader,
                            pasta_logica=pasta_logica,
                            pasta_raiz_mega=pasta_raiz_holder["valor"],
                            nome_campo=label_local,
                            extensoes_csv=ext_local,
                            estado_entry=estado_campos[label_local],
                            pbar=pbar_local,
                            botao=(btn_pasta_local if eh_pasta else btn_arq),
                            botao_outro=(btn_arq if eh_pasta else btn_pasta_local),
                            botao_cancelar=btn_cancel_local,
                            atualizar_botao_salvar=_atualizar_botao_salvar,
                            atualizar_lock_pasta=_atualizar_lock_pasta,
                            criar_sub_aberta=_criar_sub_aberta_se_necessario,
                            filedialog=_filedialog,
                            cores=(_OK, _ERRO, _PEND),
                            eh_pasta=eh_pasta,
                        )
                    return _handler

                btn_sel.configure(command=_fazer_handler(
                    label, ext_csv, pbar, btn_sel, btn_pasta, btn_cancelar, eh_pasta=False
                ))
                btn_pasta.configure(command=_fazer_handler(
                    label, ext_csv, pbar, btn_sel, btn_pasta, btn_cancelar, eh_pasta=True
                ))

        _construir_widgets_campos(campos_exigidos)

        # ====================================================
        # Seção 3: Canal + Data + Observação + Tempo
        # ====================================================
        tk.Frame(inner, bg="#222", height=1).pack(fill="x", pady=(12, 8))

        # Edição: prioriza titulo_atividade (canal real da sub via JOIN no
        # backend) sobre canal_entrega (texto livre, pode estar desatualizado).
        if subtarefa is not None:
            canal_inicial = (
                str(getattr(subtarefa, "titulo_atividade", "") or "")
                or str(getattr(subtarefa, "canal_entrega", "") or "")
                or self._titulo_atividade
            )
        else:
            canal_inicial = self._titulo_atividade
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

        # Trocar canal: refetch da config (pasta raiz + pastas lógicas), reset
        # da pasta lógica e dos estados de upload. Os widgets de campos
        # exigidos NÃO são reconstruídos — limitação aceita: se o conjunto
        # de campos do novo canal for diferente, o usuário deve fechar e
        # reabrir a janela pelo menu principal.
        canal_anterior = {"valor": canal_inicial}

        def _ao_trocar_canal(*_a: object) -> None:
            novo_canal = (var_canal.get() or "").strip()
            if not novo_canal or novo_canal == canal_anterior["valor"]:
                return

            novo_id = int(self._mapa_canal_para_id.get(novo_canal) or 0)
            if novo_id <= 0 or novo_id == id_atividade_efetiva["id"]:
                canal_anterior["valor"] = novo_canal
                return

            tem_pasta = bool(pasta_logica.get("id_pasta_logica"))
            tem_upload = any(
                st.get("state") in ("enviando", "concluido")
                for st in estado_campos.values()
            )
            if tem_pasta or tem_upload:
                ok = messagebox.askyesno(
                    "Trocar canal",
                    "Trocar de canal vai descartar a pasta lógica e cancelar "
                    "uploads em andamento. Deseja continuar?",
                    parent=janela,
                )
                if not ok:
                    var_canal.set(canal_anterior["valor"])
                    return
                for st in estado_campos.values():
                    ce = st.get("cancel_event")
                    if ce is not None:
                        try:
                            ce.set()
                        except Exception:
                            pass

            var_status_pasta.set("Carregando configurações do canal…")
            lbl_status_pasta.configure(fg=_PEND)

            def _fetch() -> dict:
                return api.obter_config_canal(novo_id)

            def _ok_fetch(cfg: object) -> None:
                d = cfg if isinstance(cfg, dict) else {}
                if not d.get("upload_ativo"):
                    messagebox.showwarning(
                        "Canal sem upload obrigatório",
                        "Este canal não tem upload obrigatório configurado. "
                        "Feche esta janela e selecione o canal correto pelo menu principal.",
                        parent=janela,
                    )
                    var_canal.set(canal_anterior["valor"])
                    var_status_pasta.set("")
                    return

                id_atividade_efetiva["id"] = novo_id
                pasta_raiz_holder["valor"] = str(d.get("pasta_raiz_mega") or "").strip()
                var_pasta_raiz.set(f"Pasta raiz no MEGA: /{pasta_raiz_holder['valor']}")
                pastas_existentes.clear()
                pastas_existentes.extend(d.get("pastas_logicas") or [])
                cmb_pasta["values"] = [
                    str(p.get("nome_pasta") or "") for p in pastas_existentes
                ]
                pasta_logica["id_pasta_logica"] = 0
                pasta_logica["nome_pasta"] = ""
                var_pasta_existente.set("")
                var_numero.set(_calcular_proximo_numero())
                modo_pasta.set("criar")
                rad_criar.configure(state="normal")
                # Reconstrói widgets dos campos com a lista do novo canal —
                # descarta widgets/estado antigos e recria a partir do que o
                # novo canal exige (Opção B: comportamento "verdadeiro" pra
                # quando os campos por canal são diferentes).
                _construir_widgets_campos(list(d.get("campos_exigidos") or []))
                var_status_pasta.set("")
                canal_anterior["valor"] = novo_canal
                _atualizar_lock_pasta()
                _atualizar_botao_salvar()

            def _falha_fetch(e: Exception) -> None:
                messagebox.showerror(
                    "Erro ao trocar canal",
                    f"Falha ao carregar configurações do canal:\n{e}",
                    parent=janela,
                )
                var_canal.set(canal_anterior["valor"])
                var_status_pasta.set("")

            self._executar_em_background(_fetch, _ok_fetch, _falha_fetch)

        var_canal.trace_add("write", _ao_trocar_canal)

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

        def _ao_fechar_janela() -> None:
            # Tarefa 1 (Opção A): se há upload em andamento, perguntar antes
            # de fechar. Se confirmar, cancela o upload e segue. A subtarefa
            # já foi auto-criada como Aberta no início do primeiro upload
            # (v2.9.3), então o trabalho NÃO é perdido — o user pode
            # voltar nela depois pra concluir.
            uploads_em_andamento = [
                (nome, st) for nome, st in estado_campos.items()
                if st.get("state") == "enviando" and st.get("cancel_event") is not None
            ]
            if uploads_em_andamento:
                resp = messagebox.askyesno(
                    "Upload em andamento",
                    "Há upload em andamento.\n\n"
                    "Se sair agora, o upload atual será cancelado, mas a tarefa "
                    "ficará salva como ABERTA — você pode voltar depois pra "
                    "continuar de onde parou.\n\nSair mesmo?",
                    parent=janela,
                )
                if not resp:
                    return
                # Sinaliza cancel pra cada upload em andamento.
                for _nome, st in uploads_em_andamento:
                    try:
                        ev = st.get("cancel_event")
                        if ev is not None and not ev.is_set():
                            ev.set()
                    except Exception:
                        pass

            # Cleanup: se em modo "nova", o user criou uma pasta lógica e
            # NÃO houve nenhum upload concluído nem sub criada, marca a
            # pasta como inativa. Evita pasta órfã queimando número.
            try:
                sub_foi_criada = self._id_subtarefa_criada_nesta_janela is not None
                tem_upload_concluido = any(
                    st.get("state") == "concluido" for st in estado_campos.values()
                )
                if (
                    subtarefa is None
                    and pasta_logica.get("id_pasta_logica")
                    and not sub_foi_criada
                    and not tem_upload_concluido
                ):
                    try:
                        api.marcar_pasta_logica_inativa(
                            int(pasta_logica["id_pasta_logica"])
                        )
                    except Exception:
                        pass
            finally:
                try:
                    janela.destroy()
                except Exception:
                    pass

        janela.protocol("WM_DELETE_WINDOW", _ao_fechar_janela)
        btn_cancelar = ttk.Button(rodape, text="Cancelar", command=_ao_fechar_janela)
        btn_cancelar.pack(side="right")
        btn_salvar = ttk.Button(rodape, textvariable=var_texto_botao, style="Primario.TButton")
        btn_salvar.pack(side="right", padx=(0, 8))

        def _atualizar_botao_salvar(*_a: object) -> None:
            tempo = (var_tempo.get() or "").strip()
            obrig_pendente: list[str] = []
            for nome, st in estado_campos.items():
                if st["obrigatorio"] and st["state"] != "concluido":
                    obrig_pendente.append(nome)

            # Canal com MEGA ativo SEM campos configurados pra esse usuário
            # = erro de configuração administrativa. Regra: se MEGA tá ativo,
            # tem que subir algo. Bloqueia até admin cadastrar campos.
            if not estado_campos:
                var_aviso_bloqueio.set(
                    "O admin não configurou arquivos pra você neste canal. "
                    "Peça pra cadastrar os campos de upload no painel antes de declarar."
                )
                btn_salvar.configure(state="disabled")
                var_texto_botao.set("Salvar e Concluir" if (tempo and not subtarefa_concluida) else "Salvar")
                return
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

            # Regra de negócio: se subiu pelo menos 1 arquivo, exige tempo > 0
            # pra concluir a tarefa. Tempo=0 só é permitido quando NÃO subiu
            # nenhum arquivo (sub fica como Aberta só com pasta).
            tem_upload_concluido = any(
                st.get("state") == "concluido" for st in estado_campos.values()
            )
            if tem_upload_concluido and not tempo and not subtarefa_concluida:
                var_aviso_bloqueio.set(
                    "Você subiu arquivo(s). Preencha o tempo gasto pra concluir a tarefa."
                )
                btn_salvar.configure(state="disabled")
                var_texto_botao.set("Salvar e Concluir")
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
            # Usa id_atividade efetiva (pode ter sido trocada via combobox de
            # canal — ver tarefa 7.4). NÃO usar self._id_atividade direto:
            # esse continua sendo o canal de origem da janela, mas o trabalho
            # real (pasta lógica + uploads) já foi pro canal selecionado.
            id_atividade = id_atividade_efetiva["id"]
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
                    sub_ja_criada = self._id_subtarefa_criada_nesta_janela is not None
                    if not sub_ja_criada:
                        self._id_subtarefa_criada_nesta_janela = self._repositorio.criar_subtarefa(
                            user_id=uid,
                            referencia_data=referencia_data,
                            id_atividade=id_atividade,
                            titulo=titulo,
                            canal_entrega=canal,
                            observacao=observacao,
                        )
                    novo_id = self._id_subtarefa_criada_nesta_janela
                    # Se a sub foi criada antes (pelo upload, modelo "Aberta
                    # automática"), atualiza os campos com o que está no
                    # form agora — o user pode ter editado observação/canal/
                    # data depois do upload.
                    if sub_ja_criada and novo_id:
                        try:
                            self._repositorio.atualizar_subtarefa(
                                user_id=uid, id_subtarefa=int(novo_id),
                                titulo=titulo, canal_entrega=canal,
                                observacao=observacao,
                                referencia_data=referencia_data,
                            )
                        except Exception:
                            pass  # se falhar atualização, segue pra concluir
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

        # Edição: hidrata estado dos campos com uploads concluídos da subtarefa
        # (em background). Sem isso, "Trocar arquivo" não saberia o caminho do
        # anterior pra apagar — e o status visual do form abriria todo "pendente"
        # mesmo com upload já feito.
        if subtarefa is not None and pasta_logica.get("id_pasta_logica") and estado_campos:
            id_sub_edit = int(getattr(subtarefa, "id_subtarefa", 0) or 0)
            if id_sub_edit > 0:
                def _fetch_uploads_existentes() -> dict:
                    return api.obter_dados_subtarefa(id_sub_edit)

                def _ok_uploads(d: object) -> None:
                    dd = d if isinstance(d, dict) else {}
                    arquivos = dd.get("arquivos") or []
                    raiz = str(dd.get("pasta_raiz_mega") or pasta_raiz_holder["valor"]).strip("/")
                    nome_pasta = str(pasta_logica.get("nome_pasta") or "")
                    for arq in arquivos:
                        if arq.get("status_upload") != "concluido":
                            continue
                        nome_campo = str(arq.get("nome_campo") or "")
                        nome_arq = str(arq.get("nome_arquivo") or "")
                        if not nome_campo or nome_campo not in estado_campos or not nome_arq:
                            continue
                        st = estado_campos[nome_campo]
                        st["state"] = "concluido"
                        st["id_upload"] = int(arq.get("id_upload") or 0)
                        st["arquivo_local"] = nome_arq
                        st["arquivo_remoto_anterior"] = f"/{raiz}/{nome_pasta}/{nome_arq}"
                        try:
                            st["var_status"].set("✓ enviado")
                            st["label_status"].configure(fg=_OK)
                            st["botao"].configure(text="Trocar arquivo")
                        except Exception:
                            pass
                    _atualizar_lock_pasta()
                    _atualizar_botao_salvar()

                def _falha_uploads(_e: Exception) -> None:
                    # Sem hidratação — usuário precisa reenviar pra ter "✓ enviado".
                    # Best effort: silencioso (sem mensagem; vai aparecer "pendente").
                    pass

                self._executar_em_background(
                    _fetch_uploads_existentes, _ok_uploads, _falha_uploads
                )

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
        botao_outro: ttk.Button | None = None,
        botao_cancelar: ttk.Button,
        atualizar_botao_salvar: Callable[[], None],
        atualizar_lock_pasta: Callable[[], None] | None = None,
        criar_sub_aberta: Callable[[], int] | None = None,
        filedialog: object,
        cores: tuple[str, str, str],
        eh_pasta: bool = False,
    ) -> None:
        """Pipeline de upload de UM arquivo OU pasta (recursivo):
        1. Filedialog → caminho local (filtrado por extensões).
        2. Pasta lógica precisa estar definida.
        3. POST `desktop_registrar_upload.php` (status=enviando) → id_upload.
        4. `MegaUploader.upload_arquivo()` em background.
        5. POST `desktop_registrar_upload.php` (status=concluido|erro).
        6. Atualiza UI (cor do label, progressbar, botão).

        Quando `eh_pasta=True`, usa `askdirectory`; valida extensões em todos
        os arquivos da pasta; e `mega-put -c <dir>` lida nativamente com
        upload recursivo.
        """
        import threading

        from app.mega_uploader import (
            ErroCredencialFaltando,
            ErroMega,
            ErroPastaMegaInexistente,
            ErroUploadCancelado,
        )
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

        from pathlib import Path as _Path

        if eh_pasta:
            caminho = filedialog.askdirectory(
                parent=janela, title=f"Selecionar pasta — {nome_campo}"
            )
            if not caminho:
                return
            dir_local = _Path(caminho)
            if not dir_local.is_dir():
                messagebox.showwarning("Atenção", "Caminho selecionado não é uma pasta.", parent=janela)
                return

            # Valida extensões em todos os arquivos da pasta (recursivo).
            permitidas: list[str] = []
            if extensoes_csv:
                permitidas = [e.strip().lower().lstrip(".") for e in extensoes_csv.split(",") if e.strip()]

            arquivos_invalidos: list[str] = []
            tamanho_total = 0
            count = 0
            for f in dir_local.rglob("*"):
                if not f.is_file():
                    continue
                count += 1
                try:
                    tamanho_total += f.stat().st_size
                except OSError:
                    pass
                if permitidas:
                    ext = f.suffix.lower().lstrip(".")
                    if ext not in permitidas:
                        arquivos_invalidos.append(f.name)

            if count == 0:
                messagebox.showwarning("Atenção", "A pasta selecionada está vazia.", parent=janela)
                return

            if arquivos_invalidos:
                amostra = ", ".join(arquivos_invalidos[:5])
                resto = f" (e mais {len(arquivos_invalidos) - 5})" if len(arquivos_invalidos) > 5 else ""
                messagebox.showwarning(
                    "Extensão não permitida",
                    f"Os seguintes arquivos têm extensão fora das permitidas ({extensoes_csv}):\n\n"
                    f"{amostra}{resto}\n\nRemova-os ou ajuste e tente de novo.",
                    parent=janela,
                )
                return

            arquivo = dir_local
            tamanho = tamanho_total or None
            # Sufixo "/" em nome_arquivo distingue pasta vs arquivo no banco.
            nome_arq = f"{dir_local.name}/"
        else:
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

            arquivo = _Path(caminho)
            tamanho = arquivo.stat().st_size if arquivo.exists() else None
            nome_arq = arquivo.name

        cancel_event = threading.Event()
        estado_entry["arquivo_local"] = str(arquivo)
        estado_entry["state"] = "enviando"
        estado_entry["cancel_event"] = cancel_event
        estado_entry["eh_pasta"] = eh_pasta
        rotulo_envio = "pasta" if eh_pasta else ""
        var_status.set(f"enviando {rotulo_envio} 0%…".replace("  ", " ").strip())
        lbl_status.configure(fg=cor_pend)
        pbar.configure(value=0)
        pbar.pack(side="left", padx=(0, 8))
        botao.configure(state="disabled")
        if botao_outro is not None:
            botao_outro.configure(state="disabled")
        if atualizar_lock_pasta is not None:
            atualizar_lock_pasta()

        # Botão "Cancelar" entra no lugar visual durante o upload.
        def _cancelar() -> None:
            if not cancel_event.is_set():
                cancel_event.set()
                var_status.set("cancelando…")
                botao_cancelar.configure(state="disabled")
        botao_cancelar.configure(command=_cancelar, state="normal")
        botao_cancelar.pack(side="right", padx=(6, 0))
        atualizar_botao_salvar()

        # Callback de progresso vem da thread daemon do `_executar_mega_put_streaming`.
        # Marshalling pra UI thread via `self.after(0, ...)`.
        def _on_progress(pct: float) -> None:
            def _aplicar(p: float = pct) -> None:
                try:
                    if not janela.winfo_exists():
                        return
                except Exception:
                    return
                pbar.configure(value=p)
                # Mantém prefixo "cancelando…" se já clicou
                if not cancel_event.is_set():
                    pref = "enviando pasta " if eh_pasta else "enviando "
                    var_status.set(f"{pref}{p:.0f}%…")
            try:
                self.after(0, _aplicar)
            except Exception:
                pass

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

            uploader = obter_uploader()

            # Defesa contra sincronia rompida (admin apagou a pasta no app
            # web do MEGA): valida existência antes de qualquer ação. Se
            # sumiu, marca pasta lógica como inativa no banco e levanta
            # `ErroPastaMegaInexistente` — UX explica que o usuário precisa
            # recriar a pasta.
            if pasta_logica.get("id_pasta_logica"):
                pasta_remota_check = pasta_remota.rstrip("/")
                try:
                    pasta_ok = uploader.pasta_existe(pasta_remota_check)  # type: ignore[attr-defined]
                except Exception:
                    # Falha de rede/sessão — segue (mega-put -c recria se faltar).
                    pasta_ok = True
                if not pasta_ok:
                    try:
                        api_local.marcar_pasta_logica_inativa(  # type: ignore[attr-defined]
                            int(pasta_logica["id_pasta_logica"])
                        )
                    except Exception:
                        pass
                    raise ErroPastaMegaInexistente(
                        f"a pasta '{pasta_logica['nome_pasta']}' foi removida no MEGA — "
                        "feche este formulário e crie a pasta lógica de novo"
                    )

            # Dedup do upload anterior (best effort).
            #
            # Pra PASTA, SEMPRE limpa o destino antes do upload novo —
            # mesmo que o caminho remoto seja idêntico ao anterior. Razão:
            # `mega-put -c <dir>` mescla conteúdos com pasta remota
            # existente. Sem essa limpeza prévia, arquivos que saíram da
            # pasta local entre uploads ficam órfãos no MEGA.
            #
            # Pra ARQUIVO, `mega-put -c` sobrescreve naturalmente, então só
            # precisa apagar o anterior se o caminho mudou (renomeou ou
            # selecionou outro arquivo no mesmo campo).
            anterior = str(estado_entry.get("arquivo_remoto_anterior") or "").strip()
            novo_path = f"{pasta_remota}{nome_arq}"

            if eh_pasta:
                try:
                    uploader.remover_pasta_recursiva(novo_path)  # type: ignore[attr-defined]
                except Exception:
                    pass

            if anterior and anterior != novo_path:
                try:
                    if anterior.endswith("/"):
                        uploader.remover_pasta_recursiva(anterior)  # type: ignore[attr-defined]
                    else:
                        uploader.remover_arquivo(anterior)  # type: ignore[attr-defined]
                except Exception:
                    pass

            # Etapa 2: upload real (com progresso e cancelamento)
            uploader.upload_arquivo(  # type: ignore[attr-defined]
                arquivo,
                pasta_remota,
                on_progress=_on_progress,
                cancel_event=cancel_event,
            )

            # Grava o caminho remoto novo pra próximo "trocar arquivo" saber
            # qual remover.
            estado_entry["arquivo_remoto_anterior"] = f"{pasta_remota}{nome_arq}"

            # Cria sub Aberta no banco no PRIMEIRO upload concluído desta
            # janela (se modo "nova"). Subs em modo edição já existem.
            id_sub_para_vincular = 0
            if criar_sub_aberta is not None:
                try:
                    id_sub_para_vincular = int(criar_sub_aberta() or 0)
                except Exception:
                    id_sub_para_vincular = 0

            # Etapa 3: marca como concluido + vincula a id_subtarefa.
            if estado_entry["id_upload"]:
                api_local.registrar_upload(  # type: ignore[attr-defined]
                    id_upload=int(estado_entry["id_upload"]),
                    id_pasta_logica=int(pasta_logica["id_pasta_logica"]),
                    nome_campo=nome_campo,
                    nome_arquivo=nome_arq,
                    status_upload="concluido",
                    tamanho_bytes=tamanho,
                    id_subtarefa=id_sub_para_vincular if id_sub_para_vincular > 0 else None,
                )
            return True

        def _esconder_cancelar() -> None:
            try:
                botao_cancelar.pack_forget()
            except Exception:
                pass

        def _ok(_: object) -> None:
            pbar.configure(value=100)
            pbar.pack_forget()
            _esconder_cancelar()
            estado_entry["state"] = "concluido"
            estado_entry["cancel_event"] = None
            var_status.set("✓ pasta enviada" if eh_pasta else "✓ enviado")
            lbl_status.configure(fg=cor_ok)
            botao.configure(state="normal", text="Trocar pasta" if eh_pasta else "Trocar arquivo")
            if botao_outro is not None:
                botao_outro.configure(state="normal")
            if atualizar_lock_pasta is not None:
                atualizar_lock_pasta()
            atualizar_botao_salvar()

        def _falha(erro: Exception) -> None:
            pbar.pack_forget()
            _esconder_cancelar()
            estado_entry["cancel_event"] = None

            texto_padrao = "📁 Pasta" if eh_pasta else "Selecionar arquivo"
            if isinstance(erro, ErroUploadCancelado):
                estado_entry["state"] = "pendente"
                var_status.set("cancelado")
                lbl_status.configure(fg=cor_pend)
                botao.configure(state="normal", text=texto_padrao)
                status_painel = "erro"
                msg_painel = "cancelado pelo usuário"
            else:
                estado_entry["state"] = "erro"
                msg_curta = str(erro)[:60]
                var_status.set(f"✗ {msg_curta}")
                lbl_status.configure(fg=cor_erro)
                botao.configure(state="normal", text="Tentar de novo")
                status_painel = "erro"
                msg_painel = str(erro)[:500]
            if botao_outro is not None:
                botao_outro.configure(state="normal")
            if atualizar_lock_pasta is not None:
                atualizar_lock_pasta()
            atualizar_botao_salvar()

            id_up = int(estado_entry.get("id_upload") or 0)
            if id_up:
                try:
                    api.registrar_upload(  # type: ignore[attr-defined]
                        id_upload=id_up,
                        id_pasta_logica=int(pasta_logica["id_pasta_logica"]),
                        nome_campo=nome_campo,
                        nome_arquivo=nome_arq,
                        status_upload=status_painel,
                        mensagem_erro=msg_painel,
                    )
                except Exception:
                    pass

            if isinstance(erro, ErroCredencialFaltando):
                messagebox.showerror(
                    "MEGA",
                    "Credenciais MEGA (mega_email / mega_password) não configuradas no painel. "
                    "Peça ao admin pra cadastrar na aba Credenciais (modo global).",
                    parent=janela,
                )
            elif isinstance(erro, ErroPastaMegaInexistente):
                messagebox.showwarning(
                    "Pasta MEGA não encontrada",
                    str(erro),
                    parent=janela,
                )
            elif isinstance(erro, ErroUploadCancelado):
                pass  # já mostrou status na UI; sem messagebox
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
