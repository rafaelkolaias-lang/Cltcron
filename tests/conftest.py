"""Fixtures compartilhadas para os testes do Cronometro."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Garantir que o diretorio raiz esteja no path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class BancoDadosFake:
    """Mock do BancoDados que retorna valores configuraveis sem conexao real."""

    def __init__(self):
        self._retorno_consultar_um: dict | None = None
        self._retorno_consultar_todos: list[dict] = []
        self._ultimo_sql: str = ""
        self._ultimo_parametros: list = []
        self._chamadas: list[tuple[str, str, list]] = []

    def configurar_consultar_um(self, retorno: dict | None):
        self._retorno_consultar_um = retorno

    def configurar_consultar_todos(self, retorno: list[dict]):
        self._retorno_consultar_todos = retorno

    def executar(self, sql: str, parametros: list | None = None) -> int:
        self._registrar("executar", sql, parametros or [])
        return 1

    def consultar_um(self, sql: str, parametros: list | None = None) -> dict | None:
        self._registrar("consultar_um", sql, parametros or [])
        return self._retorno_consultar_um

    def consultar_todos(self, sql: str, parametros: list | None = None) -> list[dict]:
        self._registrar("consultar_todos", sql, parametros or [])
        return self._retorno_consultar_todos

    def executar_muitos(self, sql: str, lista_parametros: list | None = None) -> None:
        self._registrar("executar_muitos", sql, lista_parametros or [])

    def fechar_conexao_da_thread(self) -> None:
        pass

    def _registrar(self, metodo: str, sql: str, parametros: list):
        self._ultimo_sql = sql
        self._ultimo_parametros = parametros
        self._chamadas.append((metodo, sql, parametros))

    def ultima_chamada_contem(self, texto: str) -> bool:
        return texto.lower() in self._ultimo_sql.lower()


@pytest.fixture
def banco_fake():
    """Retorna um BancoDadosFake configuravel."""
    return BancoDadosFake()


@pytest.fixture
def banco_mock():
    """Retorna um MagicMock do BancoDados."""
    mock = MagicMock()
    mock.consultar_um.return_value = None
    mock.consultar_todos.return_value = []
    mock.executar.return_value = 1
    return mock
