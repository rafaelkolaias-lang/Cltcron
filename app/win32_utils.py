"""Utilitários Windows + helpers de tempo/conversão usados pelo monitor."""
from __future__ import annotations

import ctypes
import time
from ctypes import wintypes
from datetime import date, datetime, timedelta

import psutil

from app.config import CAPTURAR_TITULO_JANELA

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
