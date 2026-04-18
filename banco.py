##banco.py
from __future__ import annotations

import os
import threading
import time
from typing import Any

import pymysql

# =========================
# CONFIG BANCO (via ENV ou fallback local)
# =========================
DB_HOST = os.environ.get("DB_HOST", "76.13.112.108")
DB_PORTA = int(os.environ.get("DB_PORT", "3306"))
DB_NOME = os.environ.get("DB_NAME", "dados")
DB_USUARIO = os.environ.get("DB_USER", "kolaias")
DB_SENHA = os.environ.get("DB_PASS", "kolaias")

# log básico (se quiser desligar, deixe False)
DEBUG_BANCO = False


PING_INTERVALO_SEGUNDOS = 60.0


class BancoDados:
    """
    Conexão por thread (Tk + worker), evita travamento e erro de thread.
    """

    def __init__(self) -> None:
        self._local = threading.local()

    def _log(self, mensagem: str) -> None:
        if DEBUG_BANCO:
            print(f"[BANCO] {mensagem}")

    def _obter_conexao_da_thread(self) -> pymysql.connections.Connection:
        conexao = getattr(self._local, "conexao", None)
        if conexao is not None:
            ultimo_ping = getattr(self._local, "ultimo_ping", 0.0)
            agora = time.monotonic()
            if (agora - ultimo_ping) >= PING_INTERVALO_SEGUNDOS:
                try:
                    conexao.ping(reconnect=True)
                    self._local.ultimo_ping = agora
                except Exception:
                    try:
                        conexao.close()
                    except Exception:
                        pass
                    self._local.conexao = None
                    conexao = None
            if conexao is not None:
                return conexao

        self._log("Abrindo nova conexão (thread).")
        conexao = pymysql.connect(
            host=DB_HOST,
            port=int(DB_PORTA),
            user=DB_USUARIO,
            password=DB_SENHA,
            database=DB_NOME,
            charset="utf8mb4",
            autocommit=True,
            cursorclass=pymysql.cursors.DictCursor,
        )
        self._local.conexao = conexao
        self._local.ultimo_ping = time.monotonic()
        return conexao

    def fechar_conexao_da_thread(self) -> None:
        conexao = getattr(self._local, "conexao", None)
        if conexao is None:
            return
        try:
            conexao.close()
        except Exception:
            pass
        self._local.conexao = None

    def executar(self, sql: str, parametros: list[Any] | None = None) -> int:
        conexao = self._obter_conexao_da_thread()
        parametros = parametros or []
        with conexao.cursor() as cursor:
            self._log(sql)
            cursor.execute(sql, parametros)
            try:
                return int(cursor.lastrowid or 0)
            except Exception:
                return 0

    def executar_e_contar(self, sql: str, parametros: list[Any] | None = None) -> int:
        """Como executar(), mas retorna rowcount (linhas afetadas) — útil para UPDATE/DELETE."""
        conexao = self._obter_conexao_da_thread()
        parametros = parametros or []
        with conexao.cursor() as cursor:
            self._log(sql)
            cursor.execute(sql, parametros)
            try:
                return int(cursor.rowcount or 0)
            except Exception:
                return 0

    def consultar_um(self, sql: str, parametros: list[Any] | None = None) -> dict | None:
        conexao = self._obter_conexao_da_thread()
        parametros = parametros or []
        with conexao.cursor() as cursor:
            self._log(sql)
            cursor.execute(sql, parametros)
            return cursor.fetchone()

    def consultar_todos(self, sql: str, parametros: list[Any] | None = None) -> list[dict]:
        conexao = self._obter_conexao_da_thread()
        parametros = parametros or []
        with conexao.cursor() as cursor:
            self._log(sql)
            cursor.execute(sql, parametros)
            return list(cursor.fetchall() or [])

    def executar_muitos(self, sql: str, lista_parametros: list[list[Any]]) -> None:
        if not lista_parametros:
            return
        conexao = self._obter_conexao_da_thread()
        with conexao.cursor() as cursor:
            self._log(sql)
            cursor.executemany(sql, lista_parametros)
