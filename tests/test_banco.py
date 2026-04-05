"""Testes de banco.py — ping interval, thread isolation."""
from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

from banco import PING_INTERVALO_SEGUNDOS, BancoDados


class TestPingInterval:
    def test_ping_intervalo_configurado_60s(self):
        assert PING_INTERVALO_SEGUNDOS == 60.0

    @patch("banco.pymysql")
    def test_nova_conexao_seta_ultimo_ping(self, mock_pymysql):
        """Ao criar conexao nova, ultimo_ping deve ser inicializado."""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn

        banco = BancoDados()
        conn = banco._obter_conexao_da_thread()

        assert conn is mock_conn
        assert hasattr(banco._local, "ultimo_ping")
        assert banco._local.ultimo_ping > 0

    @patch("banco.pymysql")
    def test_conexao_existente_nao_pinga_antes_60s(self, mock_pymysql):
        """Se a conexao foi pingada ha menos de 60s, nao deve pingar de novo."""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn

        banco = BancoDados()
        # Primeira chamada: cria conexao
        banco._obter_conexao_da_thread()

        # Segunda chamada: deve reutilizar sem ping (< 60s)
        mock_conn.ping.reset_mock()
        banco._obter_conexao_da_thread()
        mock_conn.ping.assert_not_called()

    @patch("banco.pymysql")
    def test_conexao_existente_pinga_apos_60s(self, mock_pymysql):
        """Apos 60s, deve pingar a conexao."""
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn

        banco = BancoDados()
        banco._obter_conexao_da_thread()

        # Simular que 61s passaram
        banco._local.ultimo_ping = time.monotonic() - 61
        banco._obter_conexao_da_thread()
        mock_conn.ping.assert_called_once_with(reconnect=True)

    @patch("banco.pymysql")
    def test_reconecta_apos_falha_ping(self, mock_pymysql):
        """Se ping falha, deve criar conexao nova."""
        mock_conn_antiga = MagicMock()
        mock_conn_antiga.ping.side_effect = Exception("Connection lost")
        mock_conn_nova = MagicMock()

        mock_pymysql.connect.side_effect = [mock_conn_antiga, mock_conn_nova]

        banco = BancoDados()
        # Primeira: cria conexao antiga
        banco._obter_conexao_da_thread()

        # Forcar ping (simula 61s)
        banco._local.ultimo_ping = time.monotonic() - 61
        # Segunda: ping falha, cria nova
        conn = banco._obter_conexao_da_thread()
        assert conn is mock_conn_nova


class TestThreadIsolation:
    @patch("banco.pymysql")
    def test_threads_diferentes_tem_conexoes_diferentes(self, mock_pymysql):
        """Cada thread deve ter sua propria conexao."""
        conn1 = MagicMock()
        conn2 = MagicMock()
        mock_pymysql.connect.side_effect = [conn1, conn2]

        banco = BancoDados()
        resultados = {}

        def worker(nome):
            resultados[nome] = banco._obter_conexao_da_thread()

        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        t1.start()
        t1.join()
        t2.start()
        t2.join()

        assert resultados["t1"] is conn1
        assert resultados["t2"] is conn2
        assert resultados["t1"] is not resultados["t2"]


class TestOperacoes:
    @patch("banco.pymysql")
    def test_executar_retorna_lastrowid(self, mock_pymysql):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 42
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        banco = BancoDados()
        resultado = banco.executar("INSERT INTO tabela VALUES (%s)", [1])
        assert resultado == 42

    @patch("banco.pymysql")
    def test_consultar_um_retorna_dict(self, mock_pymysql):
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "nome": "teste"}
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_pymysql.connect.return_value = mock_conn

        banco = BancoDados()
        resultado = banco.consultar_um("SELECT * FROM tabela WHERE id = %s", [1])
        assert resultado == {"id": 1, "nome": "teste"}

    @patch("banco.pymysql")
    def test_fechar_conexao(self, mock_pymysql):
        mock_conn = MagicMock()
        mock_pymysql.connect.return_value = mock_conn

        banco = BancoDados()
        banco._obter_conexao_da_thread()
        banco.fechar_conexao_da_thread()

        mock_conn.close.assert_called_once()
        assert getattr(banco._local, "conexao", None) is None
