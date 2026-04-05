"""Testes da logica de tempo — converter, formatar, MonitorDeUso."""
from __future__ import annotations

import time

import pytest

from app import MonitorDeUso, converter_segundos_para_inteiro, formatar_hhmmss

# ============================================================
# converter_segundos_para_inteiro
# ============================================================

class TestConverterSegundos:
    def test_zero(self):
        assert converter_segundos_para_inteiro(0) == 0

    def test_inteiro_positivo(self):
        assert converter_segundos_para_inteiro(120) == 120

    def test_float_arredonda_pra_baixo(self):
        assert converter_segundos_para_inteiro(59.9) == 59

    def test_negativo_vira_zero(self):
        assert converter_segundos_para_inteiro(-10) == 0

    def test_negativo_float_vira_zero(self):
        assert converter_segundos_para_inteiro(-0.5) == 0

    def test_valor_grande(self):
        assert converter_segundos_para_inteiro(86400.0) == 86400


# ============================================================
# formatar_hhmmss
# ============================================================

class TestFormatarHhmmss:
    def test_zero(self):
        assert formatar_hhmmss(0) == "00:00:00"

    def test_um_segundo(self):
        assert formatar_hhmmss(1) == "00:00:01"

    def test_59_segundos(self):
        assert formatar_hhmmss(59) == "00:00:59"

    def test_um_minuto(self):
        assert formatar_hhmmss(60) == "00:01:00"

    def test_uma_hora(self):
        assert formatar_hhmmss(3600) == "01:00:00"

    def test_uma_hora_um_minuto_um_segundo(self):
        assert formatar_hhmmss(3661) == "01:01:01"

    def test_valor_grande(self):
        assert formatar_hhmmss(86399) == "23:59:59"

    def test_mais_que_24h(self):
        assert formatar_hhmmss(90061) == "25:01:01"

    def test_negativo_retorna_zeros(self):
        assert formatar_hhmmss(-100) == "00:00:00"

    def test_none_retorna_zeros(self):
        assert formatar_hhmmss(None) == "00:00:00"


# ============================================================
# MonitorDeUso — estado e acumulacao
# ============================================================

class TestMonitorDeUso:
    @pytest.fixture
    def monitor(self, banco_mock):
        return MonitorDeUso(banco_mock)

    def test_estado_inicial_parado(self, monitor):
        estado = monitor.obter_estado()
        assert estado.rodando is False
        assert estado.situacao == "pausado"
        assert estado.segundos_trabalhando == 0
        assert estado.segundos_ocioso == 0
        assert estado.segundos_pausado == 0

    def test_obter_segundos_cronometro_zerado(self, monitor):
        assert monitor.obter_segundos_cronometro() == 0

    def test_obter_segundos_trabalhando_zerado(self, monitor):
        assert monitor.obter_segundos_trabalhando() == 0

    def test_obter_segundos_pausado_zerado(self, monitor):
        assert monitor.obter_segundos_pausado() == 0

    def test_acumular_tempo_trabalhando(self, monitor):
        """Simula acumulacao manual de tempo trabalhando."""
        with monitor._trava:
            monitor._rodando = True
            monitor._sessao_carregada = True
            monitor._situacao_manual = "rodando"
            monitor._situacao_calculada = "trabalhando"
            monitor._ultimo_marco_mono = time.monotonic()
            # Simula 10 segundos
            monitor._segundos_trabalhando_float = 10.0

        assert monitor.obter_segundos_trabalhando() >= 10

    def test_acumular_tempo_ocioso(self, monitor):
        """Simula acumulacao de tempo ocioso."""
        with monitor._trava:
            monitor._rodando = True
            monitor._sessao_carregada = True
            monitor._situacao_manual = "rodando"
            monitor._situacao_calculada = "ocioso"
            monitor._ultimo_marco_mono = time.monotonic()
            monitor._segundos_ocioso_float = 300.0

        assert monitor.obter_segundos_cronometro() >= 300

    def test_acumular_tempo_pausado(self, monitor):
        """Simula acumulacao de tempo pausado."""
        with monitor._trava:
            monitor._rodando = True
            monitor._sessao_carregada = True
            monitor._situacao_manual = "pausado"
            monitor._situacao_calculada = "pausado"
            monitor._ultimo_marco_mono = time.monotonic()
            monitor._segundos_pausado_float = 60.0

        assert monitor.obter_segundos_pausado() >= 60

    def test_cronometro_soma_trabalhando_e_ocioso(self, monitor):
        """obter_segundos_cronometro = trabalhando + ocioso (sem pausado)."""
        with monitor._trava:
            monitor._segundos_trabalhando_float = 100.0
            monitor._segundos_ocioso_float = 50.0
            monitor._segundos_pausado_float = 200.0

        cronometro = monitor.obter_segundos_cronometro()
        assert cronometro == 150  # 100 + 50, sem o pausado

    def test_pausar_bloqueado_durante_ocioso(self, monitor):
        """Editor nao pode pausar enquanto esta ocioso."""
        with monitor._trava:
            monitor._sessao_carregada = True
            monitor._rodando = True
            monitor._situacao_manual = "rodando"
            monitor._situacao_calculada = "ocioso"
            monitor._ultimo_marco_mono = time.monotonic()

        monitor.pausar()

        # Deve continuar rodando — pausa bloqueada
        estado = monitor.obter_estado()
        assert estado.rodando is True
        assert estado.situacao == "ocioso"

    def test_pausar_permitido_quando_trabalhando(self, monitor, banco_mock):
        """Editor pode pausar normalmente quando esta trabalhando."""
        with monitor._trava:
            monitor._sessao_carregada = True
            monitor._rodando = True
            monitor._situacao_manual = "rodando"
            monitor._situacao_calculada = "trabalhando"
            monitor._ultimo_marco_mono = time.monotonic()
            monitor._id_sessao = 1
            monitor._user_id = "teste"

        monitor.pausar()

        estado = monitor.obter_estado()
        assert estado.rodando is False
        assert estado.situacao == "pausado"

    def test_delta_tempo_locked_parado(self, monitor):
        """Delta deve ser 0 quando nao esta rodando."""
        with monitor._trava:
            monitor._rodando = False
            assert monitor._delta_tempo_locked() == 0.0

    def test_snapshot_inclui_ultimo_erro(self, monitor):
        """Snapshot deve incluir ultimo erro registrado."""
        with monitor._trava:
            monitor._registrar_erro_locked("Falha teste")
        estado = monitor.obter_estado()
        assert estado.ultimo_erro == "Falha teste"
