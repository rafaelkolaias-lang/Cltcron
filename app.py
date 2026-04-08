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
from datetime import date, datetime
from pathlib import Path
from tkinter import messagebox, ttk

import psutil

from atividades import RepositorioAtividades
from banco import BancoDados
from declaracoes_dia import RepositorioDeclaracoesDia

# =========================
# CONFIGURAÇÕES
# =========================
VERSAO_APLICACAO = "v2.2"
URL_ATUALIZACAO = "https://raw.githubusercontent.com/rafaelkolaias-lang/Cltcron/main/painel/downloads/CronometroLeve.exe"

INTERVALO_LOOP_SEGUNDOS = 0.20
INTERVALO_UI_MILISSEGUNDOS = 80
INTERVALO_HEARTBEAT_SEGUNDOS = 60.0
INTERVALO_STATUS_BANCO_SEGUNDOS = 5.0

LIMITE_OCIOSO_SEGUNDOS = 5 * 60

CAPTURAR_TITULO_JANELA = False

INTERVALO_SCAN_APPS_SEGUNDOS = 15.0

ARQUIVO_LOGIN_SALVO = Path.home() / ".cronometro_leve_login.json"
ARQUIVO_ESTADO_SESSAO = Path.home() / ".cronometro_leve_estado.json"
ARQUIVO_FILA_OFFLINE = Path.home() / ".cronometro_leve_fila_offline.json"

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


@dataclass
class EstadoMonitor:
    rodando: bool
    situacao: str
    segundos_trabalhando: int
    segundos_ocioso: int
    segundos_pausado: int
    ultimo_erro: str


class MonitorDeUso:
    def __init__(self, banco: BancoDados) -> None:
        self._banco = banco
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._thread_loop: threading.Thread | None = None

        self._id_sessao: int | None = None
        self._token_sessao: str = ""

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

        self._ultimo_heartbeat_mono: float = 0.0
        self._ultimo_sync_status_mono: float = 0.0
        self._ultimo_flush_fila_mono: float = 0.0
        self._ultimo_marco_mono: float = 0.0
        self._ultimo_erro: str = ""
        self._offline_notificado: bool = False

        self._mapa_intervalos_apps: dict[str, dict] = {}
        self._ultimo_scan_apps_mono: float = 0.0
        self._ultimo_save_estado_mono: float = 0.0
        self._inicio_sessao_cache: datetime | None = None

    def _registrar_erro_locked(self, mensagem: str) -> None:
        self._ultimo_erro = (mensagem or "").strip()[:240]

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

        return EstadoMonitor(
            rodando=self._rodando,
            situacao=self._situacao_calculada,
            segundos_trabalhando=converter_segundos_para_inteiro(trabalhando),
            segundos_ocioso=converter_segundos_para_inteiro(ocioso),
            segundos_pausado=converter_segundos_para_inteiro(pausado),
            ultimo_erro=self._ultimo_erro,
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
                self._segundos_trabalhando_float += delta

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

        self._banco.executar(
            """
            INSERT INTO cronometro_eventos_status
                (id_sessao, user_id, tipo_evento, situacao, ocorrido_em, idle_segundos)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            [_id, _uid, tipo_evento, situacao, ocorrido_em or datetime.now(), int(idle_segundos)],
        )

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
        fila.append({
            "tipo_evento": tipo_evento,
            "situacao": situacao,
            "idle_segundos": idle_segundos,
            "id_sessao": self._id_sessao,
            "user_id": self._user_id,
            "ocorrido_em": (ocorrido_em or datetime.now()).isoformat(),
        })
        self._salvar_fila_offline(fila)

    def _tentar_flush_fila_offline(self) -> None:
        """Re-envia eventos pendentes da fila offline. Para ao primeiro erro."""
        fila = self._carregar_fila_offline()
        if not fila:
            return
        enviados = 0
        for item in fila:
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
                enviados += 1
            except Exception:
                break
        if enviados > 0:
            self._salvar_fila_offline(fila[enviados:])
            pendentes = len(fila) - enviados
            if pendentes == 0 and self._offline_notificado:
                self._offline_notificado = False
                self._notificar_conexao_restaurada(enviados)
            msg = (
                f"Fila offline: {enviados} eventos re-enviados"
                + (f", {pendentes} ainda pendentes" if pendentes else " (fila limpa)")
            )
            self._registrar_erro_locked(msg)

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

    def _abrir_foco(self, nome_app: str, titulo: str) -> None:
        if self._id_sessao is None:
            return

        self._id_foco_aberto = self._banco.executar(
            """
            INSERT INTO cronometro_foco_janela
                (id_sessao, user_id, nome_app, titulo_janela, inicio_em, fim_em)
            VALUES (%s, %s, %s, %s, %s, NULL)
            """,
            [self._id_sessao, self._user_id, nome_app, (titulo or None), datetime.now()],
        )

    def _fechar_foco(self) -> None:
        if self._id_foco_aberto is None:
            return

        self._banco.executar(
            "UPDATE cronometro_foco_janela SET fim_em = %s WHERE id_foco = %s",
            [datetime.now(), self._id_foco_aberto],
        )
        self._id_foco_aberto = None

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
        payload = {
            "abertos": [],
            "em_foco": {
                "nome_app": self._nome_app_foco or "desconhecido",
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
        with self._trava:
            if self._thread_loop and self._thread_loop.is_alive():
                raise RuntimeError("Já existe uma sessão em execução.")

            self._id_sessao = int(dados.get("id_sessao") or 0)
            self._token_sessao = str(dados.get("token_sessao") or "").strip()
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

            self._mapa_intervalos_apps = {}
            self._ultimo_scan_apps_mono = 0.0

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora
            self._ultimo_erro = ""

            self._salvar_estado_local_locked(sessao_em_aberto=True)
            self._atualizar_status_atual_locked()

    def iniciar(self, user_id: str, nome_exibicao: str, id_atividade: int, titulo_atividade: str) -> None:
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

            self._mapa_intervalos_apps = {}
            self._ultimo_scan_apps_mono = 0.0

            agora = time.monotonic()
            self._ultimo_marco_mono = agora
            self._ultimo_heartbeat_mono = agora
            self._ultimo_sync_status_mono = agora
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

    def pausar(self) -> None:
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

    def retomar(self) -> None:
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

        try:
            self._inserir_evento("retorno", "trabalhando", 0, _id_snap, _uid_snap)
        except Exception:
            pass

    def pausar_e_preservar_sessao(self) -> None:
        self.pausar()

    def zerar_sessao(self) -> None:
        """Para o cronômetro, salva relatório da sessão zerada e descarta o estado local."""
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

            self._sessao_carregada = False
            self._segundos_trabalhando_float = 0.0
            self._segundos_ocioso_float = 0.0
            self._segundos_pausado_float = 0.0
            self._ultimo_marco_mono = 0.0
            self._parar.set()
            self._limpar_estado_local()

        try:
            self._inserir_evento("zerar", "pausado", 0, _id_snap, _uid_snap)
        except Exception:
            pass

        try:
            self._banco.executar(
                "UPDATE cronometro_sessoes SET finalizado_em = %s WHERE id_sessao = %s",
                [datetime.now(), _id_snap],
            )
        except Exception:
            pass

        # Inserir relatório para que o tempo fique disponível para declaração de tarefas
        try:
            segundos_total = converter_segundos_para_inteiro(
                _seg_trab_snap + _seg_ocio_snap
            )
            self._banco.executar(
                """
                INSERT INTO cronometro_relatorios
                    (id_sessao, user_id, id_atividade, relatorio, segundos_total,
                     segundos_trabalhando, segundos_ocioso, segundos_pausado, criado_em)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    _id_snap,
                    _uid_snap,
                    int(_id_ativ_snap) if _id_ativ_snap else None,
                    "Sessão zerada",
                    int(segundos_total),
                    converter_segundos_para_inteiro(_seg_trab_snap),
                    converter_segundos_para_inteiro(_seg_ocio_snap),
                    converter_segundos_para_inteiro(_seg_paus_snap),
                    datetime.now(),
                ],
            )
        except Exception:
            pass

        try:
            self._limpar_status_atual()
        except Exception:
            pass

    def finalizar(self, relatorio: str) -> None:
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

        segundos_total = converter_segundos_para_inteiro(
            self._segundos_trabalhando_float + self._segundos_ocioso_float
        )

        self._banco.executar(
            """
            INSERT INTO cronometro_relatorios
                (id_sessao, user_id, id_atividade, relatorio, segundos_total,
                 segundos_trabalhando, segundos_ocioso, segundos_pausado, criado_em)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                self._id_sessao,
                self._user_id,
                int(self._id_atividade),
                (relatorio or "").strip(),
                int(segundos_total),
                converter_segundos_para_inteiro(self._segundos_trabalhando_float),
                converter_segundos_para_inteiro(self._segundos_ocioso_float),
                converter_segundos_para_inteiro(self._segundos_pausado_float),
                datetime.now(),
            ],
        )

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

                if apps_visiveis_scan is not None:
                    try:
                        self._atualizar_intervalos_apps_locked(apps_visiveis_scan, delta_scan)
                    except Exception as e:
                        with self._trava:
                            self._registrar_erro_locked(f"Falha scan apps: {e}")

                if _evt_situacao:
                    try:
                        self._inserir_evento(*_evt_situacao)
                    except Exception:
                        self._adicionar_a_fila_offline(*_evt_situacao)

                if _fazer_flush:
                    try:
                        self._tentar_flush_fila_offline()
                    except Exception:
                        pass

                if _fazer_heartbeat:
                    try:
                        self._inserir_evento("heartbeat", _hb_situacao, _hb_idle)
                    except Exception as e:
                        with self._trava:
                            self._registrar_erro_locked(f"Falha heartbeat: {e}")
                            if not self._offline_notificado:
                                self._offline_notificado = True
                                self._notificar_sem_conexao()
                        self._adicionar_a_fila_offline("heartbeat", _hb_situacao, _hb_idle)

                if _fazer_status:
                    try:
                        self._atualizar_status_atual_locked()
                        with self._trava:
                            if self._offline_notificado:
                                self._offline_notificado = False
                                self._registrar_erro_locked("")
                    except Exception as e:
                        with self._trava:
                            self._registrar_erro_locked(f"Falha status atual: {e}")
                            if not self._offline_notificado:
                                self._offline_notificado = True
                                self._notificar_sem_conexao()

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
        self.title("Tarefas do dia")
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

        self._var_resumo = tk.StringVar(value="")
        self._var_trava = tk.StringVar(value="Carregando...")

        self._montar_tela()
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
                "Cadastre as subtarefas executadas nesta atividade principal. "
                "Preencha o Tempo gasto no formulário para salvar como Concluída. "
                "Depois do pagamento, a data fica travada e não pode mais editar nem excluir."
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
        self._arvore.heading("titulo", text="Subtarefa")
        self._arvore.heading("canal", text="Canal")
        self._arvore.heading("status", text="Status")
        self._arvore.heading("data", text="Data")
        self._arvore.heading("tempo", text="Tempo")
        self._arvore.heading("observacao", text="Observação")
        self._arvore.heading("bloqueio", text="Pagamento")

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

            # Mesclar subtarefas e pagamentos ordenados por data desc
            # Cada item: (data, tipo_ordem, iid, valores, tags)
            # tipo_ordem: 0=pagamento (aparece acima), 1=subtarefa
            itens_mesclados: list[tuple[date | None, int, str, tuple, tuple]] = []

            for subtarefa in subtarefas:
                id_sub = int(getattr(subtarefa, "id_subtarefa", 0))
                ref = getattr(subtarefa, "referencia_data", None)
                itens_mesclados.append((
                    ref if isinstance(ref, date) else None,
                    1,
                    f"subtarefa_{id_sub}",
                    (
                        str(getattr(subtarefa, "titulo", "") or ""),
                        str(getattr(subtarefa, "canal_entrega", "") or ""),
                        "Concluída" if bool(getattr(subtarefa, "concluida", False)) else "Aberta",
                        self._formatar_data(ref),
                        formatar_hhmmss(int(getattr(subtarefa, "segundos_gastos", 0) or 0)),
                        str(getattr(subtarefa, "observacao", "") or ""),
                        "Pago" if bool(getattr(subtarefa, "bloqueada_pagamento", False)) else "",
                    ),
                    (),
                ))

            for pag in pagamentos:
                data_pag = pag.get("data_pagamento")
                if isinstance(data_pag, str):
                    try:
                        data_pag = date.fromisoformat(data_pag)
                    except (ValueError, TypeError):
                        data_pag = None
                valor = pag.get("valor", 0)
                valor_fmt = f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                ref_inicio = pag.get("referencia_inicio") or ""
                ref_fim = pag.get("referencia_fim") or ""
                periodo = ""
                if ref_inicio and ref_fim:
                    periodo = f"{self._formatar_data(ref_inicio)} a {self._formatar_data(ref_fim)}"
                elif ref_inicio:
                    periodo = f"A partir de {self._formatar_data(ref_inicio)}"
                elif ref_fim:
                    periodo = f"Até {self._formatar_data(ref_fim)}"
                obs = str(pag.get("observacao") or "")
                id_pag = int(pag.get("id_pagamento", 0))
                itens_mesclados.append((
                    data_pag if isinstance(data_pag, date) else None,
                    0,
                    f"pagamento_{id_pag}",
                    (
                        f"💰 Pagamento — {valor_fmt}",
                        periodo,
                        "Pago",
                        self._formatar_data(data_pag),
                        "",
                        obs,
                        "",
                    ),
                    ("pagamento",),
                ))

            # Ordenar: data desc, pagamentos acima de subtarefas na mesma data
            itens_mesclados.sort(key=lambda x: (x[0] or date.min, -x[1]), reverse=True)

            for _, _, iid, valores, tags in itens_mesclados:
                self._arvore.insert("", "end", iid=iid, values=valores, tags=tags)

            self._var_resumo.set(
                f"Trabalhado: {resumo['monitorado_hhmmss']}    |    "
                f"Declarado: {resumo['declarado_hhmmss']}"
            )
            self._atualizar_texto_trava(travado_ate)

        def _falha(erro: Exception) -> None:
            self._var_resumo.set(f"Falha ao carregar: {erro}")
            messagebox.showerror("Erro", str(erro), parent=self)

        self._executar_em_background(_buscar, _aplicar, _falha)

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
        janela.geometry("700x420")
        janela.resizable(False, False)
        janela.transient(self)
        janela.grab_set()
        janela.configure(bg="#111111")

        canal_inicial = (str(getattr(subtarefa, "canal_entrega", "") or "") if subtarefa else self._titulo_atividade)
        var_titulo = tk.StringVar(value=(str(getattr(subtarefa, "titulo", "") or "") if subtarefa else ""))
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

        # barra de acento no topo
        tk.Frame(janela, bg=_A, height=3).pack(fill="x")

        # área principal
        inner = tk.Frame(janela, bg=_C, padx=26, pady=18)
        inner.pack(fill="both", expand=True)

        titulo_janela = "Editar Tarefa" if subtarefa else "Nova Tarefa"
        tk.Label(inner, text=titulo_janela, bg=_C, fg="#ffffff",
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 16))

        # Tarefa
        tk.Label(inner, text="TAREFA", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Entry(inner, textvariable=var_titulo, width=82).pack(fill="x", pady=(3, 12))

        # Canal + Data (lado a lado)
        linha_superior = tk.Frame(inner, bg=_C)
        linha_superior.pack(fill="x")
        coluna_esquerda = tk.Frame(linha_superior, bg=_C)
        coluna_esquerda.pack(side="left", fill="x", expand=True)
        coluna_direita = tk.Frame(linha_superior, bg=_C)
        coluna_direita.pack(side="left", fill="x", expand=True, padx=(12, 0))

        tk.Label(coluna_esquerda, text="CANAL", bg=_C, fg=_D,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
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
            titulo = var_titulo.get()
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

        entrada_user.focus_set()
        self.bind("<Return>", lambda _e: self._logar())

    def _montar_tela_principal(self) -> None:
        self.geometry("660x340")
        for widget in self.winfo_children():
            widget.destroy()

        quadro = ttk.Frame(self, padding=14)
        quadro.pack(fill="both", expand=True)

        topo = ttk.Frame(quadro)
        topo.pack(fill="x")

        nome = self._usuario["nome_exibicao"] if self._usuario else ""
        ttk.Label(topo, text=f"Usuário: {nome}", font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(topo, text="Fixar", command=self._alternar_fixar).pack(side="right", padx=(6, 0))
        ttk.Button(topo, text="Sair", command=self._sair).pack(side="right")

        # combo oculto — mantém a lógica de seleção de atividade sem exibir na tela
        self._combo = ttk.Combobox(self, textvariable=self._var_atividade, state="readonly", width=58, values=[])

        painel = ttk.Frame(quadro)
        painel.pack(fill="both", expand=True, pady=(14, 0))

        ttk.Label(painel, textvariable=self._var_tempo, font=("Segoe UI", 44, "bold"), foreground="#ffffff").pack(anchor="center")
        ttk.Label(painel, textvariable=self._var_status, font=("Segoe UI", 10, "bold"), foreground="#aaaaaa").pack(anchor="center", pady=(6, 0))
        ttk.Label(painel, textvariable=self._var_erro, foreground="#f0a500",
                  font=("Segoe UI", 8), wraplength=380, justify="center").pack(anchor="center", pady=(2, 0))

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
                subprocess.Popen([str(caminho_atual)])
                self.after(0, lambda: os._exit(0))
            except Exception:
                pass

        threading.Thread(target=_em_thread, daemon=True).start()

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
            status = str(linha["status"] or "").strip()
            item = f"#{id_atividade} - {titulo} ({status})"
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

    def _acao_principal(self) -> None:
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

    def _abrir_fixado(self) -> None:
        if self._janela_fixada and self._janela_fixada.winfo_exists():
            return

        janela = tk.Toplevel(self)
        janela.title("Cronômetro (Fixado)")
        janela.geometry("230x95")
        janela.resizable(False, False)
        janela.attributes("-topmost", True)
        janela.configure(bg="#111111", padx=10, pady=10)

        ttk.Label(janela, textvariable=self._var_tempo_fixado, font=("Segoe UI", 26, "bold")).pack(anchor="center")
        ttk.Label(janela, textvariable=self._var_status_fixado, font=("Segoe UI", 9, "bold")).pack(anchor="center", pady=(2, 0))
        janela.protocol("WM_DELETE_WINDOW", self._fechar_fixado)
        self._janela_fixada = janela

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

        if status_texto != self._ultimo_status_renderizado:
            self._var_status.set(status_texto)
            self._var_status_fixado.set(status_texto if tem_sessao or estado.rodando else "")
            self._ultimo_status_renderizado = status_texto

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

        if estado.ultimo_erro:
            offline = getattr(self._monitor, "_offline_notificado", False)
            if offline:
                self._var_erro.set("⚠ Perdemos a conexão com o servidor, provavelmente você está sem internet.")
            else:
                self._var_erro.set(f"⚠ {estado.ultimo_erro}")
        else:
            self._var_erro.set("")

        if hasattr(self, "_btn_tarefas"):
            offline = getattr(self._monitor, "_offline_notificado", False)
            self._btn_tarefas.configure(state="disabled" if offline else "normal")

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
