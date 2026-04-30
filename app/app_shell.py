"""Shell Tkinter principal: classe App.

Conecta UI, MonitorDeUso, JanelaSubtarefas e auto-update.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
import urllib.request
from pathlib import Path
from tkinter import messagebox, ttk

from atividades import RepositorioAtividades
from banco import BancoDados
from declaracoes_dia import RepositorioDeclaracoesDia

from app.config import (
    ARQUIVO_LOGIN_SALVO,
    ARQUIVO_REGRESSIVA,
    ARQUIVO_LOG_TECNICO,
    HISTORICO_VERSOES,
    INTERVALO_UI_MILISSEGUNDOS,
    INTERVALO_VERIFICAR_UPDATE_MS,
    LIMITE_HORAS_AVISO,
    LIMITE_HORAS_MAXIMO,
    LOG_TEC,
    MODO_SCRIPT,
    URL_ATUALIZACAO,
    VERSAO_APLICACAO,
)
from app.monitor import MonitorDeUso
from app.subtarefas import JanelaSubtarefas
from app.win32_utils import formatar_hhmmss


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title(f"Cronômetro {VERSAO_APLICACAO}")
        self.resizable(False, False)
        self._aplicar_icone()

        self._banco = BancoDados()
        self._repositorio = RepositorioAtividades(self._banco)
        self._repositorio_declaracoes = RepositorioDeclaracoesDia(self._banco)
        self._monitor = MonitorDeUso(self._banco)

        self._usuario: dict[str, str] | None = None
        self._mapa_item_para_id: dict[str, int] = {}

        self._var_user = tk.StringVar(value="")
        self._var_chave = tk.StringVar(value="")
        self._var_atividade = tk.StringVar(value="")
        self._var_status = tk.StringVar(value="Faça login.")
        self._var_tempo = tk.StringVar(value="00:00:00")
        self._var_erro = tk.StringVar(value="")

        self._janela_fixada: tk.Toplevel | None = None
        self._var_tempo_fixado = tk.StringVar(value="00:00:00")
        self._var_status_fixado = tk.StringVar(value="")

        # Contagem regressiva visual — roda por cima do cronômetro progressivo sem alterar dados reais.
        # Progresso medido em segundos_trabalhando (conta só trabalho líquido, não decrementa em pausa/ocioso).
        self._regressiva_alvo_seg: int = 0
        self._regressiva_trab_inicio: int = 0
        self._regressiva_ativa: bool = False
        self._regressiva_modal_mostrado: bool = False
        self._regressiva_dialogo: tk.Toplevel | None = None
        self._var_tempo_regressiva = tk.StringVar(value="00:00:00")
        self._var_tempo_regressiva_fixado = tk.StringVar(value="00:00:00")
        self._regressiva_carregar_do_disco()

        # T25: modal de aviso de update evita empilhamento quando o user ignora
        self._modal_update_aberto: bool = False

        self._ultimo_segundo_renderizado = -1
        self._ultimo_status_renderizado = ""

        self._aplicar_estilo()
        self._montar_tela_login()
        dados_salvos = self._ler_login_salvo()
        if dados_salvos:
            self._var_user.set(dados_salvos["user_id"])
            self._var_chave.set(dados_salvos["chave"])
            self._logar()

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.after(INTERVALO_UI_MILISSEGUNDOS, self._tick_ui)

    def _aplicar_estilo(self) -> None:
        _BG   = "#111111"
        _BG2  = "#1a1a1a"
        _BG3  = "#222222"
        _BTN  = "#2a2a2a"
        _BTN_H = "#363636"
        _ACCENT   = "#1b6ef3"
        _ACCENT_H = "#1457cc"
        _DANGER   = "#c0392b"
        _DANGER_H = "#a93226"
        _TEXT = "#e0e0e0"
        _DIM  = "#666666"
        _BORDER = "#2e2e2e"

        try:
            self.configure(bg=_BG)
            estilo = ttk.Style(self)
            try:
                estilo.theme_use("clam")
            except Exception:
                pass

            # Frames
            estilo.configure("TFrame", background=_BG)
            estilo.configure("Card.TFrame", background=_BG2, padding=20, relief="flat")

            # Labels
            estilo.configure("TLabel",
                background=_BG, foreground=_TEXT, font=("Segoe UI", 10))
            estilo.configure("Titulo.TLabel",
                background=_BG2, foreground="#ffffff", font=("Segoe UI", 16, "bold"))
            estilo.configure("Subtitulo.TLabel",
                background=_BG2, foreground=_DIM, font=("Segoe UI", 10))
            estilo.configure("Cab.TLabel",
                background=_BG, foreground=_TEXT, font=("Segoe UI", 10, "bold"))

            # Buttons base
            estilo.configure("TButton",
                background=_BTN, foreground=_TEXT,
                font=("Segoe UI", 10), padding=10,
                borderwidth=0, relief="flat", focuscolor=_BTN,
            )
            estilo.map("TButton",
                background=[("active", _BTN_H), ("pressed", "#404040"), ("disabled", _BG3)],
                foreground=[("disabled", _DIM)],
                relief=[("pressed", "flat"), ("active", "flat")],
            )

            # Primary button — azul (Pausar / Retomar / Salvar)
            estilo.configure("Primario.TButton",
                background=_ACCENT, foreground="#ffffff",
                font=("Segoe UI", 10, "bold"), padding=12,
                borderwidth=0, relief="flat", focuscolor=_ACCENT,
            )
            estilo.map("Primario.TButton",
                background=[("active", _ACCENT_H), ("pressed", "#0f47a8"), ("disabled", "#1a3a70")],
                foreground=[("disabled", "#7090bb")],
                relief=[("pressed", "flat"), ("active", "flat")],
            )

            # Verde button — Iniciar
            _GREEN   = "#1a9c4a"
            _GREEN_H = "#157d3b"
            estilo.configure("Verde.TButton",
                background=_GREEN, foreground="#ffffff",
                font=("Segoe UI", 10, "bold"), padding=12,
                borderwidth=0, relief="flat", focuscolor=_GREEN,
            )
            estilo.map("Verde.TButton",
                background=[("active", _GREEN_H), ("pressed", "#0f6030"), ("disabled", "#0e3d20")],
                foreground=[("disabled", "#70aa80")],
                relief=[("pressed", "flat"), ("active", "flat")],
            )

            # Danger button (Excluir)
            estilo.configure("Perigo.TButton",
                background=_DANGER, foreground="#ffffff",
                font=("Segoe UI", 10), padding=10,
                borderwidth=0, relief="flat", focuscolor=_DANGER,
            )
            estilo.map("Perigo.TButton",
                background=[("active", _DANGER_H), ("pressed", "#922b21"), ("disabled", "#4a1010")],
                foreground=[("disabled", "#aa6666")],
                relief=[("pressed", "flat"), ("active", "flat")],
            )

            # Entry
            estilo.configure("TEntry",
                fieldbackground="#1a1a1a", foreground=_TEXT,
                insertcolor=_TEXT, borderwidth=1,
                bordercolor=_BORDER,
            )

            # Combobox
            estilo.configure("TCombobox",
                fieldbackground="#1a1a1a", foreground=_TEXT,
                background=_BTN, selectbackground=_ACCENT,
                arrowcolor=_TEXT,
            )
            estilo.map("TCombobox",
                fieldbackground=[("readonly", "#1a1a1a")],
                foreground=[("readonly", _TEXT)],
                selectbackground=[("readonly", "#1a1a1a")],
                selectforeground=[("readonly", _TEXT)],
            )

            # Scrollbar
            estilo.configure("TScrollbar",
                background=_BTN, troughcolor=_BG2,
                arrowcolor=_DIM, borderwidth=0,
            )

            # Treeview
            estilo.configure("Treeview",
                background=_BG2, foreground=_TEXT,
                fieldbackground=_BG2, rowheight=26, borderwidth=0,
            )
            estilo.configure("Treeview.Heading",
                background=_BG3, foreground=_TEXT,
                font=("Segoe UI", 10, "bold"), relief="flat", borderwidth=0,
            )
            estilo.map("Treeview",
                background=[("selected", _ACCENT)],
                foreground=[("selected", "#ffffff")],
            )
            estilo.map("Treeview.Heading",
                background=[("active", _BTN_H)],
                relief=[("active", "flat")],
            )

        except Exception:
            pass

    def _aplicar_icone(self) -> None:
        """Carrega logo.png como ícone da janela (requer Pillow)."""
        try:
            from PIL import Image, ImageTk  # type: ignore
            # No exe frozen (PyInstaller), datas são extraídos em sys._MEIPASS.
            # Em script normal, logo.png fica na raiz do projeto (um nível acima deste módulo).
            base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
            caminho = base / "logo.png"
            if not caminho.exists():
                return
            img = Image.open(str(caminho)).convert("RGBA")
            img = img.resize((32, 32), Image.LANCZOS)
            self._icone_app = ImageTk.PhotoImage(img)  # guarda referência — GC não pode coletar
            self.iconphoto(True, self._icone_app)
        except Exception:
            pass  # sem Pillow ou sem arquivo — ignora silenciosamente

    def _ler_login_salvo(self) -> dict | None:
        try:
            if not ARQUIVO_LOGIN_SALVO.exists():
                return None
            dados = json.loads(ARQUIVO_LOGIN_SALVO.read_text(encoding="utf-8"))
            uid = str(dados.get("user_id") or "").strip()
            chave = str(dados.get("chave") or "").strip()
            if uid and chave:
                return {"user_id": uid, "chave": chave}
        except Exception:
            pass
        return None

    def _salvar_login(self, user_id: str, chave: str) -> None:
        try:
            dados = {"user_id": (user_id or "").strip(), "chave": (chave or "").strip()}
            ARQUIVO_LOGIN_SALVO.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _montar_tela_carregando(self) -> None:
        self.geometry("480x520")
        for widget in self.winfo_children():
            widget.destroy()
        fundo = tk.Frame(self, bg="#111111")
        fundo.pack(fill="both", expand=True)
        tk.Label(fundo, text="Conectando…", bg="#111111", fg="#606060",
                 font=("Segoe UI", 12)).place(relx=0.5, rely=0.5, anchor="center")

    def _tentar_auto_login(self, user_id: str, chave: str) -> None:
        def _em_thread() -> None:
            try:
                usuario = self._repositorio.autenticar_usuario(user_id, chave)
            except Exception:
                self.after(0, lambda: self._mostrar_login_com_erro(
                    user_id, chave, "Sem conexão com o servidor."))
                return
            if not usuario:
                self.after(0, lambda: self._mostrar_login_com_erro(
                    user_id, chave, "Credenciais inválidas."))
                return
            def _na_ui() -> None:
                self._usuario = usuario
                self._verificar_atualizacao()
                self._agendar_verificacao_periodica_update()
                self._montar_tela_principal()
            self.after(0, _na_ui)
        threading.Thread(target=_em_thread, daemon=True).start()

    def _mostrar_login_com_erro(self, user_id: str, chave: str, msg: str) -> None:
        self._montar_tela_login()
        self._var_user.set(user_id)
        self._var_chave.set(chave)
        self._var_status.set(msg)

    def _montar_tela_login(self) -> None:
        self.geometry("480x520")
        self.title(f"Cronômetro {VERSAO_APLICACAO}")
        for widget in self.winfo_children():
            widget.destroy()

        _BG  = "#111111"
        _C   = "#1a1a1a"   # card bg
        _D   = "#606060"   # rótulos dim
        _A   = "#1b6ef3"   # accent azul

        # fundo da janela
        fundo = tk.Frame(self, bg=_BG)
        fundo.pack(fill="both", expand=True)

        # card centralizado
        card = tk.Frame(fundo, bg=_C)
        card.place(relx=0.5, rely=0.5, anchor="center")

        # barra de acento no topo do card
        tk.Frame(card, bg=_A, height=3, width=360).pack(fill="x")

        # conteúdo interno com padding
        inner = tk.Frame(card, bg=_C, padx=32, pady=24)
        inner.pack(fill="both")

        # cabeçalho
        tk.Label(inner, text="Cronômetro", bg=_C, fg="#ffffff",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(inner, text="Faça login para continuar", bg=_C, fg=_D,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(2, 20))

        # User ID
        tk.Label(inner, text="USER ID", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        entrada_user = ttk.Entry(inner, textvariable=self._var_user, width=34)
        entrada_user.pack(fill="x", pady=(3, 14))

        # Chave
        tk.Label(inner, text="CHAVE", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        entrada_chave = ttk.Entry(inner, textvariable=self._var_chave, width=34, show="•")
        entrada_chave.pack(fill="x", pady=(3, 18))

        # Botão Entrar
        ttk.Button(inner, text="Entrar", style="Verde.TButton",
                   command=self._logar).pack(fill="x")

        # Status — cor muda conforme conteúdo
        lbl_status = tk.Label(inner, textvariable=self._var_status, bg=_C, fg=_D,
                              font=("Segoe UI", 9))
        lbl_status.pack(anchor="w", pady=(10, 0))

        def _atualizar_cor_status(*_: object) -> None:
            try:
                if not lbl_status.winfo_exists():
                    return
            except Exception:
                return
            txt = self._var_status.get().lower()
            if any(p in txt for p in ("inválido", "erro", "falha", "sem conexão")):
                lbl_status.configure(fg="#ff5555")
            elif any(p in txt for p in ("ok", "verificando", "carregando", "baixando")):
                lbl_status.configure(fg="#3ecf6e")
            else:
                lbl_status.configure(fg=_D)

        self._var_status.trace_add("write", _atualizar_cor_status)

        # Botão notas de atualização
        btn_notas = tk.Label(fundo, text=f"{VERSAO_APLICACAO} — ver novidades",
                             bg=_BG, fg="#555555", font=("Segoe UI", 8),
                             cursor="hand2")
        btn_notas.place(relx=0.5, rely=1.0, anchor="s", y=-8)
        btn_notas.bind("<Button-1>", lambda _: self._abrir_changelog())

        entrada_user.focus_set()
        self.bind("<Return>", lambda _e: self._logar())

    def _abrir_changelog(self) -> None:
        janela = tk.Toplevel(self)
        janela.title(f"Novidades — Cronômetro {VERSAO_APLICACAO}")
        janela.geometry("420x400")
        janela.resizable(False, True)
        janela.transient(self)
        janela.grab_set()
        janela.configure(bg="#111111")

        # Área scrollável
        canvas = tk.Canvas(janela, bg="#111111", highlightthickness=0)
        scrollbar = ttk.Scrollbar(janela, orient="vertical", command=canvas.yview)
        frame = tk.Frame(canvas, bg="#111111")

        frame.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw", width=400)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)
        scrollbar.pack(side="right", fill="y")

        for entrada in HISTORICO_VERSOES:
            # Cabeçalho da versão
            tk.Label(frame, text=f"{entrada['versao']}  —  {entrada['data']}",
                     bg="#111111", fg="#3ecf6e", font=("Segoe UI", 11, "bold"),
                     anchor="w").pack(fill="x", pady=(12, 4))

            # Itens
            for nota in entrada["notas"]:
                tk.Label(frame, text=f"  •  {nota}", bg="#111111", fg="#bbbbbb",
                         font=("Segoe UI", 9), anchor="w", wraplength=370,
                         justify="left").pack(fill="x", pady=1)

            # Separador
            tk.Frame(frame, bg="#333333", height=1).pack(fill="x", pady=(10, 0))

        # Botão fechar
        ttk.Button(janela, text="Fechar", command=janela.destroy).pack(pady=(8, 10))

    def _montar_tela_principal(self) -> None:
        self.geometry("560x300")
        for widget in self.winfo_children():
            widget.destroy()

        quadro = ttk.Frame(self, padding=14)
        quadro.pack(fill="both", expand=True)

        topo = ttk.Frame(quadro)
        topo.pack(fill="x")

        nome = self._usuario["nome_exibicao"] if self._usuario else ""
        # Nome do usuário migrou para o título da janela (ao lado da versão)
        self.title(f"Cronômetro {VERSAO_APLICACAO} — {nome}" if nome else f"Cronômetro {VERSAO_APLICACAO}")

        # Botões centralizados no topo. Log só em modo script (.py) — não aparece no .exe.
        botoes_topo = ttk.Frame(topo)
        botoes_topo.pack(anchor="center")
        ttk.Button(botoes_topo, text="Fixar", command=self._alternar_fixar).pack(side="left", padx=4)
        ttk.Button(botoes_topo, text="⏱ Regressiva", command=self._abrir_modal_regressiva).pack(side="left", padx=4)
        ttk.Button(botoes_topo, text="Sair", command=self._sair).pack(side="left", padx=4)
        if MODO_SCRIPT:
            ttk.Button(botoes_topo, text="🐞 Log", command=self._abrir_janela_log).pack(side="left", padx=4)

        # combo oculto — mantém a lógica de seleção de atividade sem exibir na tela
        self._combo = ttk.Combobox(self, textvariable=self._var_atividade, state="readonly", width=58, values=[])

        painel = ttk.Frame(quadro)
        painel.pack(fill="both", expand=True, pady=(14, 0))

        # Dois labels — só um visível por vez (controlado por _aplicar_modo_regressiva).
        # Quando regressiva ativa: lbl_regressiva grande (foco) + lbl_tempo pequeno (progressivo abaixo).
        # Quando inativa: só lbl_tempo grande (comportamento original).
        self._lbl_regressiva_principal = ttk.Label(
            painel, textvariable=self._var_tempo_regressiva,
            font=("Segoe UI", 44, "bold"), foreground="#ff6b1f",
        )
        self._lbl_tempo_principal = ttk.Label(
            painel, textvariable=self._var_tempo,
            font=("Segoe UI", 44, "bold"), foreground="#ffffff",
        )
        self._aplicar_modo_regressiva()
        # Label de status (TRABALHANDO / OCIOSO / ...) — cor trocada dinamicamente em _tick_ui
        # conforme conectividade (verde online / amarelo offline).
        self._lbl_status_principal = ttk.Label(
            painel, textvariable=self._var_status,
            font=("Segoe UI", 10, "bold"), foreground="#aaaaaa",
        )
        self._lbl_status_principal.pack(anchor="center", pady=(6, 0))
        # Label de mensagens: erro persistente (laranja) ou sucesso transitório (verde)
        self._lbl_erro_principal = ttk.Label(
            painel, textvariable=self._var_erro, foreground="#f0a500",
            font=("Segoe UI", 8), wraplength=380, justify="center",
        )
        self._lbl_erro_principal.pack(anchor="center", pady=(2, 0))

        self._var_texto_btn_principal = tk.StringVar(value="Iniciar")

        botoes = ttk.Frame(quadro)
        botoes.pack(fill="x", pady=(16, 0))

        self._btn_principal = ttk.Button(botoes, textvariable=self._var_texto_btn_principal, style="Verde.TButton", command=self._acao_principal)
        self._btn_principal.pack(side="left", expand=True, fill="x", padx=4)
        self._btn_tarefas = ttk.Button(botoes, text="Tarefas", command=self._abrir_tarefas_do_dia)
        self._btn_tarefas.pack(side="left", expand=True, fill="x", padx=4)
        ttk.Button(botoes, text="Zerar Cronômetro", command=self._finalizar).pack(side="left", expand=True, fill="x", padx=4)

        self._carregar_atividades()

        if self._usuario:
            dados = self._monitor.obter_dados_sessao_pendente_do_usuario(self._usuario["user_id"])
            if dados:
                id_atividade_pendente = int(dados.get("id_atividade") or 0)
                self._definir_combo_por_id_atividade(id_atividade_pendente)

                try:
                    self._monitor.restaurar_sessao(dados, self._usuario["nome_exibicao"])
                    self._var_status.set("SESSÃO RESTAURADA (PAUSADA)")
                except Exception as erro:
                    self._var_status.set(f"Falha ao restaurar sessão: {erro}")

    def _verificar_atualizacao(self) -> None:
        """Verifica atualização em background — só roda quando executado como .exe (PyInstaller)."""

        # Pula auto-update quando rodando pelo .py (modo desenvolvimento)
        if not getattr(sys, "frozen", False):
            return

        def _em_thread() -> None:
            try:
                caminho_atual = Path(sys.executable).resolve()
                tamanho_local = caminho_atual.stat().st_size

                req = urllib.request.Request(URL_ATUALIZACAO, method="HEAD")
                req.add_header("User-Agent", "CronometroLeve-Updater/1.0")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    tamanho_remoto = int(resp.headers.get("Content-Length", 0))

                if tamanho_remoto <= 0 or tamanho_remoto == tamanho_local:
                    return  # sem atualização

                self.after(0, lambda: _mostrar_overlay())
                _baixar(caminho_atual)
            except Exception:
                pass  # falha silenciosa — atualização é opcional

        def _mostrar_overlay() -> None:
            self.protocol("WM_DELETE_WINDOW", lambda: None)
            self.resizable(False, False)
            self.geometry("320x320")

            _BG = "#111111"
            _C = "#1a1a1a"
            _A = "#1b6ef3"

            overlay = tk.Frame(self, bg=_BG)
            overlay.place(relx=0, rely=0, relwidth=1, relheight=1)

            card = tk.Frame(overlay, bg=_C)
            card.place(relx=0.5, rely=0.5, anchor="center")

            tk.Frame(card, bg=_A, height=3, width=260).pack(fill="x")

            inner = tk.Frame(card, bg=_C, padx=32, pady=32)
            inner.pack(fill="both")

            tk.Label(
                inner, text="⟳", bg=_C, fg=_A,
                font=("Segoe UI", 28),
            ).pack(pady=(0, 12))
            tk.Label(
                inner, text="Atualizando…", bg=_C, fg="#ffffff",
                font=("Segoe UI", 13, "bold"),
            ).pack()
            tk.Label(
                inner, text="O programa será reiniciado\nautomaticamente em instantes.",
                bg=_C, fg="#666666", font=("Segoe UI", 9), justify="center",
            ).pack(pady=(8, 0))

        def _baixar(caminho_atual: Path) -> None:
            pasta = caminho_atual.parent
            novo_exe = pasta / "CronometroLeve_novo.exe"
            backup_exe = pasta / "CronometroLeve.exe.bak"
            try:
                urllib.request.urlretrieve(URL_ATUALIZACAO, str(novo_exe))
                if backup_exe.exists():
                    backup_exe.unlink()
                if caminho_atual.exists():
                    os.rename(str(caminho_atual), str(backup_exe))
                try:
                    os.rename(str(novo_exe), str(caminho_atual))
                except Exception:
                    if backup_exe.exists() and not caminho_atual.exists():
                        os.rename(str(backup_exe), str(caminho_atual))
                    return
                # Zerar sessão antes de reiniciar (envia tudo ao servidor como se o
                # usuário tivesse clicado em "Zerar Cronômetro")
                try:
                    if getattr(self, "_monitor", None) is not None and getattr(self._monitor, "_id_sessao", None):
                        self._monitor.zerar_sessao()
                except Exception as e:
                    print(f"[auto-update] Falha ao zerar sessão antes do reinício: {e}")
                subprocess.Popen([str(caminho_atual)])
                self.after(0, lambda: os._exit(0))
            except Exception:
                pass

        threading.Thread(target=_em_thread, daemon=True).start()

    def _agendar_verificacao_periodica_update(self) -> None:
        """Agenda próximo ciclo de checagem de update (apenas avisa — não auto-aplica).
        T25: a cada 10 min, se houver update disponível, abre modal informativo.
        """
        try:
            self.after(INTERVALO_VERIFICAR_UPDATE_MS, self._verificar_atualizacao_periodica)
        except tk.TclError:
            pass

    def _verificar_atualizacao_periodica(self) -> None:
        """Check em background do tamanho do .exe remoto vs local.
        Se diferente, dispara modal informativo. Sempre reagenda o próximo ciclo.
        Só roda em .exe (PyInstaller). Em modo script, nem entra.
        """
        if not getattr(sys, "frozen", False):
            return

        def _em_thread() -> None:
            try:
                caminho_atual = Path(sys.executable).resolve()
                tamanho_local = caminho_atual.stat().st_size

                req = urllib.request.Request(URL_ATUALIZACAO, method="HEAD")
                req.add_header("User-Agent", "CronometroLeve-Updater/1.0")
                with urllib.request.urlopen(req, timeout=8) as resp:
                    tamanho_remoto = int(resp.headers.get("Content-Length", 0))

                if tamanho_remoto > 0 and tamanho_remoto != tamanho_local:
                    self.after(0, self._mostrar_aviso_update_disponivel)
            except Exception:
                pass
            finally:
                # Sempre reagenda — mantém o ciclo de 10 min rodando
                self.after(0, self._agendar_verificacao_periodica_update)

        threading.Thread(target=_em_thread, daemon=True).start()

    def _mostrar_aviso_update_disponivel(self) -> None:
        """Modal informativo. Não aplica a atualização — só pede reinício.
        Se o usuário só clica OK e ignora, o próximo ciclo (10 min depois) reabre
        enquanto a atualização continuar disponível.
        """
        if getattr(self, "_modal_update_aberto", False):
            return  # evita empilhar

        dlg = tk.Toplevel(self)
        self._modal_update_aberto = True
        dlg.title("Atualização disponível")
        dlg.geometry("400x170")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.transient(self)
        dlg.configure(bg="#111111")

        ttk.Label(dlg, text="⟳ Atualização disponível", font=("Segoe UI", 14, "bold")).pack(pady=(16, 6))
        ttk.Label(
            dlg,
            text="Uma nova versão do cronômetro está disponível.\nReinicie o programa para aplicar.",
            wraplength=360, justify="center",
        ).pack(padx=14)

        def _fechar() -> None:
            self._modal_update_aberto = False
            try: dlg.destroy()
            except Exception: pass

        dlg.protocol("WM_DELETE_WINDOW", _fechar)
        ttk.Button(dlg, text="OK", style="Verde.TButton", command=_fechar).pack(pady=12)
        dlg.bind("<Return>", lambda _e: _fechar())
        dlg.bind("<Escape>", lambda _e: _fechar())

    def _logar(self) -> None:
        user_id = (self._var_user.get() or "").strip()
        chave = (self._var_chave.get() or "").strip()

        if not user_id or not chave:
            self._var_status.set("Informe user_id e chave.")
            return

        self._var_status.set("Verificando…")
        self.update_idletasks()

        def _em_thread() -> None:
            try:
                usuario = self._repositorio.autenticar_usuario(user_id, chave)
            except Exception:
                self.after(0, lambda: self._var_status.set("Sem conexão com o servidor."))
                return

            if not usuario:
                self.after(0, lambda: self._var_status.set("Login inválido."))
                return

            def _na_ui() -> None:
                self._usuario = usuario
                self._salvar_login(user_id, chave)
                self._var_status.set("Login OK.")
                self.unbind("<Return>")
                self._verificar_atualizacao()
                self._agendar_verificacao_periodica_update()
                self._montar_tela_principal()

            self.after(0, _na_ui)

        threading.Thread(target=_em_thread, daemon=True).start()

    def _sair(self) -> None:
        try:
            self._monitor.pausar_e_preservar_sessao()
        except Exception:
            pass

        self._fechar_fixado()

        self._usuario = None
        self._var_status.set("Faça login.")
        self._var_tempo.set("00:00:00")
        self._var_erro.set("")
        self._ultimo_segundo_renderizado = -1
        self._ultimo_status_renderizado = ""
        self._montar_tela_login()
        dados_salvos = self._ler_login_salvo()
        if dados_salvos:
            self._var_user.set(dados_salvos["user_id"])
            self._var_chave.set(dados_salvos["chave"])

    def _carregar_atividades(self) -> None:
        if not self._usuario:
            return

        try:
            atividades = self._repositorio.listar_atividades_do_usuario(self._usuario["user_id"])
        except Exception as erro:
            messagebox.showerror("Erro", f"Falha ao carregar atividades.\n{erro}")
            return

        valores: list[str] = []
        self._mapa_item_para_id.clear()

        for linha in atividades:
            id_atividade = int(linha["id_atividade"])
            titulo = str(linha["titulo"] or "").strip()
            item = titulo  # apenas o nome do canal (sem #ID e sem status)
            valores.append(item)
            self._mapa_item_para_id[item] = id_atividade

        self._combo["values"] = valores

        if valores:
            self._var_atividade.set(valores[0])

    def _definir_combo_por_id_atividade(self, id_atividade: int) -> None:
        for item, identificador in self._mapa_item_para_id.items():
            if int(identificador) == int(id_atividade):
                self._var_atividade.set(item)
                return

    def _obter_id_atividade_selecionada(self) -> tuple[int, str]:
        item = (self._var_atividade.get() or "").strip()
        if not item or item not in self._mapa_item_para_id:
            raise RuntimeError("Selecione uma atividade.")
        id_atividade = int(self._mapa_item_para_id[item])
        titulo = item.split(" - ", 1)[1] if " - " in item else item
        return id_atividade, titulo

    def _obter_contexto_atividade_ativa(self) -> tuple[int, str]:
        if self._monitor.tem_sessao_carregada():
            with self._monitor._trava:
                id_atividade = int(self._monitor._id_atividade or 0)
                titulo = str(self._monitor._titulo_atividade or "").strip()
            if id_atividade > 0:
                self._definir_combo_por_id_atividade(id_atividade)
                return id_atividade, titulo
        return self._obter_id_atividade_selecionada()

    def _verificar_limite_horas(self) -> bool:
        """Retorna True se pode continuar. Mostra aviso se acima de 20h."""
        seg = self._monitor.obter_segundos_trabalhando()
        if seg >= LIMITE_HORAS_MAXIMO:
            messagebox.showwarning(
                "Limite atingido",
                "Você atingiu 30 horas trabalhadas não declaradas.\n"
                "O sistema não computa mais horas até que declare as existentes.\n\n"
                "Abra Tarefas e declare seu trabalho.",
            )
            return False
        if seg >= LIMITE_HORAS_AVISO:
            horas = seg // 3600
            messagebox.showwarning(
                "Atenção — horas não declaradas",
                f"Você tem mais de {horas} horas trabalhadas não declaradas.\n"
                f"O sistema só computa até 30 horas, perdendo horas que exceder isso.\n\n"
                f"Declare suas horas em Tarefas para não perder tempo.",
            )
        return True

    def _acao_principal(self) -> None:
        if not self._verificar_limite_horas():
            return
        if not self._monitor.tem_sessao_carregada():
            self._iniciar()
        elif self._monitor.obter_estado().rodando:
            self._pausar()
        else:
            self._retomar()

    def _rodar_em_background(self, operacao, ao_concluir, ao_falhar=None) -> None:
        """Executa operacao() em thread, chama ao_concluir/ao_falhar na UI thread."""
        def _thread():
            try:
                operacao()
                self.after(0, lambda: ao_concluir() if self.winfo_exists() else None)
            except Exception as e:
                if ao_falhar:
                    self.after(0, lambda: ao_falhar(e) if self.winfo_exists() else None)
        threading.Thread(target=_thread, daemon=True).start()

    def _iniciar(self) -> None:
        if not self._usuario:
            return

        if self._monitor.tem_sessao_carregada():
            messagebox.showwarning("Atenção", "Já existe uma sessão carregada. Use Retomar ou Finalizar.")
            return

        try:
            id_atividade, titulo = self._obter_id_atividade_selecionada()
        except Exception as erro:
            messagebox.showerror("Erro", str(erro))
            return

        self._var_status.set("Iniciando...")
        self._rodar_em_background(
            lambda: self._monitor.iniciar(self._usuario["user_id"], self._usuario["nome_exibicao"], id_atividade, titulo),
            lambda: self._var_status.set("TRABALHANDO"),
            lambda e: (self._var_status.set("ERRO"), messagebox.showerror("Erro", str(e))),
        )

    def _pausar(self) -> None:
        estado = self._monitor.obter_estado()
        if estado.situacao == "ocioso":
            self._var_status.set("OCIOSO — pausa bloqueada")
            return

        self._var_status.set("Pausando...")
        self._rodar_em_background(
            lambda: self._monitor.pausar(),
            lambda: self._var_status.set("PAUSADO") if self._monitor.tem_sessao_carregada() else None,
        )

    def _retomar(self) -> None:
        self._var_status.set("Retomando...")
        self._rodar_em_background(
            lambda: self._monitor.retomar(),
            lambda: self._var_status.set("TRABALHANDO") if self._monitor.tem_sessao_carregada() else None,
        )

    def _alternar_fixar(self) -> None:
        if self._janela_fixada and self._janela_fixada.winfo_exists():
            self._fechar_fixado()
            return
        self._abrir_fixado()

    # -------------------- Contagem regressiva (visual) --------------------
    def _regressiva_carregar_do_disco(self) -> None:
        try:
            if ARQUIVO_REGRESSIVA.exists():
                d = json.loads(ARQUIVO_REGRESSIVA.read_text(encoding="utf-8"))
                self._regressiva_alvo_seg = int(d.get("alvo_seg") or 0)
                self._regressiva_trab_inicio = int(d.get("trab_inicio") or 0)
                self._regressiva_ativa = bool(d.get("ativa") or False)
        except Exception:
            pass

    def _regressiva_salvar_no_disco(self) -> None:
        try:
            ARQUIVO_REGRESSIVA.write_text(
                json.dumps({
                    "alvo_seg": int(self._regressiva_alvo_seg),
                    "trab_inicio": int(self._regressiva_trab_inicio),
                    "ativa": bool(self._regressiva_ativa),
                }, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    @staticmethod
    def _regressiva_parse_tempo(texto: str) -> int | None:
        """Aceita '8h', '8h30m', '8:00', '8:00:00', '30m', '45' (minutos). Retorna segundos ou None."""
        t = (texto or "").strip().lower().replace(" ", "")
        if not t:
            return None
        # HH:MM:SS ou HH:MM
        if ":" in t:
            partes = t.split(":")
            try:
                nums = [int(p) for p in partes]
            except ValueError:
                return None
            if len(nums) == 2:
                h, m = nums; s = 0
            elif len(nums) == 3:
                h, m, s = nums
            else:
                return None
            total = h * 3600 + m * 60 + s
            return total if total > 0 else None
        # Formatos com sufixo h/m/s (ex: 8h, 8h30m, 90m, 45s, 1h15m30s)
        if any(c in t for c in "hms"):
            horas = minutos = segundos = 0
            buf = ""
            for ch in t:
                if ch.isdigit():
                    buf += ch
                elif ch in "hms":
                    if not buf:
                        return None
                    n = int(buf); buf = ""
                    if ch == "h": horas = n
                    elif ch == "m": minutos = n
                    elif ch == "s": segundos = n
                else:
                    return None
            if buf:  # lixo ao fim
                return None
            total = horas * 3600 + minutos * 60 + segundos
            return total if total > 0 else None
        # Só número → assume minutos
        try:
            n = int(t)
            return n * 60 if n > 0 else None
        except ValueError:
            return None

    def _abrir_modal_regressiva(self) -> None:
        dlg = tk.Toplevel(self)
        dlg.title("Contagem regressiva")
        dlg.geometry("360x220")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg="#111111")

        ttk.Label(
            dlg, text="Duração da contagem regressiva",
            font=("Segoe UI", 11, "bold"),
        ).pack(pady=(14, 4), padx=14, anchor="w")
        ttk.Label(
            dlg, text="Digite só números. Cada dígito empurra da direita (HH MM SS).",
            font=("Segoe UI", 9), foreground="#888888",
        ).pack(padx=14, anchor="w")

        # Buffer de até 6 dígitos; renderiza sempre como HH:MM:SS com zeros à esquerda.
        # Ex.: buffer="1" -> "00:00:01"; buffer="12" -> "00:00:12"; buffer="123456" -> "12:34:56".
        buffer = [""]
        if self._regressiva_ativa and self._regressiva_alvo_seg > 0:
            total = int(self._regressiva_alvo_seg)
            h, m, s = total // 3600, (total % 3600) // 60, total % 60
            buffer[0] = f"{h:02d}{m:02d}{s:02d}".lstrip("0")

        var_tempo = tk.StringVar(value="00:00:00")
        entrada = ttk.Entry(
            dlg, textvariable=var_tempo, font=("Consolas", 18, "bold"),
            justify="center",
        )
        entrada.pack(padx=14, pady=8, fill="x")
        entrada.focus_set()

        lbl_erro = ttk.Label(dlg, text="", foreground="#f0a500", font=("Segoe UI", 9))
        lbl_erro.pack(padx=14, anchor="w")

        def _renderizar() -> None:
            d = buffer[0].zfill(6)
            var_tempo.set(f"{d[0:2]}h {d[2:4]}m {d[4:6]}s")
            # Cursor sempre no fim (não selecionado); usuário não edita manualmente.
            try:
                entrada.icursor("end")
                entrada.selection_clear()
            except Exception:
                pass

        def _on_key(event: tk.Event) -> str | None:
            if event.keysym in ("Return", "Escape", "Tab"):
                return None  # deixa propagar
            if event.keysym == "BackSpace":
                buffer[0] = buffer[0][:-1]
                _renderizar()
                return "break"
            if event.char and event.char.isdigit():
                buffer[0] = (buffer[0] + event.char)[-6:]
                _renderizar()
                return "break"
            # Qualquer outra tecla: bloqueia edição (preserva a máscara)
            return "break"

        entrada.bind("<Key>", _on_key)
        _renderizar()

        botoes = ttk.Frame(dlg)
        botoes.pack(side="bottom", fill="x", padx=14, pady=12)

        def _ativar() -> None:
            d = buffer[0].zfill(6)
            h, m, s = int(d[0:2]), int(d[2:4]), int(d[4:6])
            segundos = h * 3600 + m * 60 + s
            if segundos <= 0:
                lbl_erro.config(text="Defina uma duração maior que zero.")
                return
            self._regressiva_alvo_seg = int(segundos)
            self._regressiva_trab_inicio = int(self._monitor.obter_segundos_trabalhando())
            self._regressiva_ativa = True
            self._regressiva_modal_mostrado = False
            self._regressiva_salvar_no_disco()
            self._aplicar_modo_regressiva()
            try: dlg.destroy()
            except Exception: pass

        def _desativar() -> None:
            self._regressiva_ativa = False
            self._regressiva_modal_mostrado = False
            self._regressiva_alvo_seg = 0
            self._regressiva_trab_inicio = 0
            self._regressiva_salvar_no_disco()
            self._aplicar_modo_regressiva()
            try: dlg.destroy()
            except Exception: pass

        ttk.Button(botoes, text="Cancelar", command=dlg.destroy).pack(side="right", padx=(6, 0))
        if self._regressiva_ativa:
            ttk.Button(botoes, text="Desativar", command=_desativar).pack(side="right", padx=(6, 0))
        ttk.Button(botoes, text="Ativar", style="Verde.TButton", command=_ativar).pack(side="right")

        dlg.bind("<Return>", lambda _e: _ativar())
        dlg.bind("<Escape>", lambda _e: dlg.destroy())

    def _aplicar_modo_regressiva(self) -> None:
        """Re-empacota labels da tela principal e da fixada conforme a regressiva esteja ativa ou não."""
        # Tela principal
        if hasattr(self, "_lbl_regressiva_principal") and hasattr(self, "_lbl_tempo_principal"):
            for w in (self._lbl_regressiva_principal, self._lbl_tempo_principal):
                try: w.pack_forget()
                except Exception: pass
            if self._regressiva_ativa:
                self._lbl_regressiva_principal.configure(font=("Segoe UI", 44, "bold"))
                self._lbl_tempo_principal.configure(font=("Segoe UI", 16, "bold"), foreground="#888888")
                self._lbl_regressiva_principal.pack(anchor="center")
                self._lbl_tempo_principal.pack(anchor="center", pady=(2, 0))
            else:
                self._lbl_tempo_principal.configure(font=("Segoe UI", 44, "bold"), foreground="#ffffff")
                self._lbl_tempo_principal.pack(anchor="center")

        # Fixada (se aberta)
        if hasattr(self, "_lbl_regressiva_fixado") and hasattr(self, "_lbl_tempo_fixado"):
            try:
                if self._janela_fixada and self._janela_fixada.winfo_exists():
                    for w in (self._lbl_regressiva_fixado, self._lbl_tempo_fixado):
                        try: w.pack_forget()
                        except Exception: pass
                    if self._regressiva_ativa:
                        self._lbl_regressiva_fixado.configure(font=("Segoe UI", 26, "bold"))
                        self._lbl_tempo_fixado.configure(font=("Segoe UI", 12), foreground="#888888")
                        self._lbl_regressiva_fixado.pack(anchor="center")
                        self._lbl_tempo_fixado.pack(anchor="center")
                    else:
                        self._lbl_tempo_fixado.configure(font=("Segoe UI", 26, "bold"), foreground="#ffffff")
                        self._lbl_tempo_fixado.pack(anchor="center")
            except Exception:
                pass

    def _disparar_fim_regressiva(self) -> None:
        """Pausa o cronômetro e mostra modal obrigatório, sempre topmost."""
        # Pausa em background (evita bloquear a UI)
        threading.Thread(target=self._monitor.pausar, daemon=True).start()

        # Reusa se já tem um diálogo aberto (evita empilhar)
        if self._regressiva_dialogo and self._regressiva_dialogo.winfo_exists():
            try: self._regressiva_dialogo.lift(); self._regressiva_dialogo.focus_force()
            except Exception: pass
            return

        alvo_formatado = formatar_hhmmss(self._regressiva_alvo_seg)
        dlg = tk.Toplevel(self)
        self._regressiva_dialogo = dlg
        dlg.title("Tempo encerrado")
        dlg.geometry("380x160")
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)
        dlg.transient(self)
        dlg.grab_set()
        dlg.configure(bg="#111111")
        dlg.protocol("WM_DELETE_WINDOW", lambda: None)  # Só fecha no OK

        ttk.Label(dlg, text="⏰ Tempo zerou!", font=("Segoe UI", 14, "bold")).pack(pady=(16, 6))
        ttk.Label(
            dlg,
            text=f"A contagem regressiva de {alvo_formatado} terminou.\nO cronômetro foi pausado automaticamente.",
            wraplength=340, justify="center",
        ).pack(padx=14)

        def _ok() -> None:
            self._regressiva_ativa = False
            self._regressiva_modal_mostrado = False
            self._regressiva_alvo_seg = 0
            self._regressiva_trab_inicio = 0
            self._regressiva_salvar_no_disco()
            self._aplicar_modo_regressiva()
            try: dlg.destroy()
            except Exception: pass
            self._regressiva_dialogo = None

        ttk.Button(dlg, text="OK", style="Verde.TButton", command=_ok).pack(pady=12)
        dlg.bind("<Return>", lambda _e: _ok())

        # Reforço: re-elevar o diálogo periodicamente enquanto estiver aberto
        def _manter_frente() -> None:
            try:
                if dlg.winfo_exists():
                    dlg.lift(); dlg.attributes("-topmost", True)
                    dlg.after(600, _manter_frente)
            except Exception:
                pass
        dlg.after(600, _manter_frente)

    def _abrir_janela_log(self) -> None:
        # Só disponível em modo script (dev); no .exe nem o botão é renderizado.
        if not MODO_SCRIPT:
            return
        from tkinter.scrolledtext import ScrolledText

        janela = tk.Toplevel(self)
        janela.title(f"Log técnico — cronômetro {VERSAO_APLICACAO}")
        janela.geometry("960x520")
        janela.configure(bg="#0f0f12")

        texto = ScrolledText(
            janela, wrap="none", font=("Consolas", 9),
            bg="#0f0f12", fg="#e2e8f0", insertbackground="#e2e8f0",
        )
        texto.pack(fill="both", expand=True)

        barra = ttk.Frame(janela)
        barra.pack(fill="x")

        var_auto = tk.BooleanVar(value=True)

        def _redesenhar() -> None:
            try:
                texto.config(state="normal")
                texto.delete("1.0", "end")
                for linha in LOG_TEC.linhas():
                    texto.insert("end", linha + "\n")
                if var_auto.get():
                    texto.see("end")
                texto.config(state="disabled")
            except Exception:
                pass

        def _copiar() -> None:
            try:
                janela.clipboard_clear()
                janela.clipboard_append("\n".join(LOG_TEC.linhas()))
            except Exception:
                pass

        def _limpar() -> None:
            LOG_TEC.limpar()
            _redesenhar()

        ttk.Checkbutton(barra, text="Auto-scroll", variable=var_auto).pack(side="left", padx=6, pady=4)
        ttk.Button(barra, text="Atualizar", command=_redesenhar).pack(side="left", padx=4)
        ttk.Button(barra, text="Copiar tudo", command=_copiar).pack(side="left", padx=4)
        ttk.Button(barra, text="Limpar", command=_limpar).pack(side="left", padx=4)
        ttk.Label(barra, text=f"Arquivo: {ARQUIVO_LOG_TECNICO}", foreground="#888").pack(side="right", padx=6)

        _redesenhar()

        def _loop_refresh() -> None:
            try:
                if not janela.winfo_exists():
                    return
                _redesenhar()
                janela.after(800, _loop_refresh)
            except Exception:
                pass

        janela.after(800, _loop_refresh)

    def _abrir_fixado(self) -> None:
        if self._janela_fixada and self._janela_fixada.winfo_exists():
            return

        janela = tk.Toplevel(self)
        janela.title("Cronômetro (Fixado)")
        janela.geometry("230x110")
        janela.resizable(False, False)
        janela.attributes("-topmost", True)
        janela.configure(bg="#111111", padx=10, pady=10)

        # Mesmo padrão da tela principal: dois labels, _aplicar_modo_regressiva escolhe o que mostra.
        self._lbl_regressiva_fixado = ttk.Label(
            janela, textvariable=self._var_tempo_regressiva_fixado,
            font=("Segoe UI", 26, "bold"), foreground="#ff6b1f",
        )
        self._lbl_tempo_fixado = ttk.Label(
            janela, textvariable=self._var_tempo_fixado,
            font=("Segoe UI", 26, "bold"),
        )
        # Status precisa ser criado antes do `_janela_fixada = janela` para ficar no pack order correto.
        self._lbl_status_fixado = ttk.Label(
            janela, textvariable=self._var_status_fixado, font=("Segoe UI", 9, "bold"),
        )
        self._lbl_status_fixado.pack(side="bottom", anchor="center", pady=(2, 0))

        # IMPORTANTE: definir _janela_fixada ANTES de _aplicar_modo_regressiva() — senão
        # _aplicar_modo_regressiva() ainda vê janela=None e não empacota os labels do fixado
        # (bug antigo: fixada abria só com status, sem o tempo).
        janela.protocol("WM_DELETE_WINDOW", self._fechar_fixado)
        self._janela_fixada = janela
        self._aplicar_modo_regressiva()

    def _fechar_fixado(self) -> None:
        try:
            if self._janela_fixada and self._janela_fixada.winfo_exists():
                self._janela_fixada.destroy()
        except Exception:
            pass
        self._janela_fixada = None

    def _finalizar(self) -> None:
        if not self._usuario:
            return
        if not self._verificar_limite_horas():
            return

        if not self._monitor.tem_sessao_carregada():
            messagebox.showwarning("Atenção", "Clique em INICIAR antes de ZERAR.")
            return

        if not messagebox.askyesno("Confirmar", "Deseja zerar o cronômetro?\nAs horas trabalhadas ficam salvas no banco."):
            return

        self._var_status.set("Zerando...")

        def _concluido():
            self._var_tempo.set("00:00:00")
            self._var_tempo_fixado.set("00:00:00")
            self._var_status.set("PRONTO")
            self._ultimo_segundo_renderizado = -1
            self._ultimo_status_renderizado = ""

        self._rodar_em_background(
            lambda: self._monitor.zerar_sessao(),
            _concluido,
        )

    def _abrir_tarefas_do_dia(self) -> None:
        if not self._usuario:
            return
        self._verificar_limite_horas()  # Avisa mas não bloqueia (usuário precisa declarar)

        if getattr(self._monitor, "_offline_notificado", False):
            messagebox.showwarning("Sem conexão", "Você precisa estar conectado à internet para acessar as tarefas.")
            return

        self._var_status.set("Carregando...")
        self.update_idletasks()

        try:
            id_atividade, titulo_atividade = self._obter_contexto_atividade_ativa()
        except Exception as erro:
            messagebox.showwarning("Atenção", str(erro))
            return

        JanelaSubtarefas(
            self,
            self._repositorio_declaracoes,
            self._usuario,
            id_atividade,
            titulo_atividade,
            segundos_trabalhando=self._monitor.obter_segundos_trabalhando(),
            segundos_pausado=self._monitor.obter_segundos_pausado(),
            modo_finalizacao=False,
            ao_finalizar=None,
            opcoes_canal=list(self._combo["values"]),
        )

    def _executar_finalizacao_do_dia(self, relatorio_final: str) -> None:
        self._monitor.finalizar(relatorio_final)
        self._var_status.set("FINALIZADO E SALVO")
        self._var_tempo.set("00:00:00")
        self._ultimo_segundo_renderizado = -1
        self._ultimo_status_renderizado = ""
        messagebox.showinfo(
            "OK",
            "Subtarefas enviadas para o servidor, cronômetro finalizado e relatório salvo.",
        )

    def _tick_ui(self) -> None:
        estado = self._monitor.obter_estado()
        segundos_cronometro = self._monitor.obter_segundos_cronometro()
        tem_sessao = self._monitor.tem_sessao_carregada()

        if estado.rodando:
            status_texto = estado.situacao.upper()
        else:
            if tem_sessao:
                status_texto = "PAUSADO"
            else:
                status_texto = "PRONTO" if self._usuario else "Faça login."

        if segundos_cronometro != self._ultimo_segundo_renderizado:
            tempo_formatado = formatar_hhmmss(segundos_cronometro)
            self._var_tempo.set(tempo_formatado)
            self._var_tempo_fixado.set(tempo_formatado)
            self._ultimo_segundo_renderizado = segundos_cronometro

        # Contagem regressiva (puramente visual — não altera trab/ocioso/pausado reais).
        if self._regressiva_ativa and self._regressiva_alvo_seg > 0:
            seg_trab = self._monitor.obter_segundos_trabalhando()
            decorridos = max(0, seg_trab - self._regressiva_trab_inicio)
            restante = max(0, self._regressiva_alvo_seg - decorridos)
            fmt_restante = formatar_hhmmss(restante)
            self._var_tempo_regressiva.set(fmt_restante)
            self._var_tempo_regressiva_fixado.set(fmt_restante)
            if restante <= 0 and not self._regressiva_modal_mostrado and tem_sessao and estado.rodando:
                self._regressiva_modal_mostrado = True
                self._disparar_fim_regressiva()

        if status_texto != self._ultimo_status_renderizado:
            self._var_status.set(status_texto)
            self._var_status_fixado.set(status_texto if tem_sessao or estado.rodando else "")
            self._ultimo_status_renderizado = status_texto

        # T24: cor do status reflete conectividade.
        # - verde quando conectado ao servidor
        # - amarelo quando em modo offline
        cor_status = "#facc15" if estado.offline else "#4ade80"
        for _lbl_attr in ("_lbl_status_principal", "_lbl_status_fixado"):
            _lbl = getattr(self, _lbl_attr, None)
            if _lbl is not None:
                try:
                    if _lbl.winfo_exists():
                        _lbl.configure(foreground=cor_status)
                except (AttributeError, tk.TclError):
                    pass

        if hasattr(self, "_var_texto_btn_principal"):
            if not tem_sessao:
                self._var_texto_btn_principal.set("Iniciar")
                _estilo_btn = "Verde.TButton"
            elif estado.rodando:
                self._var_texto_btn_principal.set("Pausar")
                _estilo_btn = "Primario.TButton"
            else:
                self._var_texto_btn_principal.set("Retomar")
                _estilo_btn = "Primario.TButton"
            try:
                self._btn_principal.configure(style=_estilo_btn)
            except (AttributeError, tk.TclError):
                pass

        # T24: separa visualmente "erro persistente" de "mensagem transitória de sucesso".
        # Erro/offline em amarelo-laranja; sucesso (fila re-enviada etc.) em verde e auto-expira.
        if estado.ultimo_erro:
            if estado.offline:
                self._var_erro.set("⚠ Perdemos a conexão com o servidor, provavelmente você está sem internet.")
            else:
                self._var_erro.set(f"⚠ {estado.ultimo_erro}")
            try:
                if self._lbl_erro_principal.winfo_exists():
                    self._lbl_erro_principal.configure(foreground="#f0a500")
            except (AttributeError, tk.TclError):
                pass
        elif estado.mensagem_sucesso:
            self._var_erro.set(f"✓ {estado.mensagem_sucesso}")
            try:
                if self._lbl_erro_principal.winfo_exists():
                    self._lbl_erro_principal.configure(foreground="#4ade80")
            except (AttributeError, tk.TclError):
                pass
        else:
            self._var_erro.set("")

        if hasattr(self, "_btn_tarefas"):
            try:
                if self._btn_tarefas.winfo_exists():
                    self._btn_tarefas.configure(state="disabled" if estado.offline else "normal")
            except Exception:
                pass

        self.after(INTERVALO_UI_MILISSEGUNDOS, self._tick_ui)

    def _ao_fechar(self) -> None:
        # Bloqueia novo clique no X enquanto finaliza
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        overlay = tk.Frame(self, bg="#111111")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        tk.Label(
            overlay,
            text="Saindo, aguarde...",
            bg="#111111",
            fg="#e0e0e0",
            font=("Segoe UI", 14, "bold"),
        ).place(relx=0.5, rely=0.5, anchor="center")
        self.update_idletasks()

        def _finalizar() -> None:
            try:
                self._monitor.pausar_e_preservar_sessao()
            except Exception:
                pass
            # Fase 2: desliga hooks low-level antes de fechar o app
            try:
                self._monitor._detector_input.parar()
            except Exception:
                pass
            try:
                self._banco.fechar_conexao_da_thread()
            except Exception:
                pass

            def _na_ui() -> None:
                self._fechar_fixado()
                self.destroy()

            self.after(0, _na_ui)

        threading.Thread(target=_finalizar, daemon=True).start()
