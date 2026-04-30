"""Detector de input sintético (auto-clickers / macros).

Usa hooks low-level do Windows (WH_MOUSE_LL + WH_KEYBOARD_LL) para ler a flag
LLMHF_INJECTED / LLKHF_INJECTED em cada evento. Eventos com essa flag foram
gerados por software (mouse_event, SendInput, keybd_event), não por hardware
físico. Acumula dois contadores independentes em "buckets de segundo":
cada segundo do relógio em que houve ao menos 1 evento humano conta como 1
segundo de "input humano". Idem para sintético. Se o mesmo segundo tiver
os dois, vai para "misto" (contabilizado como humano — cenário raro).

Thread-safe: callbacks do hook rodam numa thread dedicada com message loop;
o MonitorDeUso lê snapshots via uma lock interna.
"""
from __future__ import annotations

import ctypes
import threading
import time
from ctypes import wintypes

from app.config import LOG_TEC

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
