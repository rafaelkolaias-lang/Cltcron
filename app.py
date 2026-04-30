from __future__ import annotations

import ctypes
import json
import os
import platform
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import urllib.request
import uuid
from ctypes import wintypes
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import messagebox, ttk

import psutil

from atividades import RepositorioAtividades
from banco import BancoDados
from declaracoes_dia import RepositorioDeclaracoesDia

# =========================
# MODO SCRIPT (dev) vs EXE (produção)
# =========================
# MODO_SCRIPT=True quando rodando via `python app.py` (não compilado).
# PyInstaller define sys.frozen=True no .exe final.
MODO_SCRIPT = not getattr(sys, "frozen", False)


class LogTecnico:
    """Log técnico em memória + arquivo. Thread-safe. Usado para depurar o cronômetro em modo script."""

    def __init__(self, caminho_arquivo: Path, max_memoria: int = 2000) -> None:
        self._caminho = caminho_arquivo
        self._max = max_memoria
        self._lock = threading.Lock()
        self._memoria: list[str] = []
        try:
            self._caminho.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def log(self, categoria: str, mensagem: str, detalhes: object = None) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        linha = f"[{ts}] [{categoria:14}] {mensagem}"
        if detalhes is not None:
            try:
                linha += f" :: {json.dumps(detalhes, ensure_ascii=False, default=str)}"
            except Exception:
                linha += f" :: {detalhes}"
        with self._lock:
            self._memoria.append(linha)
            if len(self._memoria) > self._max:
                del self._memoria[: len(self._memoria) - self._max]
            try:
                with open(self._caminho, "a", encoding="utf-8") as f:
                    f.write(linha + "\n")
            except Exception:
                pass

    def linhas(self) -> list[str]:
        with self._lock:
            return list(self._memoria)

    def limpar(self) -> None:
        with self._lock:
            self._memoria.clear()
        try:
            if self._caminho.exists():
                self._caminho.write_text("", encoding="utf-8")
        except Exception:
            pass


ARQUIVO_LOG_TECNICO = Path.home() / ".cronometro_leve_log_tecnico.txt"
LOG_TEC = LogTecnico(ARQUIVO_LOG_TECNICO)


# =========================
# CONFIGURAÇÕES
# =========================
VERSAO_APLICACAO = "v2.7"

HISTORICO_VERSOES = [
    {
        "versao": "v2.5",
        "data": "18/04/2026",
        "notas": [
            "Contagem regressiva visual (ex.: jornada de 8h) com pausa automática e alerta obrigatório ao zerar",
            "Janela fixada mostra regressiva e cronômetro juntos; bug de abertura sem tempo corrigido",
            "Totais de trabalhado/ocioso/pausado aparecem no painel web quase em tempo real (atualização a cada 5 min e ao pausar)",
            "Gráficos do painel com Top Apps e barras foco/2.º plano precisos por dia (sem rateio proporcional)",
            "Exclusão automática de trechos ociosos nos gráficos de foco (trabalho líquido)",
            "Status 'TRABALHANDO' muda de cor: verde (online) / amarelo (offline)",
            "Mensagens de sincronização (fila re-enviada) aparecem em verde e somem sozinhas após 10s",
            "Reenvio offline robusto: itens de sessão inválida são descartados sem travar a fila",
            "Saneamento automático de registros pendurados ao iniciar/restaurar sessão",
            "Nome do usuário movido para o título da janela; botões do topo centralizados (Fixar / Regressiva / Sair)",
            "Log técnico detalhado com categorias de conexão (só modo desenvolvedor)",
        ],
    },
    {
        "versao": "v2.4",
        "data": "12/04/2026",
        "notas": [
            "Campo obrigatório Nº do Vídeo ao declarar tarefa",
            "Título salvo no formato: NUMERO - NOME DA TAREFA",
            "Campo aceita apenas números inteiros (zeros à esquerda removidos)",
            "Confirmação obrigatória de upload no Drive antes de salvar",
            "Ajuda contextual (?) nos campos Nº do Vídeo, Tarefa e Canal",
        ],
    },
    {
        "versao": "v2.3",
        "data": "08/04/2026",
        "notas": [
            "Tarefas de todas as datas na lista (não filtra mais por dia)",
            "Pagamentos aparecem na lista de tarefas",
            "Limite de 30h não declaradas (aviso a partir de 20h)",
            "Trava por hora: tarefas após pagamento ficam livres",
            "Ordenação por data e hora real (pagamentos na posição correta)",
            "Changelog acessível na tela de login",
            "Correções de travamento e estabilidade (9 bugs corrigidos)",
        ],
    },
    {
        "versao": "v2.2",
        "data": "08/04/2026",
        "notas": [
            "Versão exibida no título da janela",
            "Resiliência offline (fila de heartbeats)",
            "Notificações Windows ao perder/restaurar conexão",
            "Auto-login com credenciais salvas",
            "Fix deadlock no monitor (banco fora do lock)",
        ],
    },
]
URL_ATUALIZACAO = "https://raw.githubusercontent.com/rafaelkolaias-lang/Cltcron/main/painel/downloads/CronometroLeve.exe"

INTERVALO_LOOP_SEGUNDOS = 0.20
INTERVALO_UI_MILISSEGUNDOS = 80
INTERVALO_HEARTBEAT_SEGUNDOS = 60.0
INTERVALO_STATUS_BANCO_SEGUNDOS = 10.0

LIMITE_OCIOSO_SEGUNDOS = 5 * 60

LIMITE_HORAS_AVISO = 20 * 3600       # 20h — avisa o usuário
LIMITE_HORAS_MAXIMO = 30 * 3600      # 30h — para de computar

CAPTURAR_TITULO_JANELA = False

INTERVALO_SCAN_APPS_SEGUNDOS = 10.0

# Persistência parcial de cronometro_relatorios — grava/atualiza a cada N segundos
# na mesma linha (id_sessao, referencia_data), para o painel web enxergar totais
# quase em tempo real sem esperar o fechamento da sessão.
INTERVALO_UPSERT_RELATORIO_SEGUNDOS = 300.0  # 5 minutos

# Verificação periódica de atualização após o login (apenas avisa, não aplica).
# Só roda quando executado como .exe (PyInstaller). Se achar update, abre modal
# informativo; se o usuário ignorar, o aviso reaparece no próximo ciclo enquanto
# houver atualização disponível.
INTERVALO_VERIFICAR_UPDATE_MS = 10 * 60 * 1000  # 10 minutos

ARQUIVO_LOGIN_SALVO = Path.home() / ".cronometro_leve_login.json"
ARQUIVO_ESTADO_SESSAO = Path.home() / ".cronometro_leve_estado.json"
ARQUIVO_FILA_OFFLINE = Path.home() / ".cronometro_leve_fila_offline.json"
ARQUIVO_REGRESSIVA = Path.home() / ".cronometro_leve_regressiva.json"

TOLERANCIA_VALIDACAO_SEGUNDOS = 1


# =========================
# Windows API
# =========================
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class EstruturaUltimaEntrada(ctypes.Structure):
    _fields_ = [("tamanho", wintypes.UINT), ("tempo", wintypes.DWORD)]


def obter_segundos_ocioso_windows() -> int:
    estrutura = EstruturaUltimaEntrada()
    estrutura.tamanho = ctypes.sizeof(EstruturaUltimaEntrada)
    if not user32.GetLastInputInfo(ctypes.byref(estrutura)):
        return 0
    tempo_boot_ms = kernel32.GetTickCount()
    ocioso_ms = tempo_boot_ms - estrutura.tempo
    return max(0, int(ocioso_ms // 1000))


def _obter_texto_janela(hwnd: int) -> str:
    comprimento = user32.GetWindowTextLengthW(hwnd)
    if comprimento <= 0:
        return ""
    buffer = ctypes.create_unicode_buffer(comprimento + 1)
    user32.GetWindowTextW(hwnd, buffer, comprimento + 1)
    return buffer.value or ""


def obter_aplicativo_em_foco() -> tuple[str, str]:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ("desconhecido", "")

    titulo = ""
    if CAPTURAR_TITULO_JANELA:
        titulo = _obter_texto_janela(hwnd).strip()

    identificador_processo = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(identificador_processo))
    pid = int(identificador_processo.value or 0)

    if pid <= 0:
        return ("desconhecido", titulo)

    try:
        processo = psutil.Process(pid)
        nome_processo = (processo.name() or "desconhecido").strip()
    except Exception:
        nome_processo = "desconhecido"

    return (nome_processo, titulo)


_cache_nomes_processos: dict[int, tuple[str, float]] = {}
_CACHE_PROCESSO_TTL = 60.0


def _obter_nome_processo_cached(pid: int) -> str:
    """Retorna nome do processo com cache de 60s por PID."""
    agora = time.monotonic()
    entrada = _cache_nomes_processos.get(pid)
    if entrada and (agora - entrada[1]) < _CACHE_PROCESSO_TTL:
        return entrada[0]
    try:
        nome = (psutil.Process(pid).name() or "").strip()
    except Exception:
        nome = ""
    if nome:
        _cache_nomes_processos[pid] = (nome, agora)
    return nome


def listar_nomes_apps_visiveis() -> set[str]:
    """Retorna set de nomes de processos que têm janela visível com título não-vazio."""
    nomes: set[str] = set()

    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def _callback(hwnd: int, _: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        comprimento = user32.GetWindowTextLengthW(hwnd)
        if comprimento < 3:
            return True
        buffer = ctypes.create_unicode_buffer(comprimento + 1)
        user32.GetWindowTextW(hwnd, buffer, comprimento + 1)
        if not (buffer.value or "").strip():
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        pid_val = int(pid.value or 0)
        if pid_val <= 0:
            return True
        nome = _obter_nome_processo_cached(pid_val)
        if nome:
            nomes.add(nome)
        return True

    try:
        fn = EnumWindowsProc(_callback)
        user32.EnumWindows(fn, 0)
    except Exception:
        pass
    return nomes


def converter_segundos_para_inteiro(segundos_float: float) -> int:
    return int(max(0.0, float(segundos_float)))


def formatar_hhmmss(segundos: int) -> str:
    total = max(0, int(segundos or 0))
    horas = total // 3600
    minutos = (total % 3600) // 60
    segs = total % 60
    return f"{horas:02d}:{minutos:02d}:{segs:02d}"


def dividir_tempos_por_dia(
    inicio_em: datetime,
    fim_em: datetime,
    segundos_trabalhando: int,
    segundos_ocioso: int,
    segundos_pausado: int,
) -> list[tuple[date, int, int, int]]:
    seg_trab = max(0, int(segundos_trabalhando or 0))
    seg_oci = max(0, int(segundos_ocioso or 0))
    seg_pau = max(0, int(segundos_pausado or 0))

    if fim_em <= inicio_em or inicio_em.date() == fim_em.date():
        return [(inicio_em.date(), seg_trab, seg_oci, seg_pau)]

    total_segundos = max(1, int((fim_em - inicio_em).total_seconds()))
    fatias: list[tuple[date, int]] = []
    cursor = inicio_em
    while cursor < fim_em:
        proximo_dia = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time())
        limite = min(proximo_dia, fim_em)
        segundos_no_dia = int((limite - cursor).total_seconds())
        if segundos_no_dia <= 0:
            break
        fatias.append((cursor.date(), segundos_no_dia))
        cursor = limite

    if not fatias:
        return [(inicio_em.date(), seg_trab, seg_oci, seg_pau)]

    resultado: list[tuple[date, int, int, int]] = []
    acum_trab = 0
    acum_oci = 0
    acum_pau = 0
    for i, (dia, seg_dia) in enumerate(fatias):
        if i == len(fatias) - 1:
            parte_trab = seg_trab - acum_trab
            parte_oci = seg_oci - acum_oci
            parte_pau = seg_pau - acum_pau
        else:
            frac = seg_dia / total_segundos
            parte_trab = int(round(seg_trab * frac))
            parte_oci = int(round(seg_oci * frac))
            parte_pau = int(round(seg_pau * frac))
            acum_trab += parte_trab
            acum_oci += parte_oci
            acum_pau += parte_pau
        resultado.append((dia, max(0, parte_trab), max(0, parte_oci), max(0, parte_pau)))

    return resultado


# =========================
# Detector de input sintético (auto-clickers / macros)
# =========================
# Usa hooks low-level do Windows (WH_MOUSE_LL + WH_KEYBOARD_LL) para ler a flag
# LLMHF_INJECTED / LLKHF_INJECTED em cada evento. Eventos com essa flag foram
# gerados por software (mouse_event, SendInput, keybd_event), não por hardware
# físico. Acumula dois contadores independentes em "buckets de segundo":
# cada segundo do relógio em que houve ao menos 1 evento humano conta como 1
# segundo de "input humano". Idem para sintético. Se o mesmo segundo tiver
# os dois, vai para "misto" (contabilizado como humano — cenário raro).
#
# Thread-safe: callbacks do hook rodam numa thread dedicada com message loop;
# o MonitorDeUso lê snapshots via uma lock interna.

# Flags das estruturas low-level (msdn)
LLMHF_INJECTED             = 0x00000001   # mouse injetado
LLMHF_LOWER_IL_INJECTED    = 0x00000002   # mouse injetado por processo de integridade menor
LLKHF_INJECTED             = 0x00000010   # teclado injetado
LLKHF_LOWER_IL_INJECTED    = 0x00000002   # teclado injetado por processo de integridade menor

WH_KEYBOARD_LL = 13
WH_MOUSE_LL    = 14
HC_ACTION      = 0


class _MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", wintypes.POINT),
        ("mouseData", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class DetectorInputSintetico:
    """
    Instala hooks low-level e conta segundos distintos com input humano /
    sintético. Operação completamente transparente — não altera nada no
    cálculo de horas trabalhadas do MonitorDeUso. Apenas registra.
    """

    def __init__(self) -> None:
        self._trava = threading.Lock()
        # Buckets de segundos: conjuntos de timestamps inteiros. Usar set
        # garante contagem única por segundo (idempotente a N eventos/s).
        self._segs_humano: set[int] = set()
        self._segs_sintetico: set[int] = set()
        # Handles dos hooks (guardados pra desinstalar ao parar)
        self._hook_mouse = None
        self._hook_kbd = None
        # Callbacks C fortemente referenciados (se coletar os callbacks o Windows crasha)
        self._cb_mouse_ref = None
        self._cb_kbd_ref = None
        self._thread: threading.Thread | None = None
        self._parar_flag = threading.Event()
        self._thread_id = 0  # ID da thread de hooks, usado pra PostThreadMessage
        self._ativo = False

    # ── API pública ─────────────────────────────────────────────
    def iniciar(self) -> None:
        if self._ativo:
            return
        self._parar_flag.clear()
        self._thread = threading.Thread(target=self._loop_hooks, name="DetectorInputSintetico", daemon=True)
        self._thread.start()
        self._ativo = True

    def parar(self) -> None:
        if not self._ativo:
            return
        self._parar_flag.set()
        # Envia WM_QUIT pra thread do hook
        if self._thread_id:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0)
            except Exception:
                pass
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._ativo = False

    def snapshot_e_limpar(self) -> tuple[int, int, int, int]:
        """
        Retorna (segs_humano, segs_sintetico, min_ts, max_ts) acumulados
        desde o último snapshot, e zera os buckets. min_ts/max_ts são os
        segundos epoch do primeiro e último input observados (0 se vazio).
        """
        with self._trava:
            h = self._segs_humano
            s = self._segs_sintetico
            if not h and not s:
                return (0, 0, 0, 0)
            uniao = h | s
            min_ts = min(uniao) if uniao else 0
            max_ts = max(uniao) if uniao else 0
            # "Misto" (segundos em ambos) — conta como humano.
            seg_humano_final = len(h)
            seg_sintetico_final = len(s - h)
            self._segs_humano = set()
            self._segs_sintetico = set()
            return (seg_humano_final, seg_sintetico_final, min_ts, max_ts)

    # ── Internals ──────────────────────────────────────────────
    def _registrar(self, injetado: bool) -> None:
        ts = int(time.time())
        # Operação rápida, lock curto
        with self._trava:
            if injetado:
                self._segs_sintetico.add(ts)
            else:
                self._segs_humano.add(ts)

    def _loop_hooks(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        # Assinaturas corretas (LRESULT CALLBACK)
        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        def _cb_mouse(nCode, wParam, lParam):
            try:
                if nCode == HC_ACTION:
                    info = ctypes.cast(lParam, ctypes.POINTER(_MSLLHOOKSTRUCT)).contents
                    injetado = bool(info.flags & (LLMHF_INJECTED | LLMHF_LOWER_IL_INJECTED))
                    self._registrar(injetado)
            except Exception:
                pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        def _cb_kbd(nCode, wParam, lParam):
            try:
                if nCode == HC_ACTION:
                    info = ctypes.cast(lParam, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                    injetado = bool(info.flags & (LLKHF_INJECTED | LLKHF_LOWER_IL_INJECTED))
                    self._registrar(injetado)
            except Exception:
                pass
            return user32.CallNextHookEx(None, nCode, wParam, lParam)

        # Mantém referências fortes (crítico — coleta desses refs faz o Windows crashar o processo)
        self._cb_mouse_ref = HOOKPROC(_cb_mouse)
        self._cb_kbd_ref = HOOKPROC(_cb_kbd)

        try:
            hmod = kernel32.GetModuleHandleW(None)
            self._hook_mouse = user32.SetWindowsHookExW(WH_MOUSE_LL, self._cb_mouse_ref, hmod, 0)
            self._hook_kbd   = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._cb_kbd_ref, hmod, 0)

            if not self._hook_mouse or not self._hook_kbd:
                LOG_TEC.log("detector_input", "falha ao instalar hooks", {
                    "mouse": bool(self._hook_mouse), "kbd": bool(self._hook_kbd),
                })
                return

            self._thread_id = kernel32.GetCurrentThreadId()
            LOG_TEC.log("detector_input", "hooks instalados", {"thread_id": self._thread_id})

            # Message loop — hooks low-level só funcionam se a thread processar mensagens
            msg = wintypes.MSG()
            while not self._parar_flag.is_set():
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret == 0 or ret == -1:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            LOG_TEC.log("detector_input", "erro no loop", {"erro": str(e)})
        finally:
            try:
                if self._hook_mouse:
                    user32.UnhookWindowsHookEx(self._hook_mouse)
                if self._hook_kbd:
                    user32.UnhookWindowsHookEx(self._hook_kbd)
            except Exception:
                pass
            self._hook_mouse = None
            self._hook_kbd = None
            LOG_TEC.log("detector_input", "hooks desinstalados", {})


@dataclass
class EstadoMonitor:
    rodando: bool
    situacao: str
    segundos_trabalhando: int
    segundos_ocioso: int
    segundos_pausado: int
    ultimo_erro: str
    # T24: feedback visual rico na UI
    offline: bool = False          # True quando a app está em modo offline
    mensagem_sucesso: str = ""     # mensagem transitória (auto-expira; ex.: "fila re-enviada")


class MonitorDeUso:
    def __init__(self, banco: BancoDados) -> None:
        self._banco = banco
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._thread_loop: threading.Thread | None = None

        self._id_sessao: int | None = None
        self._token_sessao: str = ""
        self._referencia_data_sessao: date | None = None

        self._user_id: str = ""
        self._nome_exibicao: str = ""
        self._id_atividade: int = 0
        self._titulo_atividade: str = ""

        self._sessao_carregada: bool = False
        self._rodando: bool = False
        self._situacao_manual: str = "pausado"
        self._situacao_calculada: str = "pausado"

        self._segundos_trabalhando_float: float = 0.0
        self._segundos_ocioso_float: float = 0.0
        self._segundos_pausado_float: float = 0.0

        self._nome_app_foco: str = "desconhecido"
        self._titulo_janela_foco: str = ""
        self._id_foco_aberto: int | None = None
        # Acumulação cumulativa do foco atual — espelha o padrão de cronometro_apps_intervalos.
        # Se o app crashar, o último UPDATE periódico já gravou os segundos até ali, eliminando
        # o "fantasma de 3h" que vinha do cap aplicado a registros com fim_em IS NULL.
        self._segundos_em_foco_atual: int = 0
        self._mono_ultimo_acumulo_foco: float = 0.0
        self._mono_ultimo_flush_foco: float = 0.0

        self._ultimo_heartbeat_mono: float = 0.0
        self._ultimo_sync_status_mono: float = 0.0
        self._ultimo_flush_fila_mono: float = 0.0
        self._ultimo_marco_mono: float = 0.0
        self._ultimo_upsert_relatorio_mono: float = 0.0
        self._ultimo_erro: str = ""
        self._offline_notificado: bool = False
        # T24: mensagem transitória de sucesso (auto-expira no snapshot após ~10s)
        self._mensagem_sucesso: str = ""
        self._mensagem_sucesso_expira_mono: float = 0.0

        self._mapa_intervalos_apps: dict[str, dict] = {}
        self._ultimo_scan_apps_mono: float = 0.0
        self._ultimo_save_estado_mono: float = 0.0
        self._inicio_sessao_cache: datetime | None = None
        # Cache de sessões já validadas no banco — evita repetir SELECT por item no flush offline.
        self._cache_sessoes_validas: dict[int, bool] = {}

        # Fase 2 — Detector de input humano vs sintético (auto-clickers)
        # Roda em thread separada com hooks low-level. Operação transparente:
        # não altera o cálculo de horas, só registra em cronometro_input_stats.
        self._detector_input = DetectorInputSintetico()

    def _registrar_erro_locked(self, mensagem: str) -> None:
        self._ultimo_erro = (mensagem or "").strip()[:240]

    def _registrar_sucesso_locked(self, mensagem: str, segundos: float = 10.0) -> None:
        """Mensagem transitória de sucesso — auto-expira após `segundos` via snapshot."""
        self._mensagem_sucesso = (mensagem or "").strip()[:240]
        self._mensagem_sucesso_expira_mono = time.monotonic() + max(0.0, segundos)

    def _snapshot_locked(self) -> EstadoMonitor:
        trabalhando = self._segundos_trabalhando_float
        ocioso = self._segundos_ocioso_float
        pausado = self._segundos_pausado_float

        if self._rodando and self._ultimo_marco_mono > 0:
            agora = time.monotonic()
            delta = max(0.0, agora - self._ultimo_marco_mono)

            if self._situacao_manual == "pausado":
                pausado += delta
            else:
                if self._situacao_calculada == "ocioso":
                    ocioso += delta
                else:
                    trabalhando += delta

        # Expira mensagem transitória de sucesso após o tempo configurado.
        msg_sucesso = self._mensagem_sucesso
        if msg_sucesso and time.monotonic() >= self._mensagem_sucesso_expira_mono:
            self._mensagem_sucesso = ""
            msg_sucesso = ""

        return EstadoMonitor(
            rodando=self._rodando,
            situacao=self._situacao_calculada,
            segundos_trabalhando=converter_segundos_para_inteiro(trabalhando),
            segundos_ocioso=converter_segundos_para_inteiro(ocioso),
            segundos_pausado=converter_segundos_para_inteiro(pausado),
            ultimo_erro=self._ultimo_erro,
            offline=self._offline_notificado,
            mensagem_sucesso=msg_sucesso,
        )

    def obter_estado(self) -> EstadoMonitor:
        with self._trava:
            return self._snapshot_locked()

    def tem_sessao_carregada(self) -> bool:
        with self._trava:
            return self._sessao_carregada

    def _delta_tempo_locked(self) -> float:
        if self._rodando and self._ultimo_marco_mono > 0:
            return max(0.0, time.monotonic() - self._ultimo_marco_mono)
        return 0.0

    def obter_segundos_cronometro(self) -> int:
        with self._trava:
            delta = self._delta_tempo_locked()
            trab = self._segundos_trabalhando_float
            ocioso = self._segundos_ocioso_float
            if self._situacao_manual != "pausado":
                if self._situacao_calculada == "ocioso":
                    ocioso += delta
                else:
                    trab += delta
            return int(trab + ocioso)

    def obter_segundos_trabalhando(self) -> int:
        with self._trava:
            delta = self._delta_tempo_locked()
            trab = self._segundos_trabalhando_float
            if self._situacao_manual != "pausado" and self._situacao_calculada != "ocioso":
                trab += delta
            return int(trab)

    def obter_segundos_pausado(self) -> int:
        with self._trava:
            delta = self._delta_tempo_locked()
            pausado = self._segundos_pausado_float
            if self._situacao_manual == "pausado":
                pausado += delta
            return int(pausado)

    def _acumular_tempo_ate_agora_locked(self, mono_agora: float) -> None:
        if self._ultimo_marco_mono <= 0:
            self._ultimo_marco_mono = mono_agora
            return

        if not self._rodando:
            self._ultimo_marco_mono = mono_agora
            return

        delta = max(0.0, mono_agora - self._ultimo_marco_mono)
        if delta <= 0:
            return

        if self._situacao_manual == "pausado":
            self._segundos_pausado_float += delta
        else:
            if self._situacao_calculada == "ocioso":
                self._segundos_ocioso_float += delta
            else:
                # Não acumula acima do limite máximo
                if self._segundos_trabalhando_float < LIMITE_HORAS_MAXIMO:
                    self._segundos_trabalhando_float = min(
                        self._segundos_trabalhando_float + delta,
                        float(LIMITE_HORAS_MAXIMO),
                    )

        self._ultimo_marco_mono = mono_agora

    def _inserir_evento(
        self,
        tipo_evento: str,
        situacao: str,
        idle_segundos: int,
        id_sessao: int | None = None,
        user_id: str | None = None,
        ocorrido_em: datetime | None = None,
    ) -> None:
        _id = id_sessao if id_sessao is not None else self._id_sessao
        _uid = user_id if user_id is not None else self._user_id
        if _id is None or not _uid:
            return

        try:
            self._banco.executar(
                """
                INSERT INTO cronometro_eventos_status
                    (id_sessao, user_id, tipo_evento, situacao, ocorrido_em, idle_segundos)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [_id, _uid, tipo_evento, situacao, ocorrido_em or datetime.now(), int(idle_segundos)],
            )
            LOG_TEC.log("evento", f"{tipo_evento} -> {situacao}", {
                "id_sessao": _id, "user_id": _uid, "idle": int(idle_segundos),
            })
        except Exception as erro:
            LOG_TEC.log("evento_erro", f"falha ao inserir {tipo_evento}", {"erro": str(erro)})
            raise

    def _flush_input_stats_locked_free(self) -> None:
        """
        Lê o snapshot acumulado pelo DetectorInputSintetico desde o último
        flush e insere uma linha em cronometro_input_stats. Chamado pelo loop
        fora de self._trava (por isso o sufixo _locked_free).
        """
        # Snapshot leve (só copia e zera os contadores do detector)
        seg_humano, seg_sintetico, min_ts, max_ts = self._detector_input.snapshot_e_limpar()
        if seg_humano == 0 and seg_sintetico == 0:
            return

        # Captura campos de sessão (snapshot atômico)
        with self._trava:
            id_sessao = self._id_sessao
            user_id = self._user_id
            ref_data = self._referencia_data_sessao or date.today()

        if id_sessao is None or not user_id:
            return

        bucket_inicio_em = (
            datetime.fromtimestamp(min_ts) if min_ts > 0 else datetime.now()
        )

        try:
            self._banco.executar(
                """
                INSERT INTO cronometro_input_stats
                    (id_sessao, user_id, bucket_inicio_em,
                     segundos_input_humano, segundos_input_sintetico, referencia_data)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    id_sessao, user_id, bucket_inicio_em,
                    int(seg_humano), int(seg_sintetico), ref_data,
                ],
            )
            LOG_TEC.log("detector_input", "stats gravado", {
                "id_sessao": id_sessao,
                "humano": int(seg_humano),
                "sintetico": int(seg_sintetico),
                "ref_data": str(ref_data),
            })
        except Exception as erro:
            LOG_TEC.log("detector_input", "falha ao gravar stats", {"erro": str(erro)})
            # não propaga — perder um bucket não é crítico

    # --- Fila offline ---

    def _carregar_fila_offline(self) -> list[dict]:
        try:
            if ARQUIVO_FILA_OFFLINE.exists():
                return json.loads(ARQUIVO_FILA_OFFLINE.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _salvar_fila_offline(self, fila: list[dict]) -> None:
        try:
            ARQUIVO_FILA_OFFLINE.write_text(
                json.dumps(fila, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _adicionar_a_fila_offline(
        self,
        tipo_evento: str,
        situacao: str,
        idle_segundos: int,
        ocorrido_em: datetime | None = None,
    ) -> None:
        fila = self._carregar_fila_offline()
        tam_antes = len(fila)
        ocorrido_iso = (ocorrido_em or datetime.now()).isoformat()
        fila.append({
            "tipo_evento": tipo_evento,
            "situacao": situacao,
            "idle_segundos": idle_segundos,
            "id_sessao": self._id_sessao,
            "user_id": self._user_id,
            "ocorrido_em": ocorrido_iso,
        })
        self._salvar_fila_offline(fila)
        LOG_TEC.log("offline_fila", f"+{tipo_evento}", {
            "tipo_evento": tipo_evento,
            "situacao": situacao,
            "idle": int(idle_segundos),
            "id_sessao": self._id_sessao,
            "user_id": self._user_id,
            "ocorrido_em": ocorrido_iso,
            "fila_antes": tam_antes,
            "fila_depois": len(fila),
        })

    def _sessao_valida_para_replay(self, id_sessao) -> bool | None:
        """Verifica se `id_sessao` existe em `cronometro_sessoes`.
        Retorna True/False se conseguiu consultar, ou None se o banco estiver inacessível
        (nesse caso o caller deve manter o item na fila, não descartar).
        Usa cache local para evitar SELECT repetido por item.
        """
        try:
            ids = int(id_sessao)
        except (TypeError, ValueError):
            return False
        if ids <= 0:
            return False
        if ids in self._cache_sessoes_validas:
            return self._cache_sessoes_validas[ids]
        try:
            linha = self._banco.consultar_um(
                "SELECT 1 AS ok FROM cronometro_sessoes WHERE id_sessao = %s LIMIT 1",
                [ids],
            )
        except Exception:
            return None  # banco indisponível
        valido = linha is not None
        self._cache_sessoes_validas[ids] = valido
        return valido

    def _tentar_flush_fila_offline(self) -> None:
        """Re-envia eventos pendentes. Descarta itens órfãos (sessão inexistente / FK violation)
        em vez de travar a fila. Preserva itens válidos e retoma no próximo tick em caso de
        erro genuíno de conexão.
        """
        fila = self._carregar_fila_offline()
        if not fila:
            return
        tam_inicial = len(fila)
        inicio_flush = datetime.now()
        LOG_TEC.log("offline_flush_inicio", f"tentando reenviar {tam_inicial}", {
            "fila_tam": tam_inicial,
            "iniciado_em": inicio_flush.isoformat(),
        })

        nova_fila: list[dict] = []
        enviados = 0
        descartados = 0
        falhou_conexao = False
        falhou_em: dict | None = None

        for idx, item in enumerate(fila):
            if falhou_conexao:
                # Preserva restante; a fila retoma no próximo flush.
                nova_fila.append(item)
                continue

            id_sessao_item = item.get("id_sessao")
            # Primeiro valida a sessão. None = banco indisponível → aborta flush preservando item.
            validade = self._sessao_valida_para_replay(id_sessao_item)
            if validade is None:
                falhou_em = {"tipo_evento": item.get("tipo_evento"), "indice": idx, "erro": "banco_indisponivel"}
                LOG_TEC.log("offline_flush_item", f"FALHA_CONEXAO {item.get('tipo_evento','')}", falhou_em)
                nova_fila.append(item)
                falhou_conexao = True
                continue
            if validade is False:
                LOG_TEC.log("offline_flush_item", f"DESCARTADO_ORFAO {item.get('tipo_evento','')}", {
                    "tipo_evento": item.get("tipo_evento"),
                    "id_sessao": id_sessao_item,
                    "motivo": "sessao_inexistente",
                    "indice": idx,
                })
                descartados += 1
                continue

            try:
                ocorrido = datetime.fromisoformat(item["ocorrido_em"])
                self._banco.executar(
                    """
                    INSERT INTO cronometro_eventos_status
                        (id_sessao, user_id, tipo_evento, situacao, ocorrido_em, idle_segundos)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        item["id_sessao"],
                        item["user_id"],
                        item["tipo_evento"],
                        item["situacao"],
                        ocorrido,
                        int(item["idle_segundos"]),
                    ],
                )
                LOG_TEC.log("offline_flush_item", f"OK {item.get('tipo_evento', '')}", {
                    "tipo_evento": item.get("tipo_evento"),
                    "situacao": item.get("situacao"),
                    "id_sessao": item.get("id_sessao"),
                    "user_id": item.get("user_id"),
                    "ocorrido_em": item.get("ocorrido_em"),
                    "indice": idx,
                })
                enviados += 1
            except Exception as erro:
                msg_erro = str(erro).lower()
                # FK violation ou sessão sumiu entre validação e INSERT → descarta, não bloqueia.
                if "foreign key" in msg_erro or "1452" in msg_erro or "fk" in msg_erro:
                    LOG_TEC.log("offline_flush_item", f"DESCARTADO_FK {item.get('tipo_evento','')}", {
                        "tipo_evento": item.get("tipo_evento"),
                        "id_sessao": id_sessao_item,
                        "motivo": "fk_violation",
                        "erro": str(erro),
                        "indice": idx,
                    })
                    descartados += 1
                    # Invalida a sessão no cache para os próximos itens
                    try: self._cache_sessoes_validas[int(id_sessao_item)] = False
                    except Exception: pass
                else:
                    falhou_em = {"tipo_evento": item.get("tipo_evento"), "indice": idx, "erro": str(erro)}
                    LOG_TEC.log("offline_flush_item", f"FALHA {item.get('tipo_evento','')}", falhou_em)
                    nova_fila.append(item)
                    falhou_conexao = True

        pendentes = len(nova_fila)
        # Sempre persiste — para remover itens descartados mesmo quando nada foi enviado.
        self._salvar_fila_offline(nova_fila)

        conexao_saiu_do_offline = False
        if (enviados > 0 or descartados > 0) and pendentes == 0 and self._offline_notificado:
            self._offline_notificado = False
            self._notificar_conexao_restaurada(enviados)
            conexao_saiu_do_offline = True
            LOG_TEC.log("conexao_restaurada", f"fila limpa — enviados={enviados} descartados={descartados}", {
                "reenviados": enviados,
                "descartados": descartados,
            })

        if enviados > 0 or descartados > 0:
            msg = (
                f"Fila offline: {enviados} eventos re-enviados"
                + (f", {descartados} descartados" if descartados else "")
                + (f", {pendentes} ainda pendentes" if pendentes else " (fila limpa)")
            )
            # Mensagem transitória (auto-some em ~10s). Não usa _registrar_erro_locked para
            # não ficar com aparência de erro persistente na UI.
            self._registrar_sucesso_locked(msg, 10.0)

        LOG_TEC.log("offline_flush_fim", f"enviados={enviados} descartados={descartados} pendentes={pendentes}", {
            "tam_inicial": tam_inicial,
            "enviados": enviados,
            "descartados": descartados,
            "pendentes": pendentes,
            "duracao_seg": (datetime.now() - inicio_flush).total_seconds(),
            "falhou_em": falhou_em,
        })

        # Consolida tempos parciais imediatamente ao sair do offline — o painel web
        # enxerga o período offline sem depender de replay evento a evento.
        if conexao_saiu_do_offline:
            try:
                self._upsert_relatorio_parcial()
                LOG_TEC.log("conexao_restaurada", "relatorio parcial consolidado apos reconexao")
            except Exception as erro:
                LOG_TEC.log("conexao_erro", "falha ao consolidar parcial pos-reconexao", {"erro": str(erro)})

    def _notificar_sem_conexao(self) -> None:
        """Popup Windows não-bloqueante avisando sobre queda de conexão."""
        def _popup() -> None:
            ctypes.windll.user32.MessageBoxW(
                0,
                "O Cronômetro perdeu a conexão com o servidor.\n\n"
                "O cronômetro continua rodando normalmente.\n"
                "Os dados serão enviados automaticamente quando a conexão voltar.",
                "Cronômetro — Sem conexão com o servidor",
                0x00010030,  # MB_OK | MB_ICONWARNING | MB_SETFOREGROUND
            )
        threading.Thread(target=_popup, daemon=True).start()

    def _notificar_conexao_restaurada(self, eventos_enviados: int) -> None:
        """Popup Windows não-bloqueante avisando que a conexão voltou."""
        def _popup() -> None:
            ctypes.windll.user32.MessageBoxW(
                0,
                f"Conexão com o servidor restaurada!\n\n"
                f"{eventos_enviados} evento(s) pendente(s) foram enviados com sucesso.",
                "Cronômetro — Conexão restaurada",
                0x00010040,  # MB_OK | MB_ICONINFORMATION | MB_SETFOREGROUND
            )
        threading.Thread(target=_popup, daemon=True).start()

    def _sanear_registros_abertos_do_usuario(self, user_id: str) -> None:
        """Fecha registros antigos com fim_em IS NULL, aplicando caps de sanidade:
        - cronometro_foco_janela:
            - se segundos_em_foco > 0 (cliente novo): usa inicio_em + segundos_em_foco como verdade.
            - senão (registros legados): cap de 3h sobre inicio_em — só pra não deixar fim_em nulo.
        - cronometro_apps_intervalos: teto de 20h por período (app aberto acima disso é fantasma).
        Roda antes de iniciar/restaurar sessão para não deixar lixo legado poluindo gráficos.
        """
        uid = (user_id or "").strip()
        if not uid:
            return
        try:
            # Registros novos (segundos_em_foco > 0): a duração real foi acumulada
            # em tempo real pelo _flush_foco_periodico até o crash. Fecha exatamente em
            # inicio_em + segundos_em_foco — sem inflar até cap arbitrário.
            linhas_foco_novos = self._banco.executar_e_contar(
                """
                UPDATE cronometro_foco_janela
                   SET fim_em = DATE_ADD(inicio_em, INTERVAL segundos_em_foco SECOND)
                 WHERE user_id = %s
                   AND fim_em IS NULL
                   AND segundos_em_foco > 0
                """,
                [uid],
            )
            # Registros legados (segundos_em_foco = 0, cliente antigo): cap de 3h como fallback.
            linhas_foco_legados = self._banco.executar_e_contar(
                """
                UPDATE cronometro_foco_janela
                   SET fim_em = DATE_ADD(inicio_em, INTERVAL 3 HOUR)
                 WHERE user_id = %s
                   AND fim_em IS NULL
                   AND segundos_em_foco = 0
                   AND inicio_em < NOW() - INTERVAL 3 HOUR
                """,
                [uid],
            )
            linhas_foco = int(linhas_foco_novos) + int(linhas_foco_legados)
            linhas_apps = self._banco.executar_e_contar(
                """
                UPDATE cronometro_apps_intervalos
                   SET fim_em = DATE_ADD(inicio_em, INTERVAL 20 HOUR)
                 WHERE user_id = %s
                   AND fim_em IS NULL
                   AND inicio_em < NOW() - INTERVAL 20 HOUR
                """,
                [uid],
            )
            # Só loga se houve limpeza real — evita poluir o log com "nada fechado" em cada iniciar/restaurar.
            if linhas_foco > 0 or linhas_apps > 0:
                LOG_TEC.log("saneamento", f"user={uid}", {
                    "foco_fechados": linhas_foco,
                    "apps_fechados": linhas_apps,
                })
        except Exception as erro:
            LOG_TEC.log("saneamento_erro", f"user={uid}", {"erro": str(erro)})

    def _abrir_foco(self, nome_app: str, titulo: str) -> None:
        if self._id_sessao is None:
            return

        self._id_foco_aberto = self._banco.executar(
            """
            INSERT INTO cronometro_foco_janela
                (id_sessao, user_id, nome_app, titulo_janela, inicio_em, fim_em, segundos_em_foco)
            VALUES (%s, %s, %s, %s, %s, NULL, 0)
            """,
            [self._id_sessao, self._user_id, nome_app, (titulo or None), datetime.now()],
        )
        # Reseta contadores cumulativos do foco recém-aberto.
        self._segundos_em_foco_atual = 0
        self._mono_ultimo_acumulo_foco = time.monotonic()
        self._mono_ultimo_flush_foco = self._mono_ultimo_acumulo_foco
        LOG_TEC.log("foco", f"abrir {nome_app}", {"titulo": titulo or "", "id_foco": self._id_foco_aberto})

    def _fechar_foco(self) -> None:
        if self._id_foco_aberto is None:
            return

        # Antes de fechar, acumula o tempo restante desde o último acúmulo.
        self._acumular_foco_locked(time.monotonic())

        self._banco.executar(
            "UPDATE cronometro_foco_janela SET fim_em = %s, segundos_em_foco = %s WHERE id_foco = %s",
            [datetime.now(), int(self._segundos_em_foco_atual), self._id_foco_aberto],
        )
        LOG_TEC.log("foco", "fechar", {
            "id_foco": self._id_foco_aberto,
            "segundos_em_foco": int(self._segundos_em_foco_atual),
        })
        self._id_foco_aberto = None
        self._segundos_em_foco_atual = 0
        self._mono_ultimo_acumulo_foco = 0.0
        self._mono_ultimo_flush_foco = 0.0

    def _acumular_foco_locked(self, mono_agora: float) -> None:
        """Soma delta desde o último acúmulo no contador em memória.

        Chamado a cada tick do _loop e antes de qualquer UPDATE/fechamento.
        Operação puramente em memória — UPDATE periódico vai pra _flush_foco_periodico.
        """
        if self._id_foco_aberto is None:
            return
        if self._mono_ultimo_acumulo_foco <= 0:
            self._mono_ultimo_acumulo_foco = mono_agora
            return
        delta = mono_agora - self._mono_ultimo_acumulo_foco
        if delta <= 0:
            return
        self._segundos_em_foco_atual += int(delta)
        self._mono_ultimo_acumulo_foco = mono_agora

    def _flush_foco_periodico(self, mono_agora: float, intervalo: float) -> bool:
        """Grava segundos_em_foco no banco a cada `intervalo` segundos (sem fechar fim_em).

        Retorna True se houve flush. Chamado FORA do lock — id e segundos são
        snapshots resolvidos antes da chamada.
        """
        if self._id_foco_aberto is None:
            return False
        if (mono_agora - self._mono_ultimo_flush_foco) < intervalo:
            return False
        id_snap = self._id_foco_aberto
        seg_snap = int(self._segundos_em_foco_atual)
        self._mono_ultimo_flush_foco = mono_agora
        try:
            self._banco.executar(
                "UPDATE cronometro_foco_janela SET segundos_em_foco = %s WHERE id_foco = %s",
                [seg_snap, id_snap],
            )
        except Exception:
            return False
        return True

    def _abrir_intervalo_app_locked(self, nome_app: str) -> int | None:
        if self._id_sessao is None or not self._user_id:
            return None
        return self._banco.executar(
            """
            INSERT INTO cronometro_apps_intervalos
                (id_sessao, user_id, nome_app, inicio_em, segundos_em_foco, segundos_segundo_plano)
            VALUES (%s, %s, %s, %s, 0, 0)
            """,
            [self._id_sessao, self._user_id, nome_app, datetime.now()],
        )

    def _atualizar_intervalos_apps_locked(self, apps_visiveis: set[str], delta: int) -> None:
        nome_foco = self._nome_app_foco or "desconhecido"
        agora = datetime.now()

        # Acumula deltas em memória e fecha apps que sumiram
        apps_fechados = []
        for nome_app in list(self._mapa_intervalos_apps.keys()):
            dados = self._mapa_intervalos_apps[nome_app]
            if nome_app in apps_visiveis:
                if nome_app == nome_foco:
                    dados["segundos_em_foco"] += delta
                else:
                    dados["segundos_segundo_plano"] += delta
            else:
                apps_fechados.append(nome_app)

        # Batch UPDATE de todos os apps ativos + fechados em uma operação
        for nome_app in apps_fechados:
            dados = self._mapa_intervalos_apps.pop(nome_app)
            try:
                self._banco.executar(
                    """
                    UPDATE cronometro_apps_intervalos
                    SET fim_em = %s, segundos_em_foco = %s, segundos_segundo_plano = %s
                    WHERE id_intervalo = %s
                    """,
                    [agora, dados["segundos_em_foco"], dados["segundos_segundo_plano"], dados["id_intervalo"]],
                )
            except Exception:
                pass

        # Batch UPDATE dos apps ativos (uma query com executar_muitos)
        updates_ativos = []
        for dados in self._mapa_intervalos_apps.values():
            updates_ativos.append([dados["segundos_em_foco"], dados["segundos_segundo_plano"], dados["id_intervalo"]])
        if updates_ativos:
            try:
                self._banco.executar_muitos(
                    """
                    UPDATE cronometro_apps_intervalos
                    SET segundos_em_foco = %s, segundos_segundo_plano = %s
                    WHERE id_intervalo = %s
                    """,
                    updates_ativos,
                )
            except Exception:
                pass

        # Abre intervalos para apps novos (INSERT já com valores corretos, sem UPDATE extra)
        for nome_app in apps_visiveis:
            if nome_app in self._mapa_intervalos_apps:
                continue
            try:
                seg_foco = delta if nome_app == nome_foco else 0
                seg_bg = 0 if nome_app == nome_foco else delta
                id_intervalo = self._banco.executar(
                    """
                    INSERT INTO cronometro_apps_intervalos
                        (id_sessao, user_id, nome_app, inicio_em, segundos_em_foco, segundos_segundo_plano)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [self._id_sessao, self._user_id, nome_app, agora, seg_foco, seg_bg],
                )
                if id_intervalo:
                    self._mapa_intervalos_apps[nome_app] = {
                        "id_intervalo": id_intervalo,
                        "segundos_em_foco": seg_foco,
                        "segundos_segundo_plano": seg_bg,
                    }
            except Exception:
                pass

    def _fechar_todos_intervalos_apps_locked(self) -> None:
        if not self._mapa_intervalos_apps:
            return
        agora = datetime.now()
        for dados in self._mapa_intervalos_apps.values():
            try:
                self._banco.executar(
                    """
                    UPDATE cronometro_apps_intervalos
                    SET fim_em = %s, segundos_em_foco = %s, segundos_segundo_plano = %s
                    WHERE id_intervalo = %s
                    """,
                    [agora, dados["segundos_em_foco"], dados["segundos_segundo_plano"], dados["id_intervalo"]],
                )
            except Exception:
                pass
        self._mapa_intervalos_apps.clear()

    def _montar_atividade_status_locked(self) -> str:
        titulo = (self._titulo_atividade or "").strip()
        if not titulo:
            return ""
        return titulo[:255]

    def _montar_apps_json_locked(self) -> str:
        nome_foco = self._nome_app_foco or "desconhecido"
        abertos: list[dict] = []
        for nome_app, dados in self._mapa_intervalos_apps.items():
            if not nome_app or nome_app == "desconhecido":
                continue
            abertos.append({
                "nome_app": nome_app,
                "em_foco": nome_app == nome_foco,
                "segundos_em_foco": int(dados.get("segundos_em_foco", 0) or 0),
                "segundos_segundo_plano": int(dados.get("segundos_segundo_plano", 0) or 0),
            })
        abertos.sort(key=lambda item: (
            0 if item.get("em_foco") else 1,
            -int(item.get("segundos_em_foco", 0) or 0) - int(item.get("segundos_segundo_plano", 0) or 0),
            str(item.get("nome_app", "")),
        ))
        payload = {
            "abertos": abertos,
            "em_foco": {
                "nome_app": nome_foco,
                "titulo_janela": self._titulo_janela_foco or "",
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _atualizar_status_atual_locked(self) -> None:
        if not self._user_id:
            return

        situacao = self._situacao_calculada or "pausado"
        atividade = self._montar_atividade_status_locked()
        inicio_em = getattr(self, "_inicio_sessao_cache", None)

        if inicio_em is None and self._id_sessao is not None:
            linha_sessao = self._banco.consultar_um(
                "SELECT iniciado_em FROM cronometro_sessoes WHERE id_sessao = %s LIMIT 1",
                [self._id_sessao],
            )
            if linha_sessao:
                inicio_em = linha_sessao["iniciado_em"]
                self._inicio_sessao_cache = inicio_em

        apps_json = self._montar_apps_json_locked()
        agora = datetime.now()
        segundos_pausado = int(self._segundos_pausado_float)

        try:
            self._banco.executar(
                """
                INSERT INTO usuarios_status_atual
                    (user_id, situacao, atividade, inicio_em, ultimo_em, segundos_pausado, apps_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    situacao = VALUES(situacao),
                    atividade = VALUES(atividade),
                    inicio_em = VALUES(inicio_em),
                    ultimo_em = VALUES(ultimo_em),
                    segundos_pausado = VALUES(segundos_pausado),
                    apps_json = VALUES(apps_json)
                """,
                [self._user_id, situacao, atividade, inicio_em, agora, segundos_pausado, apps_json],
            )
            LOG_TEC.log("status_banco", f"upsert user={self._user_id} sit={situacao}", {
                "segundos_pausado": segundos_pausado,
                "apps_json_tam": len(apps_json or ""),
            })
        except Exception as erro:
            LOG_TEC.log("status_erro", f"falha upsert user={self._user_id}", {"erro": str(erro)})
            raise

    def _limpar_status_atual(self) -> None:
        if not self._user_id:
            return

        apps_json = json.dumps(
            {"abertos": [], "em_foco": {"nome_app": "desconhecido", "titulo_janela": ""}},
            ensure_ascii=False,
        )

        self._banco.executar(
            """
            INSERT INTO usuarios_status_atual
                (user_id, situacao, atividade, inicio_em, ultimo_em, segundos_pausado, apps_json)
            VALUES (%s, %s, %s, NULL, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                situacao = VALUES(situacao),
                atividade = VALUES(atividade),
                inicio_em = NULL,
                ultimo_em = VALUES(ultimo_em),
                segundos_pausado = VALUES(segundos_pausado),
                apps_json = VALUES(apps_json)
            """,
            [self._user_id, "pausado", "", datetime.now(), 0, apps_json],
        )

    def _salvar_estado_local_locked(self, sessao_em_aberto: bool) -> None:
        estado = self._snapshot_locked()

        dados = {
            "sessao_em_aberto": bool(sessao_em_aberto),
            "id_sessao": self._id_sessao,
            "token_sessao": self._token_sessao,
            "user_id": self._user_id,
            "nome_exibicao": self._nome_exibicao,
            "id_atividade": self._id_atividade,
            "titulo_atividade": self._titulo_atividade,
            "situacao_manual": self._situacao_manual,
            "situacao_calculada": self._situacao_calculada,
            "segundos_trabalhando": float(estado.segundos_trabalhando),
            "segundos_ocioso": float(estado.segundos_ocioso),
            "segundos_pausado": float(estado.segundos_pausado),
            "versao_app": VERSAO_APLICACAO,
            "salvo_em": datetime.now().isoformat(),
        }

        try:
            ARQUIVO_ESTADO_SESSAO.write_text(
                json.dumps(dados, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _limpar_estado_local(self) -> None:
        try:
            if ARQUIVO_ESTADO_SESSAO.exists():
                ARQUIVO_ESTADO_SESSAO.unlink()
        except Exception:
            pass

    def _carregar_estado_local(self) -> dict | None:
        try:
            if not ARQUIVO_ESTADO_SESSAO.exists():
                return None
            return json.loads(ARQUIVO_ESTADO_SESSAO.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _sessao_do_banco_esta_aberta(self, id_sessao: int, token_sessao: str, user_id: str) -> bool:
        linha = self._banco.consultar_um(
            """
            SELECT id_sessao
            FROM cronometro_sessoes
            WHERE id_sessao = %s
              AND token_sessao = %s
              AND user_id = %s
              AND finalizado_em IS NULL
            LIMIT 1
            """,
            [int(id_sessao), str(token_sessao), str(user_id)],
        )
        return bool(linha)

    def obter_dados_sessao_pendente_do_usuario(self, user_id: str) -> dict | None:
        dados = self._carregar_estado_local()
        if not dados:
            return None

        if str(dados.get("user_id") or "").strip() != (user_id or "").strip():
            return None

        if not bool(dados.get("sessao_em_aberto")):
            return None

        id_sessao = int(dados.get("id_sessao") or 0)
        token_sessao = str(dados.get("token_sessao") or "").strip()
        if id_sessao <= 0 or not token_sessao:
            return None

        try:
            if not self._sessao_do_banco_esta_aberta(id_sessao, token_sessao, user_id):
                return None
        except Exception:
            return None

        return dados

    def restaurar_sessao(self, dados: dict, nome_exibicao_atual: str) -> None:
        # Fecha registros antigos pendurados antes de restaurar — evita lixo legado nos gráficos.
        self._sanear_registros_abertos_do_usuario(str(dados.get("user_id") or "").strip())
        with self._trava:
            if self._thread_loop and self._thread_loop.is_alive():
                raise RuntimeError("Já existe uma sessão em execução.")

            self._id_sessao = int(dados.get("id_sessao") or 0)
            self._token_sessao = str(dados.get("token_sessao") or "").strip()
            self._referencia_data_sessao = date.today()
            self._user_id = str(dados.get("user_id") or "").strip()
            self._nome_exibicao = (nome_exibicao_atual or "").strip() or str(dados.get("nome_exibicao") or "").strip()
            self._id_atividade = int(dados.get("id_atividade") or 0)
            self._titulo_atividade = str(dados.get("titulo_atividade") or "").strip()

            self._segundos_trabalhando_float = float(dados.get("segundos_trabalhando") or 0.0)
            self._segundos_ocioso_float = float(dados.get("segundos_ocioso") or 0.0)
            self._segundos_pausado_float = float(dados.get("segundos_pausado") or 0.0)

            self._sessao_carregada = True
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"

            self._nome_app_foco = "desconhecido"
            self._titulo_janela_foco = ""
            self._id_foco_aberto = None
            self._segundos_em_foco_atual = 0
            self._mono_ultimo_acumulo_foco = 0.0
            self._mono_ultimo_flush_foco = 0.0

            self._mapa_intervalos_apps = {}
            self._ultimo_scan_apps_mono = 0.0

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora
            self._ultimo_upsert_relatorio_mono = agora
            self._ultimo_erro = ""

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()

    def iniciar(self, user_id: str, nome_exibicao: str, id_atividade: int, titulo_atividade: str) -> None:
        LOG_TEC.log("sessao", "iniciar()", {
            "user_id": user_id, "id_atividade": id_atividade, "titulo": titulo_atividade,
        })
        # Fecha registros antigos pendurados antes de abrir novos — evita lixo legado nos gráficos.
        self._sanear_registros_abertos_do_usuario(user_id)
        with self._trava:
            if self._sessao_carregada:
                raise RuntimeError("Já existe uma sessão carregada. Finalize ou retome a atual.")

            self._user_id = (user_id or "").strip()
            self._nome_exibicao = (nome_exibicao or "").strip()
            self._id_atividade = int(id_atividade)
            self._titulo_atividade = (titulo_atividade or "").strip()

            self._segundos_trabalhando_float = 0.0
            self._segundos_ocioso_float = 0.0
            self._segundos_pausado_float = 0.0

            self._sessao_carregada = True
            self._rodando = True
            self._situacao_manual = "rodando"
            self._situacao_calculada = "trabalhando"

            self._token_sessao = uuid.uuid4().hex

            maquina = socket.gethostname()
            sistema = f"{platform.system()} {platform.release()}"

            self._id_sessao = self._banco.executar(
                """
                INSERT INTO cronometro_sessoes
                    (user_id, token_sessao, maquina_nome, sistema, versao_app, iniciado_em, finalizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, NULL)
                """,
                [self._user_id, self._token_sessao, maquina, sistema, VERSAO_APLICACAO, datetime.now()],
            )
            self._referencia_data_sessao = date.today()

            self._mapa_intervalos_apps = {}
            self._ultimo_scan_apps_mono = 0.0

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora
            self._ultimo_upsert_relatorio_mono = agora
            self._ultimo_erro = ""

            self._inserir_evento("inicio", "trabalhando", 0)

            nome, titulo = obter_aplicativo_em_foco()
            self._nome_app_foco = nome
            self._titulo_janela_foco = titulo
            self._abrir_foco(nome, titulo)

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()

            self._parar = threading.Event()
            self._thread_loop = threading.Thread(target=self._loop, daemon=True)
            self._thread_loop.start()

        # Fase 2: inicia detector de input sintético em paralelo (fora do lock)
        try:
            self._detector_input.iniciar()
        except Exception as e:
            LOG_TEC.log("detector_input", "falha ao iniciar", {"erro": str(e)})

    def pausar(self) -> None:
        LOG_TEC.log("sessao", "pausar()")
        with self._trava:
            if not self._sessao_carregada:
                return
            if not self._rodando or self._situacao_manual == "pausado":
                return
            # Impedir pausa enquanto estiver ocioso — evita que o editor
            # esconda tempo ocioso reclassificando como "pausado"
            if self._situacao_calculada == "ocioso":
                return

            self._acumular_tempo_ate_agora_locked(time.monotonic())
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"

            try:
                self._fechar_foco()
            except Exception:
                pass

            try:
                self._fechar_todos_intervalos_apps_locked()
            except Exception:
                pass

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()
            _id_snap = self._id_sessao
            _uid_snap = self._user_id

        try:
            self._inserir_evento("pausa", "pausado", 0, _id_snap, _uid_snap)
        except Exception:
            pass

        # Persiste totais parciais imediatamente ao pausar — o painel web passa a enxergar o bloco concluído.
        try:
            self._upsert_relatorio_parcial()
        except Exception:
            pass

    def retomar(self) -> None:
        LOG_TEC.log("sessao", "retomar()")
        with self._trava:
            if not self._sessao_carregada:
                return
            if self._rodando:
                return

            self._rodando = True
            self._situacao_manual = "rodando"
            self._situacao_calculada = "trabalhando"

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora

            nome, titulo = obter_aplicativo_em_foco()
            self._nome_app_foco = nome
            self._titulo_janela_foco = titulo

            try:
                self._abrir_foco(nome, titulo)
            except Exception:
                pass

            if not self._thread_loop or not self._thread_loop.is_alive():
                self._parar = threading.Event()
                self._thread_loop = threading.Thread(target=self._loop, daemon=True)
                self._thread_loop.start()

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()
            _id_snap = self._id_sessao
            _uid_snap = self._user_id

        # Fase 2: detector de input sintético foi iniciado em iniciar() e
        # permanece ativo durante toda a vida da app. Snapshot só ocorre no
        # heartbeat que só dispara com _rodando=True, então pausa/retorno
        # não precisa mexer nele.

        try:
            self._inserir_evento("retorno", "trabalhando", 0, _id_snap, _uid_snap)
        except Exception:
            pass

    def pausar_e_preservar_sessao(self) -> None:
        self.pausar()

    # -------------------- Relatório parcial (upsert) --------------------
    def _upsert_relatorio_com_snapshots(
        self,
        id_sessao: int,
        user_id: str,
        id_atividade: int,
        seg_trab_float: float,
        seg_oci_float: float,
        seg_pau_float: float,
        ref_data_fallback: date,
        texto_relatorio: str,
        com_fechamento: bool,
    ) -> None:
        """Grava/atualiza `cronometro_relatorios` por (id_sessao, referencia_data).
        Usa SELECT + UPDATE/INSERT para não depender de UNIQUE KEY (evita ALTER no banco).
        Divide totais por dia quando a sessão cruza meia-noite.
        """
        if id_sessao is None or not user_id:
            return
        try:
            fim_em_agora = datetime.now()
            inicio_em = None
            try:
                linha_sessao = self._banco.consultar_um(
                    "SELECT iniciado_em FROM cronometro_sessoes WHERE id_sessao = %s LIMIT 1",
                    [id_sessao],
                )
                if linha_sessao and linha_sessao.get("iniciado_em"):
                    inicio_em = linha_sessao["iniciado_em"]
            except Exception:
                inicio_em = None
            if not isinstance(inicio_em, datetime):
                inicio_em = datetime.combine(ref_data_fallback, datetime.min.time())

            fatias = dividir_tempos_por_dia(
                inicio_em,
                fim_em_agora,
                converter_segundos_para_inteiro(seg_trab_float),
                converter_segundos_para_inteiro(seg_oci_float),
                converter_segundos_para_inteiro(seg_pau_float),
            )

            texto_efetivo = (texto_relatorio or "").strip() or "Sessão em andamento (parcial)"

            for dia, seg_trab_dia, seg_oci_dia, seg_pau_dia in fatias:
                segundos_total_dia = seg_trab_dia + seg_oci_dia
                existente = None
                try:
                    existente = self._banco.consultar_um(
                        "SELECT id_relatorio FROM cronometro_relatorios WHERE id_sessao = %s AND referencia_data = %s LIMIT 1",
                        [id_sessao, dia],
                    )
                except Exception:
                    existente = None

                if existente and existente.get("id_relatorio"):
                    self._banco.executar(
                        """
                        UPDATE cronometro_relatorios
                           SET id_atividade = %s,
                               relatorio = %s,
                               segundos_total = %s,
                               segundos_trabalhando = %s,
                               segundos_ocioso = %s,
                               segundos_pausado = %s,
                               criado_em = %s
                         WHERE id_relatorio = %s
                        """,
                        [
                            int(id_atividade) if id_atividade else None,
                            texto_efetivo,
                            int(segundos_total_dia),
                            int(seg_trab_dia),
                            int(seg_oci_dia),
                            int(seg_pau_dia),
                            fim_em_agora,
                            int(existente["id_relatorio"]),
                        ],
                    )
                    LOG_TEC.log("relatorio", f"UPDATE dia={dia}", {
                        "id_relatorio": existente["id_relatorio"],
                        "trab": seg_trab_dia, "oci": seg_oci_dia, "pau": seg_pau_dia,
                        "fechamento": com_fechamento,
                    })
                else:
                    self._banco.executar(
                        """
                        INSERT INTO cronometro_relatorios
                            (id_sessao, user_id, id_atividade, relatorio, segundos_total,
                             segundos_trabalhando, segundos_ocioso, segundos_pausado, criado_em, referencia_data)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            id_sessao,
                            user_id,
                            int(id_atividade) if id_atividade else None,
                            texto_efetivo,
                            int(segundos_total_dia),
                            int(seg_trab_dia),
                            int(seg_oci_dia),
                            int(seg_pau_dia),
                            fim_em_agora,
                            dia,
                        ],
                    )
                    LOG_TEC.log("relatorio", f"INSERT dia={dia}", {
                        "trab": seg_trab_dia, "oci": seg_oci_dia, "pau": seg_pau_dia,
                        "fechamento": com_fechamento,
                    })
        except Exception as erro:
            LOG_TEC.log("relatorio_erro", "upsert falhou", {"erro": str(erro)})

    def _upsert_relatorio_parcial(self) -> None:
        """Wrapper do upsert que coleta snapshots do state atual sob lock e chama o worker fora.
        Atualiza acumuladores com `_acumular_tempo_ate_agora_locked` antes do snapshot.
        """
        with self._trava:
            if self._id_sessao is None or not self._user_id:
                return
            self._acumular_tempo_ate_agora_locked(time.monotonic())
            id_sessao_snap = self._id_sessao
            user_id_snap = self._user_id
            id_ativ_snap = int(self._id_atividade) if self._id_atividade else 0
            seg_trab_snap = self._segundos_trabalhando_float
            seg_oci_snap = self._segundos_ocioso_float
            seg_pau_snap = self._segundos_pausado_float
            ref_data_snap = self._referencia_data_sessao or date.today()

        self._upsert_relatorio_com_snapshots(
            id_sessao_snap, user_id_snap, id_ativ_snap,
            seg_trab_snap, seg_oci_snap, seg_pau_snap,
            ref_data_snap, texto_relatorio="", com_fechamento=False,
        )

    def zerar_sessao(self) -> None:
        """Para o cronômetro, salva relatório da sessão zerada e descarta o estado local."""
        LOG_TEC.log("sessao", "zerar_sessao()")
        with self._trava:
            if not self._sessao_carregada or self._id_sessao is None:
                return

            self._acumular_tempo_ate_agora_locked(time.monotonic())
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"
            self._inicio_sessao_cache = None

            try:
                self._fechar_foco()
            except Exception:
                pass

            try:
                self._fechar_todos_intervalos_apps_locked()
            except Exception:
                pass

            # Capturar snapshots dentro do lock antes de zerar
            _id_snap = self._id_sessao
            _uid_snap = self._user_id
            _id_ativ_snap = self._id_atividade
            _seg_trab_snap = self._segundos_trabalhando_float
            _seg_ocio_snap = self._segundos_ocioso_float
            _seg_paus_snap = self._segundos_pausado_float
            _ref_data_snap = self._referencia_data_sessao or date.today()

            self._sessao_carregada = False
            self._segundos_trabalhando_float = 0.0
            self._segundos_ocioso_float = 0.0
            self._segundos_pausado_float = 0.0
            self._ultimo_marco_mono = 0.0
            self._parar.set()
            self._limpar_estado_local()

        try:
            self._inserir_evento("zerar", "pausado", 0, _id_snap, _uid_snap)
        except Exception as e:
            print(f"[zerar_sessao] Falha ao gravar evento 'zerar': {e}")

        try:
            self._banco.executar(
                "UPDATE cronometro_sessoes SET finalizado_em = %s WHERE id_sessao = %s",
                [datetime.now(), _id_snap],
            )
        except Exception:
            pass

        # Consolida na mesma linha parcial já criada ao longo da sessão (ou insere se não existir).
        # Sessões que cruzam meia-noite continuam sendo divididas em múltiplas linhas por referencia_data.
        try:
            self._upsert_relatorio_com_snapshots(
                _id_snap, _uid_snap, int(_id_ativ_snap) if _id_ativ_snap else 0,
                _seg_trab_snap, _seg_ocio_snap, _seg_paus_snap,
                _ref_data_snap, texto_relatorio="Sessão zerada", com_fechamento=True,
            )
        except Exception:
            pass

        try:
            self._limpar_status_atual()
        except Exception:
            pass

    def finalizar(self, relatorio: str) -> None:
        LOG_TEC.log("sessao", "finalizar()", {"relatorio_tam": len(relatorio or "")})
        with self._trava:
            if not self._sessao_carregada or self._id_sessao is None or not self._user_id:
                raise RuntimeError("Você precisa clicar em INICIAR antes de FINALIZAR.")

            self._acumular_tempo_ate_agora_locked(time.monotonic())
            self._rodando = False
            self._situacao_manual = "pausado"
            self._situacao_calculada = "pausado"
            self._inicio_sessao_cache = None

            try:
                self._fechar_foco()
            except Exception:
                pass

            try:
                self._fechar_todos_intervalos_apps_locked()
            except Exception:
                pass

        try:
            self._inserir_evento("finalizar", "pausado", 0)
        except Exception:
            pass

        try:
            self._banco.executar(
                "UPDATE cronometro_sessoes SET finalizado_em = %s WHERE id_sessao = %s",
                [datetime.now(), self._id_sessao],
            )
        except Exception:
            pass

        # Consolida na mesma linha parcial já criada ao longo da sessão (ou insere se não existir).
        # Sessões que cruzam meia-noite continuam sendo divididas em múltiplas linhas por referencia_data.
        ref_data_fallback = self._referencia_data_sessao or date.today()
        texto_relatorio = (relatorio or "").strip()
        try:
            self._upsert_relatorio_com_snapshots(
                self._id_sessao, self._user_id, int(self._id_atividade),
                self._segundos_trabalhando_float, self._segundos_ocioso_float, self._segundos_pausado_float,
                ref_data_fallback, texto_relatorio=texto_relatorio, com_fechamento=True,
            )
        except Exception:
            pass

        with self._trava:
            self._sessao_carregada = False
            self._parar.set()
            self._limpar_estado_local()

        try:
            self._limpar_status_atual()
        except Exception:
            pass

    def _loop(self) -> None:
        try:
            ultimo_foco = ("", "")

            while not self._parar.is_set():
                time.sleep(INTERVALO_LOOP_SEGUNDOS)
                mono_agora = time.monotonic()

                try:
                    idle = obter_segundos_ocioso_windows()
                    nome_foco, titulo_foco = obter_aplicativo_em_foco()
                except Exception as e:
                    with self._trava:
                        self._registrar_erro_locked(f"Falha foco/idle: {e}")
                    continue

                # Scan de apps visíveis a cada INTERVALO_SCAN_APPS_SEGUNDOS (fora da lock — pode ser lento)
                apps_visiveis_scan: set[str] | None = None
                delta_scan = 0
                if (mono_agora - self._ultimo_scan_apps_mono) >= INTERVALO_SCAN_APPS_SEGUNDOS:
                    try:
                        apps_visiveis_scan = listar_nomes_apps_visiveis()
                    except Exception:
                        apps_visiveis_scan = set()
                    delta_scan = max(1, int(mono_agora - self._ultimo_scan_apps_mono)) if self._ultimo_scan_apps_mono > 0 else int(INTERVALO_SCAN_APPS_SEGUNDOS)
                    self._ultimo_scan_apps_mono = mono_agora

                # Flags para operações de banco — decididas dentro do lock,
                # executadas FORA para não bloquear Pausar/Retomar/Iniciar
                _foco_mudou       = False
                _evt_situacao: tuple | None = None
                _fazer_heartbeat  = False
                _hb_situacao      = ""
                _hb_idle          = 0
                _fazer_flush      = False
                _fazer_status     = False
                _salvar_local     = False
                _fazer_upsert_relatorio = False

                try:
                    with self._trava:
                        if not self._sessao_carregada:
                            continue
                        if not self._rodando:
                            continue

                        # ── Atualização de estado puro (sem banco) ──────────
                        situacao_anterior = self._situacao_calculada
                        nova_situacao = "ocioso" if idle >= LIMITE_OCIOSO_SEGUNDOS else "trabalhando"
                        self._situacao_calculada = nova_situacao
                        self._acumular_tempo_ate_agora_locked(mono_agora)
                        # Acumula segundos do foco atual em memória (UPDATE no banco vai
                        # acontecer fora do lock via _flush_foco_periodico).
                        self._acumular_foco_locked(mono_agora)
                        self._nome_app_foco = nome_foco
                        self._titulo_janela_foco = titulo_foco
                        foco_atual = (nome_foco, titulo_foco)

                        # ── Marcar o que precisa ir ao banco ─────────────────
                        if foco_atual != ultimo_foco:
                            _foco_mudou = True

                        if situacao_anterior != nova_situacao:
                            if situacao_anterior == "trabalhando" and nova_situacao == "ocioso":
                                _evt_situacao = ("ocioso_inicio", "ocioso", idle)
                            elif situacao_anterior == "ocioso" and nova_situacao == "trabalhando":
                                _evt_situacao = ("ocioso_fim", "trabalhando", idle)

                        if (mono_agora - self._ultimo_heartbeat_mono) >= INTERVALO_HEARTBEAT_SEGUNDOS:
                            self._ultimo_heartbeat_mono = mono_agora
                            _fazer_heartbeat = True
                            _fazer_flush     = True
                            _hb_situacao     = self._situacao_calculada
                            _hb_idle         = idle

                        if (mono_agora - self._ultimo_sync_status_mono) >= INTERVALO_STATUS_BANCO_SEGUNDOS:
                            self._ultimo_sync_status_mono = mono_agora
                            _fazer_status = True

                        if (mono_agora - self._ultimo_save_estado_mono) >= 10.0:
                            self._ultimo_save_estado_mono = mono_agora
                            _salvar_local = True

                        if (mono_agora - self._ultimo_upsert_relatorio_mono) >= INTERVALO_UPSERT_RELATORIO_SEGUNDOS:
                            self._ultimo_upsert_relatorio_mono = mono_agora
                            _fazer_upsert_relatorio = True

                except Exception as e:
                    with self._trava:
                        self._registrar_erro_locked(f"Falha loop: {e}")

                # ── Operações de banco FORA do lock ──────────────────────────

                if _salvar_local:
                    try:
                        with self._trava:
                            self._salvar_estado_local_locked(sessao_em_aberto=True)
                    except Exception:
                        pass

                if _foco_mudou:
                    try:
                        self._fechar_foco()
                    except Exception:
                        pass
                    try:
                        self._abrir_foco(nome_foco, titulo_foco)
                    except Exception:
                        pass
                    ultimo_foco = foco_atual
                else:
                    # Foco não mudou — flush periódico do contador cumulativo
                    # mantém segundos_em_foco em dia no banco mesmo sem troca,
                    # de modo que crash/kill não deixe registro com fim_em NULL
                    # e duração correta. Mesmo intervalo do scan de apps (10s).
                    try:
                        self._flush_foco_periodico(mono_agora, INTERVALO_SCAN_APPS_SEGUNDOS)
                    except Exception:
                        pass

                if apps_visiveis_scan is not None:
                    try:
                        self._atualizar_intervalos_apps_locked(apps_visiveis_scan, delta_scan)
                    except Exception as e:
                        with self._trava:
                            self._registrar_erro_locked(f"Falha scan apps: {e}")

                if _evt_situacao:
                    try:
                        self._inserir_evento(*_evt_situacao)
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", f"inserir_evento falhou: {_evt_situacao[0]}", {
                            "operacao": "inserir_evento",
                            "tipo_evento": _evt_situacao[0],
                            "situacao": _evt_situacao[1] if len(_evt_situacao) > 1 else None,
                            "erro": str(e),
                            "offline_antes": self._offline_notificado,
                        })
                        self._adicionar_a_fila_offline(*_evt_situacao)

                if _fazer_flush:
                    try:
                        self._tentar_flush_fila_offline()
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", "flush_fila_offline falhou", {
                            "operacao": "flush_fila_offline",
                            "erro": str(e),
                        })

                if _fazer_heartbeat:
                    try:
                        self._inserir_evento("heartbeat", _hb_situacao, _hb_idle)
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", "heartbeat falhou", {
                            "operacao": "heartbeat",
                            "situacao": _hb_situacao,
                            "idle": _hb_idle,
                            "erro": str(e),
                            "entrou_offline": not self._offline_notificado,
                        })
                        with self._trava:
                            self._registrar_erro_locked(f"Falha heartbeat: {e}")
                            if not self._offline_notificado:
                                self._offline_notificado = True
                                self._notificar_sem_conexao()
                        self._adicionar_a_fila_offline("heartbeat", _hb_situacao, _hb_idle)

                    # Fase 2: flush do detector de input sintético (junto do heartbeat)
                    try:
                        self._flush_input_stats_locked_free()
                    except Exception as e:
                        LOG_TEC.log("detector_input", "flush falhou", {"erro": str(e)})

                if _fazer_status:
                    try:
                        estava_offline = self._offline_notificado
                        self._atualizar_status_atual_locked()
                        with self._trava:
                            if self._offline_notificado:
                                self._offline_notificado = False
                                self._registrar_erro_locked("")
                        if estava_offline:
                            LOG_TEC.log("status_restaurado", "usuarios_status_atual voltou a aceitar upsert", {
                                "operacao": "atualizar_status_atual",
                            })
                    except Exception as e:
                        LOG_TEC.log("conexao_erro", "status_atual falhou", {
                            "operacao": "atualizar_status_atual",
                            "erro": str(e),
                            "entrou_offline": not self._offline_notificado,
                        })
                        with self._trava:
                            self._registrar_erro_locked(f"Falha status atual: {e}")
                            if not self._offline_notificado:
                                self._offline_notificado = True
                                self._notificar_sem_conexao()

                if _fazer_upsert_relatorio:
                    try:
                        self._upsert_relatorio_parcial()
                    except Exception:
                        pass

        finally:
            try:
                self._banco.fechar_conexao_da_thread()
            except Exception:
                pass



from collections.abc import Callable


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
        subtarefa = self._mapa_subtarefas.get(int(id_subtarefa)) if id_subtarefa else None

        janela = tk.Toplevel(self)
        janela.title("Declarar Tarefa")
        janela.geometry("700x460")
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
            caminho = Path(__file__).parent / "logo.png"
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


if __name__ == "__main__":
    App().mainloop()
